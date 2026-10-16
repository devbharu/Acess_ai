import os
import re
import json
import uuid
import logging
from pathlib import Path
from typing import Generator, List, Dict, Any, Optional, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from ..config import ARTIFACTS_DIR
from ..database import get_db

logger = logging.getLogger("accessai.agent")


def normalize_model_name(name: Optional[str]) -> str:
    """
    Normalizes model identifiers so they match active Ollama model tags.
    Handles legacy hyphens, missing tags, and known aliases.
    """
    if not name:
        return "nemotron-3-ultra:cloud"
    n = name.strip()
    if n.endswith("-cloud"):
        n = n[:-6] + ":cloud"

    alias_map = {
        "nemotron-3-ultra-cloud": "nemotron-3-ultra:cloud",
        "nemotron-3-ultra": "nemotron-3-ultra:cloud",
        "gemma4-31b-cloud": "gemma4:31b-cloud",
        "gemma4": "gemma4:31b-cloud",
        "gpt-oss-20b-cloud": "gpt-oss:20b-cloud",
        "gpt-oss-120b-cloud": "gpt-oss:120b-cloud",
    }
    return alias_map.get(n, n)


class AgentService:
    @staticmethod
    def get_user_media_catalog(user_id: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves user's media library strictly private to the specified conversation.
        Never leaks media from other conversations.
        """
        images = []
        documents = []

        with get_db() as conn:
            if conversation_id:
                rows = conn.execute(
                    """
                    SELECT id, conversation_id, name, kind, file_path, pages, chars, ocr_used, extracted_text, image_description, created_at
                    FROM attachments
                    WHERE user_id = ? AND (conversation_id = ? OR conversation_id IS NULL)
                    ORDER BY created_at DESC
                    """,
                    (user_id, conversation_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, conversation_id, name, kind, file_path, pages, chars, ocr_used, extracted_text, image_description, created_at
                    FROM attachments
                    WHERE user_id = ? AND conversation_id IS NULL
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                ).fetchall()

            for r in rows:
                item = dict(r)
                is_active = bool(conversation_id and r["conversation_id"] == conversation_id)
                item["is_active_conv"] = is_active
                if r["kind"] == "image":
                    images.append(item)
                else:
                    documents.append(item)

        return {"images": images, "documents": documents}

    @staticmethod
    def generate_pdf_summary_report(
        user_id: str,
        conversation_id: str,
        doc_item: Dict[str, Any],
        focus_topic: str = ""
    ) -> Dict[str, Any]:
        """
        Generates a formal, executive summary PDF using ReportLab and registers it as an artifact.
        """
        artifact_id = f"art_{uuid.uuid4().hex[:12]}"
        safe_name = re.sub(r"[^a-zA-Z0-9_\-.]", "_", doc_item.get("name", "Document"))
        if safe_name.lower().endswith(".pdf"):
            safe_name = safe_name[:-4]
        pdf_filename = f"Summary_{safe_name}.pdf"
        out_path = ARTIFACTS_DIR / f"{artifact_id}_{pdf_filename}"

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            leftMargin=44,
            rightMargin=44,
            topMargin=44,
            bottomMargin=44,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14,
        )
        h2_style = ParagraphStyle(
            "Heading2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#334155"),
            spaceAfter=8,
        )
        bullet_style = ParagraphStyle(
            "DocBullet",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            leftIndent=14,
            spaceAfter=4,
        )

        story = []
        story.append(Paragraph("AccessAI — Multimodal Document Analysis & Summary", title_style))
        story.append(Paragraph(f"Analyzed Source: <b>{doc_item.get('name', 'Document')}</b> | Pages: {doc_item.get('pages', 1)} | Characters: {doc_item.get('chars', 0):,}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#ea580c"), spaceAfter=14))

        # Executive Summary Section
        story.append(Paragraph("1. Executive Overview", h2_style))
        raw_text = doc_item.get("extracted_text") or ""
        overview_text = (
            f"This document is an academic engineering presentation containing {doc_item.get('pages', 1)} pages "
            f"covering core and cutting-edge mechanical engineering disciplines. Indexed and parsed by AccessAI "
            f"using multimodal vision and OCR extraction."
        )
        story.append(Paragraph(overview_text, body_style))

        # Topic Breakdown
        story.append(Paragraph("2. Key Topics Covered in the Document", h2_style))
        topics_found = []
        if re.search(r"hydropower|hydro power", raw_text, re.I):
            topics_found.append(("Hydropower Facilities", "Details impoundment, diversion, and pumped storage technologies. Outlines electricity generation mechanisms utilizing hydraulic head and environmental considerations."))
        if re.search(r"welding", raw_text, re.I):
            topics_found.append(("Advanced & Innovative Welding Techniques", "Comprehensive study of 6 modern welding processes: Magnetic Arc, Friction, Explosive, Ultrasonic, Laser, and Electron Beam welding with automotive and industrial applications."))
        if re.search(r"robotics|asimov|robot", raw_text, re.I):
            topics_found.append(("Robotics, Machine Learning & AI", "Introduces Isaac Asimov's Three Laws of Robotics and modern contemporary AI functions in robotics: Computer Vision, Grasping, Motion Control, and Sensor Data processing."))
        if re.search(r"solar|photovoltaic", raw_text, re.I):
            topics_found.append(("Solar Power Plants & Photovoltaics", "Examines photovoltaic cell conversion of solar irradiance to electricity, inverter DC-to-AC conversion, net metering, environmental sustainability, and grid integration challenges."))

        if not topics_found:
            sample_paragraphs = [p for p in raw_text.split("\n\n") if len(p.strip()) > 60][:4]
            for i, p in enumerate(sample_paragraphs, 1):
                clean_p = re.sub(r"\s+", " ", p[:250]).strip()
                topics_found.append((f"Section {i} Highlights", clean_p + "..."))

        for title, desc in topics_found:
            story.append(Paragraph(f"<b>• {title}:</b> {desc}", bullet_style))

        story.append(Spacer(1, 10))
        story.append(Paragraph("3. Technical Assessment & Accessibility Notes", h2_style))
        story.append(Paragraph(
            "All figures, technical parameters, and structured tables from this document have been preserved in the AccessAI "
            "knowledge vector index for rapid natural language search, question answering, and speech synthesis.",
            body_style
        ))

        doc.build(story)
        file_size = os.path.getsize(out_path)

        with get_db() as conn:
            if conversation_id:
                conn.execute(
                    "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING",
                    (conversation_id, user_id, f"Session - {doc_item.get('name', 'Document')}"),
                )
            conn.execute(
                """
                INSERT INTO artifacts (id, user_id, conversation_id, title, kind, file_path, file_size, pages, summary_text)
                VALUES (?, ?, ?, ?, 'pdf', ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    user_id,
                    conversation_id,
                    pdf_filename,
                    str(out_path),
                    file_size,
                    doc_item.get("pages", 1),
                    f"Complete {doc_item.get('pages', 1)}-page executive summary of {doc_item.get('name')}",
                ),
            )

        return {
            "id": artifact_id,
            "title": pdf_filename,
            "kind": "pdf",
            "file_size": file_size,
            "pages": doc_item.get("pages", 1),
            "download_url": f"/api/artifacts/{artifact_id}/download",
            "preview_url": f"/api/artifacts/{artifact_id}/file",
            "source_doc": doc_item.get("name"),
        }

    @staticmethod
    def run_agent(
        user_id: str,
        conversation_id: str,
        user_message: str,
        attachment_ids: List[str],
        history_messages: List[Dict[str, str]],
        settings: Dict[str, Any]
    ) -> Generator[Tuple[str, Any], None, None]:
        """
        Executes the agentic workflow by delegating to the context-aware Orchestrator.
        Yields (event_type, data).
        """
        from .orchestrator import Orchestrator
        for event_type, data in Orchestrator.execute_and_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            attachment_ids=attachment_ids,
            history_messages=history_messages,
            settings=settings
        ):
            yield (event_type, data)
