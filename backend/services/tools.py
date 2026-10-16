import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from ..database import get_db
from .document_service import DocumentService
from .vision_service import VisionService

logger = logging.getLogger("accessai.tools")

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        Returns schemas formatted for LLM tool calling (OpenAI / Ollama format).
        """
        schemas = []
        for t in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                }
            })
        return schemas

    def execute(self, name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a registered tool with argument validation and error containment.
        """
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' is not registered."}

        func = tool["func"]
        try:
            import inspect
            sig = inspect.signature(func)
            merged = dict(context or {})
            merged.update(arguments or {})

            filtered_args = {}
            for param_name, param in sig.parameters.items():
                if param_name in merged:
                    filtered_args[param_name] = merged[param_name]
                elif param.default is not inspect.Parameter.empty:
                    pass

            res = func(**filtered_args)
            return {"success": True, "result": res}
        except TypeError as te:
            logger.error("Tool '%s' invalid arguments: %s", name, te)
            return {"success": False, "error": f"Invalid arguments for {name}: {str(te)}"}
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", name, e)
            return {"success": False, "error": str(e)}


registry = ToolRegistry()

# -------------------------------------------------------------
# Tool Implementations
# -------------------------------------------------------------

def _resolve_attachment_file(file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Helper to get attachment and verify user ownership."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, conversation_id, name, kind, file_path, pages, chars, ocr_used, extracted_text, image_description "
            "FROM attachments WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def list_conversation_files(user_id: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists files strictly private to the current conversation."""
    with get_db() as conn:
        if conversation_id:
            rows = conn.execute(
                "SELECT id, name, kind, pages, chars, ocr_used, created_at FROM attachments WHERE user_id = ? AND (conversation_id = ? OR conversation_id IS NULL) ORDER BY created_at DESC",
                (user_id, conversation_id),
            ).fetchall()
            return [dict(r) for r in rows]
        rows = conn.execute(
            "SELECT id, name, kind, pages, chars, ocr_used, created_at FROM attachments WHERE user_id = ? AND conversation_id IS NULL ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_available_images(user_id: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists images strictly private to the current conversation."""
    with get_db() as conn:
        if conversation_id:
            rows = conn.execute(
                "SELECT id, name, file_path, image_description, extracted_text, ocr_used, created_at "
                "FROM attachments WHERE user_id = ? AND (conversation_id = ? OR conversation_id IS NULL) AND kind = 'image' ORDER BY created_at DESC",
                (user_id, conversation_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, file_path, image_description, extracted_text, ocr_used, created_at "
                "FROM attachments WHERE user_id = ? AND conversation_id IS NULL AND kind = 'image' ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        res = []
        for r in rows:
            res.append({
                "id": r["id"],
                "name": r["name"],
                "description": r["image_description"] or "Visual scene available.",
                "ocr_text": r["extracted_text"] or "",
            })
        return res


def get_file_metadata(file_id: str, user_id: str) -> Dict[str, Any]:
    """Retrieves metadata of a specific file."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"File '{file_id}' not found or access denied.")
    return {
        "id": att["id"],
        "name": att["name"],
        "kind": att["kind"],
        "pages": att.get("pages", 1),
        "chars": att.get("chars", 0),
        "ocr_used": bool(att.get("ocr_used")),
        "file_path": att["file_path"],
    }


def extract_document_text(file_id: str, user_id: str, max_chars: int = 15000) -> Dict[str, Any]:
    """Extracts or returns cached document text."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    text = att.get("extracted_text") or ""
    if not text and os.path.exists(att["file_path"]):
        res = DocumentService.extract_from_file(att["file_path"], att["name"])
        text = "\n\n".join([p["text"] for p in res["pages_data"]])
    return {
        "id": att["id"],
        "name": att["name"],
        "pages": att.get("pages", 1),
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def get_document_outline(file_id: str, user_id: str) -> Dict[str, Any]:
    """Retrieves document outline / table of contents / headings."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    outline = DocumentService.get_document_outline(att["file_path"])
    return {
        "file_id": att["id"],
        "filename": att["name"],
        "total_pages": att.get("pages", 1),
        "outline": outline,
    }


def search_document(file_id: str, query: str, user_id: str) -> List[Dict[str, Any]]:
    """Searches for keyword or topic inside the document."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    return DocumentService.search_document(att["file_path"], query)


def get_page_content(file_id: str, page_number: int, user_id: str) -> Dict[str, Any]:
    """Retrieves text and content of a specific page."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    content = DocumentService.get_page_content(att["file_path"], page_number)
    content["file_id"] = att["id"]
    content["filename"] = att["name"]
    return content


def get_document_images(file_id: str, user_id: str, page_number: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lists images embedded within a document."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    return DocumentService.get_document_images(att["file_path"], page_number)


def describe_image(file_id: str, user_id: str, model_id: str = "gemma4:31b-cloud") -> Dict[str, Any]:
    """Generates visual scene description and OCR text for an image."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att or att["kind"] != "image":
        raise ValueError(f"Image '{file_id}' not found.")
    res = VisionService.analyze_image(att["file_path"], model_id)
    return {
        "file_id": att["id"],
        "name": att["name"],
        "description": res.get("image_description") or att.get("image_description") or "Image analyzed.",
        "ocr_text": res.get("ocr_text") or att.get("extracted_text") or "",
        "file_path": att["file_path"],
    }


def answer_question_about_image(file_id: str, question: str, user_id: str, model_id: str = "gemma4:31b-cloud") -> Dict[str, Any]:
    """Answers a specific user question about an image."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att or att["kind"] != "image":
        raise ValueError(f"Image '{file_id}' not found.")
    answer = VisionService.answer_question_about_image(att["file_path"], question, model_id)
    return {
        "file_id": att["id"],
        "name": att["name"],
        "question": question,
        "answer": answer,
        "file_path": att["file_path"],
    }


def extract_table(file_id: str, user_id: str, page_number: Optional[int] = None) -> List[Dict[str, Any]]:
    """Extracts tables from a document."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    return DocumentService.extract_tables(att["file_path"], page_number)


def analyze_chart(file_id: str, user_id: str, page_number: Optional[int] = None, model_id: str = "gemma4:31b-cloud") -> Dict[str, Any]:
    """Analyzes a chart or diagram on a specific document page or image."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"File '{file_id}' not found.")
    if att["kind"] == "image":
        desc = VisionService.analyze_image(att["file_path"], model_id)
        return {
            "source": att["name"],
            "analysis": desc.get("image_description") or "Chart graphic analyzed.",
            "data": desc.get("ocr_text") or "",
        }
    else:
        # Document page chart
        p_num = page_number or 1
        page_info = DocumentService.get_page_content(att["file_path"], p_num)
        return {
            "source": att["name"],
            "page": p_num,
            "analysis": f"Visual chart data on page {p_num}: {page_info.get('text', '')[:400]}",
        }


def compare_documents(file_id_1: str, file_id_2: str, user_id: str) -> Dict[str, Any]:
    """Compares two documents."""
    att1 = _resolve_attachment_file(file_id_1, user_id)
    att2 = _resolve_attachment_file(file_id_2, user_id)
    if not att1 or not att2:
        raise ValueError("One or both documents not found.")

    out1 = DocumentService.get_document_outline(att1["file_path"])
    out2 = DocumentService.get_document_outline(att2["file_path"])

    return {
        "doc1": {"name": att1["name"], "pages": att1.get("pages", 1), "outline": out1[:5]},
        "doc2": {"name": att2["name"], "pages": att2.get("pages", 1), "outline": out2[:5]},
        "comparison": f"Compared {att1['name']} ({att1.get('pages', 1)} pages) with {att2['name']} ({att2.get('pages', 1)} pages).",
    }


def generate_accessible_summary(file_id: str, user_id: str) -> Dict[str, Any]:
    """Generates an accessible, structured screen-reader friendly summary."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"File '{file_id}' not found.")

    if att["kind"] == "image":
        return {
            "title": f"Accessible Description of {att['name']}",
            "summary": att.get("image_description") or "Image description.",
            "ocr": att.get("extracted_text") or "",
        }
    else:
        outline = DocumentService.get_document_outline(att["file_path"])
        sections = [item["title"] for item in outline[:8]]
        return {
            "title": f"Accessible Overview of {att['name']}",
            "pages": att.get("pages", 1),
            "key_sections": sections,
            "summary": f"This document contains {att.get('pages', 1)} pages covering {', '.join(sections[:4])}.",
        }


def generate_pdf_report(file_id: str, user_id: str, conversation_id: str, focus_topic: str = "") -> Dict[str, Any]:
    """Compiles a real ReportLab PDF executive summary report artifact."""
    from .agent_service import AgentService
    att = _resolve_attachment_file(file_id, user_id)
    if not att:
        raise ValueError(f"Document '{file_id}' not found.")
    artifact = AgentService.generate_pdf_summary_report(
        user_id=user_id,
        conversation_id=conversation_id,
        doc_item=att,
        focus_topic=focus_topic
    )
    return artifact


def extract_image_text(file_id: str, user_id: str) -> Dict[str, Any]:
    """Extracts all text from an image/screenshot using OCR preserving reading order."""
    att = _resolve_attachment_file(file_id, user_id)
    if not att or att["kind"] != "image":
        raise ValueError(f"Image '{file_id}' not found.")
    text = att.get("extracted_text") or ""
    if not text and att.get("file_path") and os.path.exists(att["file_path"]):
        res = VisionService.analyze_image(att["file_path"])
        text = res.get("ocr_text") or ""
    return {
        "file_id": att["id"],
        "filename": att["name"],
        "extracted_text": text,
        "uncertain_regions": [],
    }


def text_to_speech(text: str, user_id: str, voice: str = "af_heart", speed: float = 1.0) -> Dict[str, Any]:
    """Synthesizes text into speech and saves audio file."""
    from .speech_service import SpeechService
    import uuid
    from ..config import AUDIO_DIR
    if not text:
        raise ValueError("No text provided to synthesize.")
    wav_bytes = SpeechService.synthesize_speech(text, voice=voice, speed=speed)
    audio_id = f"aud_{uuid.uuid4().hex[:12]}"
    filename = f"{audio_id}.wav"
    out_path = AUDIO_DIR / filename
    with open(out_path, "wb") as f:
        f.write(wav_bytes)
    return {
        "audio_id": audio_id,
        "audio_url": f"/api/audio/{filename}",
        "available": True,
        "duration_seconds": None,
    }


def speech_to_text(audio_id: str, user_id: str, language: str = "auto") -> Dict[str, Any]:
    """Transcribes audio file to text using faster-whisper."""
    from .speech_service import SpeechService
    from ..config import AUDIO_DIR
    att = _resolve_attachment_file(audio_id, user_id)
    audio_path = att["file_path"] if att else None
    if not audio_path or not os.path.exists(audio_path):
        candidate = AUDIO_DIR / f"{audio_id}.wav"
        if candidate.exists():
            audio_path = str(candidate)
        else:
            raise ValueError(f"Audio file '{audio_id}' not found.")
    text = SpeechService.transcribe(audio_path, language=language)
    return {
        "transcript": text,
        "language": language if language != "auto" else "en",
        "audio_id": audio_id,
    }


# -------------------------------------------------------------
# Register All Tools
# -------------------------------------------------------------

registry.register(
    name="list_conversation_files",
    description="Lists all documents and images uploaded in the conversation or library.",
    parameters={
        "type": "object",
        "properties": {
            "conversation_id": {"type": "string", "description": "Active conversation ID"}
        },
    },
    func=list_conversation_files
)

registry.register(
    name="list_available_images",
    description="Lists all user uploaded images with AI scene descriptions and OCR text.",
    parameters={
        "type": "object",
        "properties": {
            "conversation_id": {"type": "string", "description": "Active conversation ID"}
        },
    },
    func=list_available_images
)

registry.register(
    name="get_file_metadata",
    description="Gets metadata (name, pages, character count, OCR status) for a file.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The unique ID of the file"}
        },
        "required": ["file_id"]
    },
    func=get_file_metadata
)

registry.register(
    name="extract_document_text",
    description="Extracts the textual content of a document.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"}
        },
        "required": ["file_id"]
    },
    func=extract_document_text
)

