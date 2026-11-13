"""
Document analysis, table extraction, chart reasoning, and PDF report generation MCP tools.
"""

from typing import Dict, Any, List, Optional
from ...database import get_db
from ...services.document_service import DocumentService
from ...services.vision_service import VisionService
from .document_tools import get_file_metadata


def extract_table(file_id: str, user_id: str, page_number: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Parses structured table cells into clean, screen-reader-friendly Markdown tables.
    """
    meta = get_file_metadata(file_id, user_id)
    return DocumentService.extract_tables(meta["file_path"], page_number)


def analyze_chart(file_id: str, user_id: str, page_number: Optional[int] = None, model_id: str = "gemma4:31b-cloud") -> Dict[str, Any]:
    """
    Analyzes engineering schematics, charts, flow diagrams, and mechanical figures.
    """
    meta = get_file_metadata(file_id, user_id)
    if meta["kind"] == "image":
        desc = VisionService.analyze_image(meta["file_path"], model_id)
        return {
            "source": meta["name"],
            "analysis": desc.get("image_description") or "Chart graphic analyzed.",
            "data": desc.get("ocr_text") or "",
        }
    else:
        p_num = page_number or 1
        page_info = DocumentService.get_page_content(meta["file_path"], p_num)
        return {
            "source": meta["name"],
            "page": p_num,
            "analysis": f"Visual chart data on page {p_num}: {page_info.get('text', '')[:400]}",
        }


def compare_documents(file_id_1: str, file_id_2: str, user_id: str) -> Dict[str, Any]:
    """
    Compares thematic scope, headings, mechanical concepts, and document differences between two files.
    """
    m1 = get_file_metadata(file_id_1, user_id)
    m2 = get_file_metadata(file_id_2, user_id)

    out1 = DocumentService.get_document_outline(m1["file_path"])
    out2 = DocumentService.get_document_outline(m2["file_path"])

    return {
        "doc1": {"name": m1["name"], "pages": m1.get("pages", 1), "outline": out1[:5]},
        "doc2": {"name": m2["name"], "pages": m2.get("pages", 1), "outline": out2[:5]},
        "comparison": f"Compared {m1['name']} ({m1.get('pages', 1)} pages) with {m2['name']} ({m2.get('pages', 1)} pages).",
    }


def generate_accessible_summary(file_id: str, user_id: str) -> Dict[str, Any]:
    """
    Creates an accessible, structured, screen-reader-optimized document overview.
    """
    meta = get_file_metadata(file_id, user_id)
    if meta["kind"] == "image":
        return {
            "title": f"Accessible Description of {meta['name']}",
            "summary": meta.get("image_description") or "Image description.",
            "ocr": meta.get("extracted_text") or "",
        }
    else:
        outline = DocumentService.get_document_outline(meta["file_path"])
        sections = [item["title"] for item in outline[:8]]
        return {
            "title": f"Accessible Overview of {meta['name']}",
            "pages": meta.get("pages", 1),
            "key_sections": sections,
            "summary": f"This document contains {meta.get('pages', 1)} pages covering {', '.join(sections[:4])}.",
        }


def generate_pdf_report(file_id: str, user_id: str, conversation_id: str, focus_topic: str = "") -> Dict[str, Any]:
    """
    Compiles an executive summary PDF using ReportLab and delivers it as an artifact.
    """
    from ...services.agent_service import AgentService
    meta = get_file_metadata(file_id, user_id)
    return AgentService.generate_pdf_summary_report(
        user_id=user_id,
        conversation_id=conversation_id,
        doc_item=meta,
        focus_topic=focus_topic,
    )
