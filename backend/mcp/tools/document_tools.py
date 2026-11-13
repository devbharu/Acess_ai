"""
Document extraction, outline, search, and page reading MCP tools.
"""

from typing import Dict, Any, List, Optional
from ...database import get_db
from ...services.document_service import DocumentService


def get_file_metadata(file_id: str, user_id: str) -> Dict[str, Any]:
    """
    Retrieves metadata (name, pages, character length, OCR usage status) for a document or image.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, kind, file_path, pages, chars, ocr_used FROM attachments WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError(f"File {file_id} not found.")
        return {
            "id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "pages": row["pages"],
            "chars": row["chars"],
            "ocr_used": bool(row["ocr_used"]),
            "file_path": row["file_path"],
        }


def extract_document_text(file_id: str, user_id: str, max_chars: int = 15000) -> Dict[str, Any]:
    """
    Extracts the textual content across all pages in a document.
    """
    meta = get_file_metadata(file_id, user_id)
    with get_db() as conn:
        row = conn.execute("SELECT extracted_text FROM attachments WHERE id = ?", (file_id,)).fetchone()
        if row and row["extracted_text"]:
            text = row["extracted_text"]
        else:
            extraction = DocumentService.extract_from_file(meta["file_path"], meta["name"])
            text = "\n\n".join([p["text"] for p in extraction["pages_data"]])
            conn.execute("UPDATE attachments SET extracted_text = ? WHERE id = ?", (text, file_id))

    truncated = len(text) > max_chars
    return {
        "id": file_id,
        "name": meta["name"],
        "pages": meta["pages"],
        "text": text[:max_chars],
        "truncated": truncated,
    }


def get_document_outline(file_id: str, user_id: str) -> Dict[str, Any]:
    """
    Extracts native table of contents or prominent page heading blocks with page numbers.
    """
    meta = get_file_metadata(file_id, user_id)
    outline = DocumentService.get_document_outline(meta["file_path"])
    return {
        "file_id": file_id,
        "filename": meta["name"],
        "total_pages": meta["pages"],
        "outline": outline,
    }


def search_document(file_id: str, query: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Performs high-precision keyword and semantic regex searches across all pages of a document.
    """
    meta = get_file_metadata(file_id, user_id)
    return DocumentService.search_document(meta["file_path"], query)


def get_page_content(file_id: str, page_number: int, user_id: str) -> Dict[str, Any]:
    """
    Retrieves the exact text, OCR content, tables, and metadata for a specific 1-indexed page.
    """
    meta = get_file_metadata(file_id, user_id)
    content = DocumentService.get_page_content(meta["file_path"], page_number)
    content["file_id"] = file_id
    content["filename"] = meta["name"]
    return content
