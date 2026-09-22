"""
Text-to-Speech (TTS) Engine for Project JARVIS.

Uses Microsoft Edge Neural TTS (edge-tts) for LOCAL DEVELOPMENT ONLY.

RISK WARNING: edge-tts is an unofficial, reverse-engineered wrapper around Microsoft
Edge's read-aloud feature — NOT a published API. It can break without notice on any
Edge update, and its ToS status is ambiguous. Do NOT use as a production dependency.

For PRODUCTION, replace with:
  - Kokoro-82M (Apache 2.0, open source, high quality): pip install kokoro
  - Piper TTS (MIT, open source, offline): https://github.com/rhasspy/piper
  - Coqui XTTS v2 (CPML, supports voice cloning): pip install TTS
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional
import edge_tts
from core.config import settings

logger = logging.getLogger("JARVIS.TTS")


class TextToSpeech:
    """Free high-fidelity neural voice synthesis engine."""

    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or settings.VOICE_NAME

    async def speak_to_file(self, text: str, output_path: Optional[str] = None) -> str:
        """Synthesize text to an audio file (MP3)."""
        if not text:
            return ""

        if not output_path:
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            output_path = str(settings.AUDIO_DIR / filename)

        try:
            communicate = edge_tts.Communicate(text=text, voice=self.voice, rate="+5%", pitch="+0Hz")
            await communicate.save(output_path)
            logger.debug(f"Synthesized voice to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"TTS Synthesis error: {e}")
            return ""

    async def synthesize_bytes(self, text: str) -> bytes:
        """Synthesize text directly to in-memory MP3 bytes."""
        if not text:
            return b""
        try:
            communicate = edge_tts.Communicate(text=text, voice=self.voice)
            chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)
        except Exception as e:
            logger.error(f"TTS Stream error: {e}")
            return b""

    @staticmethod
    def cleanup_cache(max_age_hours: int = 24) -> int:
        """Purge temporary synthesized audio files older than max_age_hours to prevent disk accumulation."""
        import time
        deleted_count = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cache_dir = settings.AUDIO_DIR
        if cache_dir.exists():
            for p in cache_dir.glob("*.*"):
                try:
                    if p.is_file() and (now - p.stat().st_mtime > max_age_seconds):
                        p.unlink()
                        deleted_count += 1
                except Exception as e:
                    logger.debug(f"Failed to remove cached audio {p}: {e}")
        if deleted_count:
            logger.info(f"Cleaned up {deleted_count} expired audio cache files.")
        return deleted_count


tts = TextToSpeech()

