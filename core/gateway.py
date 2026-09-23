"""
LiteLLM Gateway & Resilient Model Router for Project JARVIS v2.

Routes requests through the LiteLLM unified proxy on port 4000 when active,
with graceful in-process fallback to direct Groq/Gemini API calls.
Enforces deterministic task-complexity classification and latency budgets (SLAs).
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
import aiohttp
from core.config import settings
from core.brain import brain

logger = logging.getLogger("JARVIS.Gateway")


class LLMGateway:
    """
    Unified LLM Gateway providing deterministic routing, failover,
    and latency monitoring.
    """

    def __init__(self):
        self.litellm_url = "http://localhost:4000/v1"
        self.master_key = getattr(settings, "LITELLM_MASTER_KEY", "sk-jarvis-gateway-token")

    async def _try_litellm_proxy(
        self,
        model_tier: str,
        messages: list,
        timeout: float = 5.0,
        temperature: float = 0.5,
    ) -> Optional[str]:
        """Attempt completion via LiteLLM proxy container."""
        headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_tier,  # 'reflex', 'reasoning', 'vision'
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.litellm_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.debug(f"LiteLLM proxy returned status {resp.status}")
                        return None
        except Exception as e:
            logger.debug(f"LiteLLM proxy unavailable ({e}); engaging in-process fallback.")
            return None

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tier: str = "reflex",  # 'reflex', 'reasoning', 'vision'
        timeout: Optional[float] = None,
    ) -> str:
        """
        Execute completion with strict latency budgets:
          - reflex: 5.0s budget
          - reasoning: 15.0s budget
        """
        start_time = time.time()
        timeout_budget = timeout or (5.0 if tier == "reflex" else 15.0)

        sys_msg = system_prompt or "You are JARVIS, an autonomous sovereign executive assistant."
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ]

        # 1. Attempt LiteLLM Proxy
        content = await self._try_litellm_proxy(tier, messages, timeout=timeout_budget)
        if content:
            elapsed = time.time() - start_time
            logger.debug(f"Completion from LiteLLM proxy [{tier}] in {elapsed:.2f}s")
            return content

        # 2. In-process Resilient Fallback (Direct Groq -> Gemini -> Ollama)
        if tier == "reflex":
            return await brain.reflex(prompt, system_prompt=sys_msg)
        elif tier == "reasoning":
            return await brain.reason(prompt, system_prompt=sys_msg)
        else:
            return await brain.auto(prompt, system_prompt=sys_msg)


# Global gateway singleton
llm_gateway = LLMGateway()
