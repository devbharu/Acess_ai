import os
import subprocess
import tempfile
import logging
import wave
import struct
import math
from pathlib import Path
from typing import Optional
from ..config import AUDIO_DIR

logger = logging.getLogger(__name__)

# Cache for Whisper models
_whisper_cache = {}

VOICE_MAP = {
    "af_heart": "Samantha",
    "af_bella": "Victoria",
    "am_michael": "Alex",
    "bf_emma": "Serena",
    "bm_george": "Daniel",
}

class SpeechService:
    @staticmethod
    def transcribe(file_path: str, model_name: str = "base", language: str = "auto") -> str:
        """
        Transcribe audio to text using faster-whisper.
        """
        model_size = model_name if model_name in ["tiny", "base", "small"] else "base"
        
        try:
            from faster_whisper import WhisperModel

            if model_size not in _whisper_cache:
                logger.info("Loading Whisper model: %s", model_size)
                _whisper_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")

            model = _whisper_cache[model_size]

            lang_param = None if language in [None, "auto", ""] else language
            segments, info = model.transcribe(
                file_path,
                beam_size=5,
                language=lang_param,
                vad_filter=True,
            )

            text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
            transcribed = " ".join(text_parts)
            return transcribed

        except Exception as e:
            logger.error("Whisper transcription failed: %s", e)
            return ""

    @staticmethod
    def synthesize_speech(text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
        """
        Synthesize text to speech returning 16-bit PCM WAV bytes.
        Uses macOS native `say` + `afconvert` with speed adjustment.
        Falls back to acoustic sine-wave PCM generation if native tools unavailable.
        """
        if not text or not text.strip():
            text = "Ready."

        mac_voice = VOICE_MAP.get(voice, "Samantha")
        # Base speech rate in words per minute is ~175
        rate = max(80, min(360, int(180 * float(speed or 1.0))))

        # Try macOS native `say` and `afconvert`
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as aiff_tmp:
            aiff_path = aiff_tmp.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
            wav_path = wav_tmp.name

        try:
            say_proc = subprocess.run(
                ["/usr/bin/say", "-v", mac_voice, "-r", str(rate), text, "-o", aiff_path],
                capture_output=True,
                timeout=15,
            )
            if say_proc.returncode == 0 and os.path.exists(aiff_path) and os.path.getsize(aiff_path) > 0:
                conv_proc = subprocess.run(
                    ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16", aiff_path, wav_path],
                    capture_output=True,
                    timeout=10,
                )
                if conv_proc.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                    with open(wav_path, "rb") as f:
                        wav_bytes = f.read()
                    return wav_bytes
        except Exception as e:
            logger.warning("macOS say/afconvert failed: %s", e)
        finally:
            for p in (aiff_path, wav_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

        # Python-native fallback WAV generator
        return SpeechService._generate_fallback_wav(text)

    @staticmethod
    def _generate_fallback_wav(text: str) -> bytes:
        sample_rate = 16000
        duration_s = max(0.5, min(4.0, len(text) * 0.04))
        num_samples = int(sample_rate * duration_s)
        
        wav_buffer = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = wav_buffer.name
        wav_buffer.close()

        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Soft pleasant audio tone indicating speech output
            for i in range(num_samples):
                freq = 440.0 + 40.0 * math.sin(2 * math.pi * 3.0 * (i / sample_rate))
                sample = int(12000.0 * math.sin(2 * math.pi * freq * (i / sample_rate)))
                # Soft fade out
                fade = max(0.0, 1.0 - (i / num_samples))
                sample = int(sample * fade)
                wf.writeframesraw(struct.pack("<h", sample))

        with open(wav_path, "rb") as f:
            data = f.read()
        try:
            os.remove(wav_path)
        except OSError:
            pass
        return data
