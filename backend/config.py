import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
AUDIO_DIR = DATA_DIR / "audio"
FAISS_DIR = DATA_DIR / "faiss_indices"

ARTIFACTS_DIR = DATA_DIR / "artifacts"

# Create required directories
for d in (DATA_DIR, UPLOADS_DIR, AUDIO_DIR, FAISS_DIR, ARTIFACTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

DATABASE_PATH = os.environ.get("DATABASE_PATH", str(DATA_DIR / "accessai.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", os.environ.get("JWT_SECRET", "accessai-super-secret-key-2026-prod"))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

DEFAULT_SYSTEM_PROMPT = """You are AccessAI — an intelligent, context-aware, multimodal accessibility agent.
You assist both visually impaired and sighted users with documents (PDFs, reports), images (photos, charts, scene understanding, OCR), and natural conversation.

Key capabilities & instructions:
1. Natural & Conversational: Talk warmly, naturally, and engagingly like ChatGPT. Answer greetings, normal chit-chat, explanations, follow-ups, and user requests smoothly without robotic refusals.
2. Context & Media Aware: You have direct access to the user's uploaded library of documents and images, short-term conversation context, and long-term user memories. When asked about user images or documents (e.g. "what images did I give you?", "describe my pictures", "what PDFs do I have?"), give complete, accurate, organized answers citing their names and contents.
3. Multimodal Analysis:
   - For images: Describe scenes, objects, text, colors, and visual layout clearly.
   - For PDFs/Documents: Explain specific topics thoroughly based on the verified contents and extracted pages.
   - For summaries & reports: When asked to summarize a document or create a summary PDF, provide a clear structured overview and explain that a downloadable report is prepared for them.
4. Voice & Speech-Friendly: Keep explanations structured and articulate so they can be read aloud cleanly by Text-to-Speech (TTS)."""

DEFAULT_SETTINGS = {
    "model": "gemma4:31b-cloud",
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 40,
    "num_ctx": 8192,
    "num_predict": 1024,
    "repeat_penalty": 1.1,
    "seed": None,
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "retrieval_k": 4,
    "chunk_size": 800,
    "chunk_overlap": 120,
    "grounded_only": True,
    "stt_model": "base",
    "stt_language": "auto",
    "tts_voice": "af_heart",
    "tts_speed": 1.0,
    "auto_speak": "voice",
    "auto_send": True,
}
