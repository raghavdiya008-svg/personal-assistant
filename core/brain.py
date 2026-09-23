"""
Cognitive Cascade Router for Project JARVIS.

Routes requests across a tri-provider fallback chain:
  1. Groq (primary, cloud free tier)
  2. Ollama local 7B/8B (secondary, unlimited if GPU present)
  3. Gemini Flash (tertiary, Google free tier multimodal)

Real task classification is performed BEFORE model dispatch:
  FAST   -> dialogue, FAQ, email formatting, calendar checks  -> Groq 8B
  DEEP   -> strategy, code, negotiation, structured JSON      -> Groq 70B
  VISION -> document reading, screen/image analysis           -> Gemini Flash
"""

import json
import logging
from typing import Any, Dict, List, Optional
from core.config import settings

logger = logging.getLogger("JARVIS.Brain")


class CognitiveBrain:
    """
    Intelligent model router with real task classification and tri-provider fallback.
    Decision flow: classify task -> pick model tier -> try Groq -> Ollama -> Gemini
    """

    FAST_KEYWORDS = {"hello", "hi", "thanks", "price", "pricing", "schedule",
                     "when", "where", "what time", "confirm", "email", "send"}

    def __init__(self):
        self._groq_client = None
        self._gemini_client = None
        self._ollama_available = False
        self._init_clients()

    def classify_task(self, text: str) -> str:
        """
        Real classifier: returns FAST, DEEP, or VISION bucket.
        FAST  -> simple dialogue, FAQ, formatting, calendar
        DEEP  -> strategy, negotiation, code, JSON extraction
        VISION -> image or screen analysis (requires image_bytes input)
        """
        lower = text.lower()
        deep_signals = ["analyze", "strategy", "code", "write a", "negotiate",
                        "compare", "extract json", "reason", "plan", "evaluate",
                        "complex", "detailed", "generate a proposal"]
        if any(sig in lower for sig in deep_signals):
            return "DEEP"
        if any(kw in lower for kw in self.FAST_KEYWORDS) or len(text) < 120:
            return "FAST"
        return "DEEP"  # default to deep for ambiguous longer inputs

    def _init_clients(self):
        """Lazy initialize model clients across all three provider tiers."""
        if settings.GROQ_API_KEY:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("Groq client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

        # Probe for local Ollama as secondary free provider
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1)
            self._ollama_available = True
            logger.info("Ollama local server detected — will use as secondary fallback.")
        except Exception:
            self._ollama_available = False
            logger.debug("Ollama not running locally. Skipping as secondary provider.")

        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Gemini client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    async def _ollama_fallback(self, prompt: str, system_prompt: str) -> str:
        """Secondary fallback: local Ollama 7B/8B model (unlimited, free, offline)."""
        if not self._ollama_available:
            return ""
        try:
            import json as _json
            import urllib.request as _req
            payload = _json.dumps({
                "model": "llama3.1:8b",
                "prompt": f"System: {system_prompt}\n\nUser: {prompt}",
                "stream": False
            }).encode()
            r = _req.urlopen(
                _req.Request("http://localhost:11434/api/generate",
                             data=payload, method="POST"), timeout=30
            )
            data = _json.loads(r.read())
            return data.get("response", "")
        except Exception as e:
            logger.warning(f"Ollama fallback failed: {e}")
            return ""

    async def reflex(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Fast Reflex: Uses Groq fast model for conversational speed.
        Realistic round-trip target: 250–500ms on free tier.
        Fallback chain: Groq -> Ollama local -> Gemini Flash.
        """
        import asyncio
        default_sys = "You are JARVIS, an AI executive assistant. Be concise, clear, and professional."
        sys_content = system_prompt or default_sys

        if self._groq_client:
            try:
                messages = [
                    {"role": "system", "content": sys_content},
                    {"role": "user", "content": prompt},
                ]
                def _call_groq():
                    return self._groq_client.chat.completions.create(
                        model=settings.FAST_MODEL,
                        messages=messages,
                        temperature=0.6,
                        max_tokens=500,
                    )
                response = await asyncio.to_thread(_call_groq)
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"Groq Reflex failed, trying Ollama: {e}")

        # Secondary fallback: local Ollama (unlimited, no rate limits)
        ollama_result = await self._ollama_fallback(prompt, sys_content)
        if ollama_result:
            return ollama_result

        # Tertiary fallback: Gemini Flash free tier
        return await self._gemini_fallback(prompt, sys_content)


    async def reason(
        self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False
    ) -> str:
        """
        Deep Reasoning: High intelligence for strategy, negotiations, and code.
        Fallback chain: Groq 70B -> Ollama local -> Gemini Flash.
        """
        import asyncio
        default_sys = (
            "You are JARVIS's Chief Strategy & Reasoning Core. "
            "Think deeply, be rigorous, structured, and prioritize high-value business outcomes."
        )
        sys_content = system_prompt or default_sys

        if self._groq_client:
            try:
                messages = [
                    {"role": "system", "content": sys_content},
                    {"role": "user", "content": prompt},
                ]
                kwargs = {
                    "model": settings.REASONING_MODEL,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2048,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                def _call_groq():
                    return self._groq_client.chat.completions.create(**kwargs)
                response = await asyncio.to_thread(_call_groq)
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"Groq Reason failed, trying Ollama: {e}")

        # Secondary fallback: local Ollama (same chain as reflex)
        ollama_result = await self._ollama_fallback(prompt, sys_content)
        if ollama_result:
            return ollama_result

        # Tertiary fallback: Gemini Flash
        return await self._gemini_fallback(prompt, sys_content)

    async def auto(self, prompt: str, system_prompt: Optional[str] = None,
                   image_bytes: Optional[bytes] = None) -> str:
        """
        Intelligent auto-router. Classifies the task and dispatches to the
        appropriate model tier automatically.

        This is the recommended entry point for callers who don't want to
        manually choose between reflex() / reason() / vision().
        """
        if image_bytes:
            return await self.vision(prompt, image_bytes)

        bucket = self.classify_task(prompt)
        logger.debug(f"Task classified as [{bucket}] for: '{prompt[:60]}...'")

        if bucket == "FAST":
            return await self.reflex(prompt, system_prompt)
        else:  # DEEP
            return await self.reason(prompt, system_prompt)


    async def vision(self, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """
        Multimodal Eyes: Analyze screens, documents, slides, and webcam frames.
        """
        import asyncio
        if self._gemini_client:
            try:
                from google.genai import types

                def _call_gemini():
                    return self._gemini_client.models.generate_content(
                        model=settings.MULTIMODAL_MODEL,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            prompt,
                        ],
                    )
                response = await asyncio.to_thread(_call_gemini)
                return response.text or ""
            except Exception as e:
                logger.error(f"Gemini Vision call failed: {e}")
                return f"[Vision Error: {e}]"

        return "[Vision Unavailable: GEMINI_API_KEY not configured]"

    async def _gemini_fallback(self, prompt: str, system_prompt: str) -> str:
        """Fallback executor using Google Gemini API."""
        import asyncio
        if self._gemini_client:
            try:
                full_prompt = f"Instructions: {system_prompt}\n\nTask: {prompt}" if system_prompt else prompt
                def _call_gemini():
                    return self._gemini_client.models.generate_content(
                        model=settings.MULTIMODAL_MODEL,
                        contents=full_prompt,
                    )
                response = await asyncio.to_thread(_call_gemini)
                return response.text or ""
            except Exception as e:
                logger.error(f"Gemini fallback also failed: {e}")

        # Mock fallback for test/offline environments
        return f"[JARVIS Offline Mock Response to: '{prompt[:50]}...']"


# Singleton brain instance
brain = CognitiveBrain()
