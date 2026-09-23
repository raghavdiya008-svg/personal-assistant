"""
Free API Multiplexer & Burst Compute Pool for Project JARVIS v2 (FreeLLMAPI Model).

Manages an opportunistic pool of free-tier upstream providers behind LiteLLM:
  - Groq free tier
  - Google Gemini AI Studio free tier
  - OpenRouter free tier (:free models)
  - Mistral free tier
  - Cohere trial tier
  - HuggingFace Inference API

Handles provider health monitoring, key rotation, and automatic cooldowns.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from core.config import settings

logger = logging.getLogger("JARVIS.FreeLLMAPI")


class FreeProviderEndpoint:
    """Represents a single free model provider endpoint."""

    def __init__(self, name: str, model_id: str, api_key: str, rpm_limit: int = 30):
        self.name = name
        self.model_id = model_id
        self.api_key = api_key
        self.rpm_limit = rpm_limit
        self.cooldown_until: float = 0.0
        self.failure_count: int = 0
        self.total_requests: int = 0

    @property
    def is_available(self) -> bool:
        return bool(self.api_key) and time.time() > self.cooldown_until

    def mark_success(self):
        self.failure_count = 0
        self.total_requests += 1

    def mark_rate_limited(self, cooldown_seconds: float = 60.0):
        self.cooldown_until = time.time() + cooldown_seconds
        self.failure_count += 1
        logger.warning(
            f"⏳ [FREELLMAPI COOLDOWN] Provider '{self.name}' rate limited. "
            f"Cooling down for {cooldown_seconds}s."
        )


class FreeAPIMultiplexer:
    """
    Opportunistic burst pool multiplexer.
    Routes non-critical background batch tasks across free providers to conserve paid quotas.
    """

    def __init__(self):
        self.endpoints: List[FreeProviderEndpoint] = []
        self._init_burst_pool()

    def _init_burst_pool(self):
        if settings.GROQ_API_KEY:
            self.endpoints.append(
                FreeProviderEndpoint("groq_qwen27b", "qwen/qwen3.8-27b", settings.GROQ_API_KEY, rpm_limit=30)
            )
        if settings.GEMINI_API_KEY:
            self.endpoints.append(
                FreeProviderEndpoint("gemini_flash", "gemini-2.5-flash", settings.GEMINI_API_KEY, rpm_limit=60)
            )
        if settings.OPENROUTER_API_KEY:
            self.endpoints.append(
                FreeProviderEndpoint("openrouter_free", "google/gemini-2.0-flash-exp:free", settings.OPENROUTER_API_KEY, rpm_limit=20)
            )
        if settings.MISTRAL_API_KEY:
            self.endpoints.append(
                FreeProviderEndpoint("mistral_free", "mistral-small-latest", settings.MISTRAL_API_KEY, rpm_limit=30)
            )
        if settings.COHERE_API_KEY:
            self.endpoints.append(
                FreeProviderEndpoint("cohere_trial", "command-r", settings.COHERE_API_KEY, rpm_limit=20)
            )

    def get_available_provider(self) -> Optional[FreeProviderEndpoint]:
        """Select next healthy free provider with round-robin or least failure count."""
        available = [ep for ep in self.endpoints if ep.is_available]
        if not available:
            return None
        # Prioritize provider with fewest failures
        available.sort(key=lambda ep: (ep.failure_count, ep.total_requests))
        return available[0]

    def get_pool_status(self) -> List[Dict[str, Any]]:
        return [
            {
                "provider": ep.name,
                "model": ep.model_id,
                "available": ep.is_available,
                "cooldown_remaining_sec": max(0.0, round(ep.cooldown_until - time.time(), 1)),
                "total_requests": ep.total_requests,
                "failures": ep.failure_count,
            }
            for ep in self.endpoints
        ]


# Singleton instance
freellmapi_pool = FreeAPIMultiplexer()
