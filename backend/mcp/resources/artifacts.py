"""
Artifact resources for AccessAI MCP Server.
URI format: accessai://artifacts/{id}
"""

from typing import Dict, Any, Optional
from ...database import get_db


def get_artifact_resource(art_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, kind, file_size, pages, summary_text, created_at FROM artifacts WHERE id = ?",
            (art_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Artifact {art_id} not found.")

        meta = dict(row)
        return {
            "id": meta["id"],
            "title": meta["title"],
            "kind": meta["kind"],
            "file_size": meta["file_size"],
            "pages": meta["pages"],
            "summary": meta["summary_text"] or "",
            "download_url": f"/api/artifacts/{meta['id']}/download",
        }
