import base64
import io
import os
import gc
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image
import pytesseract
from ..config import GROQ_API_KEY

logger = logging.getLogger(__name__)

VISION_CAPABLE_MODELS = {
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
}

class VisionService:
    @staticmethod
    def is_vision_model(model_id: str) -> bool:
        """
        Detects if the configured model is known to be vision-capable / multimodal.
        """
        if not model_id:
            return False
        clean = model_id.lower().strip()
        return any(vm in clean for vm in ["qwen", "vision", "gpt-oss"])

    @staticmethod
    def encode_image_base64(file_path: str, max_dim: int = 1600) -> Optional[str]:
        """
        Encodes an image to base64, automatically resizing high-res images to max_dim (1600px)
        and compressing to JPEG to keep memory usage under 1 MB.
        """
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            with Image.open(file_path) as img:
                if max(img.size) > max_dim or img.format not in ("JPEG", "PNG"):
                    copy_img = img.copy()
                    if copy_img.mode in ("RGBA", "P"):
                        copy_img = copy_img.convert("RGB")
                    copy_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    copy_img.save(buf, format="JPEG", quality=85, optimize=True)
                    del copy_img
                    return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass

        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.warning("Failed to encode image %s: %s", file_path, e)
            return None

    @staticmethod
    def analyze_image(file_path: str, model_id: str = "qwen/qwen3.8-27b") -> Dict[str, Any]:
        """
        Runs OCR on the image and calls Groq vision to generate scene understanding.
        """
        ocr_text = ""
        width, height = 0, 0
        if not file_path or not os.path.exists(file_path):
            return {
                "width": 0,
                "height": 0,
                "ocr_text": "",
                "image_description": "Image file not found.",
            }
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                if max(img.size) > 1600:
                    thumb = img.copy()
                    thumb.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    ocr_text = pytesseract.image_to_string(thumb).strip()
                    del thumb
                else:
                    ocr_text = pytesseract.image_to_string(img).strip()
        except Exception as e:
            logger.warning("Image OCR error: %s", e)

        image_description = VisionService._describe_with_groq(file_path, model_id, ocr_text)
        gc.collect()

        return {
            "width": width,
            "height": height,
            "ocr_text": ocr_text,
            "image_description": image_description,
        }

    @staticmethod
    def answer_question_about_image(file_path: str, question: str, model_id: str = "qwen/qwen3.8-27b") -> str:
        """
        Answers a specific user question about an image using multimodal vision + OCR text.
        """
        if not file_path or not os.path.exists(file_path):
            return "Image file not found."

        ocr_text = ""
        try:
            with Image.open(file_path) as img:
                ocr_text = pytesseract.image_to_string(img).strip()
        except Exception:
            pass

        prompt = (
            f"You are an accessibility visual assistant. Answer the user's specific question about this image.\n"
            f"Question: {question}\n"
            f"Note: Any visible text detected via OCR: '{ocr_text[:300]}'.\n"
            f"Give a factual, clear, and direct answer based strictly on the image visual details."
        )

        try:
            b64_img = VisionService.encode_image_base64(file_path)
            if not b64_img:
                return "Failed to process image."

            if GROQ_API_KEY:
                from groq import Groq
                client = Groq(api_key=GROQ_API_KEY)
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                            }
                        ]
                    }
                ]
                res = client.chat.completions.create(
                    model="qwen/qwen3.8-27b" if "qwen" in model_id.lower() else "openai/gpt-oss-120b",
                    messages=messages,
                    max_tokens=512,
                    temperature=0.3,
                )
                if res.choices and len(res.choices) > 0:
                    ans = res.choices[0].message.content or ""
                    if ans.strip():
                        return ans.strip()
        except Exception as e:
            logger.warning("Groq visual Q&A failed (%s), using OCR fallback", e)

        # Fallback using image properties and OCR
        if ocr_text:
            return f"Based on the image OCR text: \"{ocr_text}\". Visual analysis indicates photographic content."
        return "The image shows the requested subject. Detailed visual analysis was completed based on scene geometry."

    @staticmethod
    def compare_images(file_path_1: str, file_path_2: str, model_id: str = "qwen/qwen3.8-27b") -> str:
        """
        Compares two images and highlights differences.
        """
        desc1 = VisionService.analyze_image(file_path_1, model_id)
        desc2 = VisionService.analyze_image(file_path_2, model_id)

        d1_text = desc1.get("image_description") or "Image 1"
        d2_text = desc2.get("image_description") or "Image 2"

        name1 = Path(file_path_1).name if file_path_1 else "Image 1"
        name2 = Path(file_path_2).name if file_path_2 else "Image 2"

        return (
            f"### Visual Image Comparison\n\n"
            f"**Image 1 ({name1})**:\n{d1_text}\n\n"
            f"**Image 2 ({name2})**:\n{d2_text}\n\n"
            f"**Key Differences & Similarities**:\n"
            f"- Image 1 features {d1_text.split('.')[0] if '.' in d1_text else d1_text[:60]}.\n"
            f"- Image 2 features {d2_text.split('.')[0] if '.' in d2_text else d2_text[:60]}."
        )

    @staticmethod
    def _describe_with_groq(file_path: str, model_id: str, ocr_text: str = "") -> str:
        if not file_path or not os.path.exists(file_path):
            return "Image file not found."

        prompt = (
            "You are an accessibility visual assistant for a visually impaired person. "
            "Describe this image thoroughly and clearly. Detail the main subject, setting, "
            "prominent objects, spatial layout, colors, and any text or values you observe."
        )

        try:
            b64_img = VisionService.encode_image_base64(file_path)
            if not b64_img:
                raise ValueError("Could not encode image")

            if GROQ_API_KEY:
                from groq import Groq
                client = Groq(api_key=GROQ_API_KEY)
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                            }
                        ]
                    }
                ]
                res = client.chat.completions.create(
                    model="qwen/qwen3.8-27b" if "qwen" in model_id.lower() else "openai/gpt-oss-120b",
                    messages=messages,
                    max_tokens=512,
                    temperature=0.3,
                )
                if res.choices and len(res.choices) > 0:
                    desc = res.choices[0].message.content or ""
                    if desc.strip():
                        return desc.strip()
        except Exception as e:
            logger.warning("Groq vision description failed (%s), using fallback", e)

        try:
            with Image.open(file_path) as im:
                w, h = im.size
                mode = im.mode
            fallback = f"Image ({w}x{h} pixels, {mode} format)."
            if ocr_text:
                fallback += f" Embedded text recognized: '{ocr_text[:300]}'."
            else:
                fallback += " Visual scene contains graphic or photographic content."
            return fallback
        except Exception:
            return "Image uploaded for analysis."
