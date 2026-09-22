"""
Speech-to-Text (STT) Engine for Project JARVIS.
Uses Groq Whisper API (whisper-large-v3) for near-instant transcription (<150ms).
"""

import io
import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger("JARVIS.STT")


class SpeechToText:
    """Ultra-fast audio transcription engine."""

    def __init__(self):
        self._groq_client = None
        self._init_client()

    def _init_client(self):
        if settings.GROQ_API_KEY:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
            except Exception as e:
                logger.warning(f"Groq STT client init failed: {e}")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribe raw audio bytes to text."""
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        if self._groq_client:
            try:
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = filename
                
                transcription = self._groq_client.audio.transcriptions.create(
                    file=(filename, audio_file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    temperature=0.0
                )
                text = str(transcription).strip()
                logger.debug(f"Transcribed audio: '{text}'")
                return text
            except Exception as e:
                logger.error(f"Groq Whisper transcription failed: {e}")

        return "[Audio transcription unavailable without GROQ_API_KEY]"


stt = SpeechToText()
