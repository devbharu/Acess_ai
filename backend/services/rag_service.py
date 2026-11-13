import os
import re
import math
import numpy as np
import logging
from typing import List, Dict, Any, Optional

try:
    import faiss
except ImportError:
    faiss = None

class RecursiveCharacterTextSplitter:
    """
    Lightweight, high-performance character text splitter.
    Zero external dependencies and zero memory overhead.
    """
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120, separators: Optional[List[str]] = None):
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = min(chunk_overlap, self.chunk_size - 10)
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        text = text.strip()
        if len(text) <= self.chunk_size:
            return [text] if text else []

        sep = separators[-1]
        for s in separators:
            if s and s in text:
                sep = s
                break

        splits = text.split(sep) if sep else list(text)
        chunks = []
        current = ""

        for part in splits:
            piece = (current + sep + part).strip() if current else part.strip()
            if len(piece) <= self.chunk_size:
                current = piece
            else:
                if current:
                    chunks.append(current)
                next_seps = separators[separators.index(sep) + 1 :] if sep in separators[:-1] else []
                if len(part) > self.chunk_size and next_seps:
                    sub_chunks = self._split(part, next_seps)
                    chunks.extend(sub_chunks[:-1])
                    current = sub_chunks[-1] if sub_chunks else ""
                else:
                    current = part.strip()

        if current:
            chunks.append(current)
        return [c for c in chunks if c.strip()]

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    _instance = None

    def __init__(self):
        self.model = None
        self._checked_model = False
        self.use_transformer = os.environ.get("USE_SENTENCE_TRANSFORMERS", "").lower() in ("true", "1")

    def _get_model(self):
        if not self.use_transformer:
            return None
        if not self._checked_model:
            self._checked_model = True
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("SentenceTransformer model loaded.")
            except Exception as e:
                logger.warning("Could not load SentenceTransformer, using TF-IDF fallback: %s", e)
                self.model = None
        return self.model

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype="float32")

        model = self._get_model()
        if model:
            try:
                emb = model.encode(texts, convert_to_numpy=True)
                return np.array(emb, dtype="float32")
            except Exception as e:
                logger.error("Encoding failed with transformer: %s", e)

        # High-performance sublinear TF-IDF + n-gram hashing vectorizer (384-dim, unit-normalized)
        dim = 384
        vectors = np.zeros((len(texts), dim), dtype="float32")
        for i, text in enumerate(texts):
            words = re.findall(r"\w+", text.lower())
            if not words:
                continue
            word_counts = {}
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1
            for w, count in word_counts.items():
                idx = (hash(w) & 0x7FFFFFFF) % dim
                tf = 1.0 + math.log(count)
                weight = tf * (1.2 if len(w) > 4 else 1.0)
                vectors[i, idx] += weight

            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] /= norm
        return vectors

_embedding_engine = None
def get_embedding_engine() -> EmbeddingEngine:
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine

class ConversationIndex:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.vectors: Optional[np.ndarray] = None
        self.faiss_index = None

    def add_passages(self, passages: List[Dict[str, Any]], embeddings: np.ndarray):
        if not passages:
            return
        
        # Normalize embeddings for inner product (cosine similarity)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = embeddings / norms

        if self.vectors is None:
            self.vectors = normalized
        else:
            self.vectors = np.vstack([self.vectors, normalized])

        self.chunks.extend(passages)

        dim = self.vectors.shape[1]
        if faiss:
            self.faiss_index = faiss.IndexFlatIP(dim)
            self.faiss_index.add(self.vectors.astype("float32"))

    def search(self, query_vector: np.ndarray, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.chunks or self.vectors is None or len(self.chunks) == 0:
            return []

        top_k = min(top_k, len(self.chunks))
        
        # Normalize query vector
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm
        query_vector = query_vector.astype("float32")
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)

        results = []
        if faiss and self.faiss_index:
            scores, indices = self.faiss_index.search(query_vector, top_k)
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.chunks):
                    item = dict(self.chunks[idx])
                    item["score"] = float(max(0.0, min(1.0, float(score))))
                    results.append(item)
        else:
            # Fallback dot product
            scores = np.dot(self.vectors, query_vector.T).flatten()
            best_indices = np.argsort(scores)[::-1][:top_k]
            for idx in best_indices:
                item = dict(self.chunks[idx])
                item["score"] = float(max(0.0, min(1.0, float(scores[idx]))))
                results.append(item)

        return results

