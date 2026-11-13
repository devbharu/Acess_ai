"""
Catalog and file listing MCP tools.
"""

from typing import List, Dict, Any, Optional
from ...database import get_db


def list_conversation_files(user_id: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists all documents and images uploaded in the conversation or user library.
    """
    with get_db() as conn:
        if conversation_id:
            rows = conn.execute(
                """
                SELECT id, name, kind, pages, chars, ocr_used, created_at
                FROM attachments
                WHERE user_id = ? AND (conversation_id = ? OR conversation_id IS NULL)
                ORDER BY created_at ASC
                """,
                (user_id, conversation_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, name, kind, pages, chars, ocr_used, created_at
                FROM attachments
                WHERE user_id = ?
                ORDER BY created_at ASC
                """,
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def list_available_images(user_id: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Catalogs all image attachments available with AI scene descriptions and OCR text.
    """
    with get_db() as conn:
        if conversation_id:
            rows = conn.execute(
                """
                SELECT id, name, image_description, extracted_text
                FROM attachments
                WHERE user_id = ? AND kind = 'image' AND (conversation_id = ? OR conversation_id IS NULL)
                ORDER BY created_at ASC
                """,
                (user_id, conversation_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, name, image_description, extracted_text
                FROM attachments
                WHERE user_id = ? AND kind = 'image'
                ORDER BY created_at ASC
                """,
                (user_id,),
            ).fetchall()
        images = []
        for r in rows:
            images.append({
                "id": r["id"],
                "name": r["name"],
                "description": r["image_description"] or "Image uploaded by user.",
                "ocr_text": r["extracted_text"] or "",
            })
        return images
