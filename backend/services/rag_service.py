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

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size=800, chunk_overlap=120, separators=None):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
        
        def split_text(self, text: str) -> List[str]:
            if not text:
                return []
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunks.append(text[start:end])
                if end == len(text):
                    break
                start += self.chunk_size - self.chunk_overlap
            return chunks

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    _instance = None

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer model loaded.")
        except Exception as e:
            logger.warning("Could not load SentenceTransformer, using TF-IDF fallback: %s", e)
            self.model = None

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype="float32")
        
        if self.model:
            try:
                emb = self.model.encode(texts, convert_to_numpy=True)
                return np.array(emb, dtype="float32")
            except Exception as e:
                logger.error("Encoding failed with transformer: %s", e)

        # Fallback simple bag-of-words / character n-gram pseudo-embedding
        dim = 384
        vectors = []
        for text in texts:
            words = re.findall(r"\w+", text.lower())
            vec = np.zeros(dim, dtype="float32")
            for w in words:
                idx = hash(w) % dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            vectors.append(vec)
        return np.array(vectors, dtype="float32")

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

    @classmethod
    def get_index(cls, conversation_id: str) -> ConversationIndex:
        cid = conversation_id or "default"
        if cid not in cls._indices:
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
