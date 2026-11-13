"""
Document resources for AccessAI MCP Server.
URI format: accessai://documents/{id}
"""

from typing import Dict, Any, Optional
from ...database import get_db
from ...services.document_service import DocumentService


def get_document_resource(doc_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, kind, file_path, pages, chars, ocr_used, extracted_text FROM attachments WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Document {doc_id} not found.")

        meta = dict(row)
        outline = DocumentService.get_document_outline(meta["file_path"], meta["name"])
        return {
            "id": meta["id"],
            "name": meta["name"],
            "pages": meta["pages"],
            "chars": meta["chars"],
            "ocr_used": bool(meta["ocr_used"]),
            "outline": outline,
            "text_sample": (meta["extracted_text"] or "")[:2000],
        }
