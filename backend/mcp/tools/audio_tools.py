"""
Speech recognition (STT) and voice synthesis (TTS) MCP tools.
"""

import os
import uuid
from typing import Dict, Any
from ...config import AUDIO_DIR
from ...services.speech_service import SpeechService


def text_to_speech(text: str, user_id: str, voice: str = "af_heart", speed: float = 1.0) -> Dict[str, Any]:
    """
    Synthesizes text into high-fidelity 16-bit PCM WAV audio.
    """
    audio_id = f"aud_{uuid.uuid4().hex[:10]}"
    out_file = str(AUDIO_DIR / f"{audio_id}.wav")

    wav_bytes = SpeechService.synthesize_speech(text, voice=voice, speed=speed)
    with open(out_file, "wb") as f:
        f.write(wav_bytes)

    return {
        "audio_id": audio_id,
        "audio_url": f"/api/audio/{audio_id}.wav",
        "available": True,
        "duration_seconds": None,
    }


def speech_to_text(audio_id: str, user_id: str, language: str = "auto") -> Dict[str, Any]:
    """
    Transcribes spoken audio recordings into text using Faster-Whisper.
    """
    audio_path = str(AUDIO_DIR / f"{audio_id}.wav")
    if not os.path.exists(audio_path):
        audio_path = str(AUDIO_DIR / f"{audio_id}.webm")

    if not os.path.exists(audio_path):
        raise ValueError(f"Audio record {audio_id} not found.")

    text = SpeechService.transcribe(audio_path, language=language)
    return {
        "transcript": text,
        "language": language,
        "audio_id": audio_id,
    }
