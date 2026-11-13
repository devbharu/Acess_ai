"""
Vision, OCR, and image understanding MCP tools.
"""

from typing import Dict, Any, List, Optional
from ...services.vision_service import VisionService
from ...services.document_service import DocumentService
from .document_tools import get_file_metadata


def describe_image(file_id: str, user_id: str, model_id: str = "gemma4:31b-cloud") -> Dict[str, Any]:
    """
    Generates a comprehensive visual scene description combined with OCR text for an image.
    """
    meta = get_file_metadata(file_id, user_id)
    analysis = VisionService.analyze_image(meta["file_path"], model_id=model_id)
    return {
        "file_id": file_id,
        "name": meta["name"],
        "description": analysis.get("image_description") or "Image analyzed.",
        "ocr_text": analysis.get("ocr_text") or "",
        "file_path": meta["file_path"],
    }


def answer_question_about_image(file_id: str, question: str, user_id: str, model_id: str = "gemma4:31b-cloud") -> Dict[str, Any]:
    """
    Answers visual questions about objects, colors, layout, and visible text in an image.
    """
    meta = get_file_metadata(file_id, user_id)
    ans = VisionService.answer_question_about_image(meta["file_path"], question, model_id=model_id)
    return {
        "file_id": file_id,
        "name": meta["name"],
        "question": question,
        "answer": ans,
        "file_path": meta["file_path"],
    }


def extract_image_text(file_id: str, user_id: str) -> Dict[str, Any]:
    """
    Extracts text from an image or screenshot preserving top-to-bottom reading order.
    """
    meta = get_file_metadata(file_id, user_id)
    res = VisionService.analyze_image(meta["file_path"])
    text = res.get("ocr_text") or ""
    return {
        "file_id": file_id,
        "filename": meta["name"],
        "extracted_text": text,
        "uncertain_regions": [],
    }


def get_document_images(file_id: str, user_id: str, page_number: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Extracts and catalogs raster images embedded within document pages.
    """
    meta = get_file_metadata(file_id, user_id)
    return DocumentService.get_document_images(meta["file_path"], page_number=page_number)
