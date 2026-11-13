import os
import io
import re
import subprocess
import tempfile
import logging
import wave
import struct
import math
import gc
from pathlib import Path
from typing import Optional
from ..config import AUDIO_DIR, GROQ_API_KEY

logger = logging.getLogger(__name__)

# Cache for local Whisper model (bounded to at most 1 active model)
_whisper_cache = {}

def _apply_av_patch():
    try:
        import av
        if hasattr(av, "open"):
            _orig_av_open = av.open
            def _safe_av_open(*args, **kwargs):
                kwargs.pop("metadata_errors", None)
                kwargs.pop("metadata_encoding", None)
                return _orig_av_open(*args, **kwargs)
            av.open = _safe_av_open
    except Exception:
        pass

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
        
        # 1. Fast zero-RAM cloud transcription via Groq Audio API
        if GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=GROQ_API_KEY)
                with open(file_path, "rb") as f:
                    resp = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=(os.path.basename(file_path), f),
                        language=language if language and language != "auto" else None,
                    )
                if resp and hasattr(resp, "text") and resp.text.strip():
                    return resp.text.strip()
            except Exception as e:
                logger.warning("Groq audio transcription failed, falling back to local faster-whisper: %s", e)

        # 2. Local fallback using faster-whisper with bounded memory cache
        try:
            _apply_av_patch()
            from faster_whisper import WhisperModel

            if model_size not in _whisper_cache:
                _whisper_cache.clear()
                gc.collect()
                logger.info("Loading local Whisper model: %s", model_size)
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
        1. Uses cross-platform gTTS + PyAV conversion (works on Render, Linux, Docker, Windows).
        2. Falls back to macOS native `say` + `afconvert` if local on macOS.
        3. Falls back to acoustic sine-wave PCM generation if offline.
        """
        if not text or not text.strip():
            text = "Ready."

        # Clean markdown formatting for natural reading
        clean_text = re.sub(r"[\*\_#`\[\]]", "", text).strip() or text

        # 1. Cross-platform gTTS (Linux / Render / Cloud)
        try:
            from gtts import gTTS
            import av

            tld = "co.uk" if any(k in voice for k in ["uk", "emma", "george", "bf_"]) else "com"
            tts = gTTS(text=clean_text[:2500], lang="en", tld=tld, slow=(speed < 0.85))

            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)

            input_container = av.open(mp3_fp, format="mp3")
            wav_fp = io.BytesIO()
            output_container = av.open(wav_fp, mode="w", format="wav")
            out_stream = output_container.add_stream("pcm_s16le", rate=24000)

            for frame in input_container.decode(audio=0):
                for packet in out_stream.encode(frame):
                    output_container.mux(packet)
            for packet in out_stream.encode():
                output_container.mux(packet)

            output_container.close()
            input_container.close()

            wav_bytes = wav_fp.getvalue()
            if len(wav_bytes) > 44 and wav_bytes[:4] == b"RIFF":
                return wav_bytes
        except Exception as e:
            logger.warning("gTTS synthesis unavailable or offline, falling back: %s", e)

        # 2. Try macOS native `say` and `afconvert` if available
        if os.path.exists("/usr/bin/say") and os.path.exists("/usr/bin/afconvert"):
            mac_voice = VOICE_MAP.get(voice, "Samantha")
            rate = max(80, min(360, int(180 * float(speed or 1.0))))

            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as aiff_tmp:
                aiff_path = aiff_tmp.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
                wav_path = wav_tmp.name

            try:
                say_proc = subprocess.run(
                    ["/usr/bin/say", "-v", mac_voice, "-r", str(rate), clean_text, "-o", aiff_path],
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
                            return f.read()
            except Exception as e:
                logger.warning("macOS say/afconvert failed: %s", e)
            finally:
                for p in (aiff_path, wav_path):
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass

        # 3. Python-native fallback WAV generator
        return SpeechService._generate_fallback_wav(clean_text)

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