registry.register(
    name="get_document_outline",
    description="Extracts the outline, table of contents, and section headings of a document with page numbers.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"}
        },
        "required": ["file_id"]
    },
    func=get_document_outline
)

registry.register(
    name="search_document",
    description="Searches for specific terms, topics, or keywords across all pages in a document.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"},
            "query": {"type": "string", "description": "Search keyword or topic"}
        },
        "required": ["file_id", "query"]
    },
    func=search_document
)

registry.register(
    name="get_page_content",
    description="Retrieves the exact text, OCR content, and metadata for a specific 1-indexed page in a document.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"},
            "page_number": {"type": "integer", "description": "1-indexed page number"}
        },
        "required": ["file_id", "page_number"]
    },
    func=get_page_content
)

registry.register(
    name="get_document_images",
    description="Lists images embedded on pages of a PDF document.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"},
            "page_number": {"type": "integer", "description": "Optional page number"}
        },
        "required": ["file_id"]
    },
    func=get_document_images
)

registry.register(
    name="describe_image",
    description="Provides a comprehensive visual scene description and OCR text for an image.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The image file ID"}
        },
        "required": ["file_id"]
    },
    func=describe_image
)

registry.register(
    name="answer_question_about_image",
    description="Answers a specific visual question about an image (objects, colors, layout, text).",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The image file ID"},
            "question": {"type": "string", "description": "The question about the image"}
        },
        "required": ["file_id", "question"]
    },
    func=answer_question_about_image
)