class RAGService:
    _indices: Dict[str, ConversationIndex] = {}
    _MAX_CACHED_INDICES = 15

    @classmethod
    def get_index(cls, conversation_id: str) -> ConversationIndex:
        cid = conversation_id or "default"
        if cid in cls._indices:
            # Move to end (most recently used)
            idx = cls._indices.pop(cid)
            cls._indices[cid] = idx
            return idx

        # Evict oldest conversation index if exceeding limit
        if len(cls._indices) >= cls._MAX_CACHED_INDICES:
            try:
                oldest_cid = next(iter(cls._indices))
                del cls._indices[oldest_cid]
            except Exception:
                pass

        idx = ConversationIndex()
        cls._indices[cid] = idx
        if conversation_id:
            try:
                from ..database import get_db
                with get_db() as conn:
                    rows = conn.execute(
                        "SELECT name, kind, file_path, extracted_text, image_description FROM attachments WHERE conversation_id = ?",
                        (conversation_id,),
                    ).fetchall()
                    for r in rows:
                        if r["kind"] == "image":
                            cls.index_image(
                                conversation_id=conversation_id,
                                filename=r["name"],
                                ocr_text=r["extracted_text"] or "",
                                image_description=r["image_description"] or "",
                                file_path=r["file_path"] or "",
                            )
                        elif r["kind"] == "document" and r["extracted_text"]:
                            cls.index_document(
                                conversation_id=conversation_id,
                                filename=r["name"],
                                pages_data=[{"page": 1, "text": r["extracted_text"]}],
                            )
            except Exception as ex:
                logger.debug("RAG warmup error: %s", ex)
        return cls._indices[cid]

    @classmethod
    def index_document(cls, conversation_id: str, filename: str, pages_data: List[Dict[str, Any]], chunk_size: int = 800, chunk_overlap: int = 120, is_ocr: bool = False):
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        passages = []

        for p in pages_data:
            page_num = p.get("page", 1)
            raw_text = p.get("text", "")
            if not raw_text.strip():
                continue
            
            sub_chunks = splitter.split_text(raw_text)
            for chunk in sub_chunks:
                passages.append({
                    "type": "ocr" if is_ocr else "document",
                    "source": filename,
                    "page": page_num,
                    "text": chunk.strip(),
                })

        if not passages:
            return

        engine = get_embedding_engine()
        texts = [p["text"] for p in passages]
        embeddings = engine.encode(texts)

        index = cls.get_index(conversation_id)
        index.add_passages(passages, embeddings)

    @classmethod
    def index_image(cls, conversation_id: str, filename: str, ocr_text: str, image_description: str, file_path: str = ""):
        passages = []
        if image_description:
            passages.append({
                "type": "image",
                "source": filename,
                "page": 1,
                "text": f"Visual scene: {image_description}",
                "file_path": file_path,
                "image_description": image_description,
            })
        if ocr_text:
            passages.append({
                "type": "ocr",
                "source": filename,
                "page": 1,
                "text": f"Extracted text: {ocr_text}",
                "file_path": file_path,
                "ocr_text": ocr_text,
            })

        if not passages:
            return

        engine = get_embedding_engine()
        texts = [p["text"] for p in passages]
        embeddings = engine.encode(texts)

        cid = conversation_id or "default"
        if cid not in cls._indices:
            cls._indices[cid] = ConversationIndex()
        cls._indices[cid].add_passages(passages, embeddings)

    @classmethod
    def retrieve(cls, conversation_id: str, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        index = cls.get_index(conversation_id)
        engine = get_embedding_engine()
        q_emb = engine.encode([query])[0]
        return index.search(q_emb, top_k=top_k)
