"""
Image resources for AccessAI MCP Server.
URI format: accessai://images/{id}
"""

from typing import Dict, Any, Optional
from ...database import get_db


def get_image_resource(img_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, kind, file_path, extracted_text, image_description FROM attachments WHERE id = ?",
            (img_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Image {img_id} not found.")

        meta = dict(row)
        return {
            "id": meta["id"],
            "name": meta["name"],
            "description": meta["image_description"] or "",
            "ocr_text": meta["extracted_text"] or "",
        }