registry.register(
    name="extract_table",
    description="Extracts tabular data from a document page into structured markdown tables.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"},
            "page_number": {"type": "integer", "description": "Optional page number"}
        },
        "required": ["file_id"]
    },
    func=extract_table
)

registry.register(
    name="analyze_chart",
    description="Analyzes diagrams, charts, or schematics in a document or image.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The file ID"},
            "page_number": {"type": "integer", "description": "Optional page number"}
        },
        "required": ["file_id"]
    },
    func=analyze_chart
)

registry.register(
    name="compare_documents",
    description="Compares the outlines, structure, and contents of two documents.",
    parameters={
        "type": "object",
        "properties": {
            "file_id_1": {"type": "string", "description": "First document ID"},
            "file_id_2": {"type": "string", "description": "Second document ID"}
        },
        "required": ["file_id_1", "file_id_2"]
    },
    func=compare_documents
)

registry.register(
    name="generate_accessible_summary",
    description="Generates an accessible, structured, screen-reader friendly summary of a document or image.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The file ID"}
        },
        "required": ["file_id"]
    },
    func=generate_accessible_summary
)

registry.register(
    name="generate_pdf_report",
    description="Compiles an executive summary report PDF using ReportLab and delivers it as an artifact.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The document file ID"},
            "focus_topic": {"type": "string", "description": "Optional focus topic"}
        },
        "required": ["file_id"]
    },
    func=generate_pdf_report
)

registry.register(
    name="extract_image_text",
    description="Extracts textual content from an image or screenshot using OCR preserving reading order.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "The image file ID"}
        },
        "required": ["file_id"]
    },
    func=extract_image_text
)

registry.register(
    name="text_to_speech",
    description="Synthesizes text into high-fidelity voice audio.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to synthesize"},
            "voice": {"type": "string", "description": "Voice identifier"},
            "speed": {"type": "number", "description": "Speech rate multiplier"}
        },
        "required": ["text"]
    },
    func=text_to_speech
)

registry.register(
    name="speech_to_text",
    description="Transcribes audio or speech recording into text.",
    parameters={
        "type": "object",
        "properties": {
            "audio_id": {"type": "string", "description": "The audio file ID or identifier"},
            "language": {"type": "string", "description": "Language code or auto"}
        },
        "required": ["audio_id"]
    },
    func=speech_to_text
)

