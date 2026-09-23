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
from core.freellmapi import freellmapi_pool

logger = logging.getLogger("JARVIS.Gateway")


class LLMGateway:
    """
    Unified LLM Gateway providing deterministic routing, failover,
    and latency monitoring across LiteLLM, in-process Brain, and FreeLLMAPI pool.
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

    async def _try_freellmapi_fallback(
        self,
        prompt: str,
        system_prompt: str,
        timeout: float = 10.0,
    ) -> Optional[str]:
        """Fallback to healthy burst provider from FreeLLMAPI pool."""
        provider = freellmapi_pool.get_available_provider()
        if not provider:
            return None

        logger.info(f"🔄 [FREELLMAPI DISPATCH] Routing to free burst endpoint: '{provider.name}' ({provider.model_id})")
        try:
            # If provider is Groq
            if "groq" in provider.name:
                from groq import Groq
                client = Groq(api_key=provider.api_key)
                def _call():
                    res = client.chat.completions.create(
                        model=provider.model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=1024,
                    )
                    return res.choices[0].message.content or ""
                out = await asyncio.to_thread(_call)
                provider.mark_success()
                return out
            # If provider is Gemini
            elif "gemini" in provider.name:
                from google import genai
                client = genai.Client(api_key=provider.api_key)
                full = f"System: {system_prompt}\n\nUser: {prompt}"
                def _call():
                    res = client.models.generate_content(
                        model=provider.model_id,
                        contents=full,
                    )
                    return res.text or ""
                out = await asyncio.to_thread(_call)
                provider.mark_success()
                return out
        except Exception as e:
            logger.warning(f"FreeLLMAPI provider '{provider.name}' failed: {e}")
            provider.mark_rate_limited(cooldown_seconds=60.0)
            return None
        return None

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tier: str = "auto",  # 'auto', 'reflex', 'reasoning', 'vision'
        timeout: Optional[float] = None,
    ) -> str:
        """
        Execute completion with strict latency budgets & tri-layer failover:
          Layer 1: LiteLLM Proxy
          Layer 2: Local Cognitive Brain (Groq 8B/70B / Ollama / Gemini)
          Layer 3: FreeLLMAPI Multiplexer Burst Pool
        """
        start_time = time.time()

        # Dynamic tier classification if set to auto
        if tier == "auto":
            task_type = brain.classify_task(prompt)
            actual_tier = "reasoning" if task_type == "DEEP" else "reflex"
        else:
            actual_tier = tier

        timeout_budget = timeout or (5.0 if actual_tier == "reflex" else 15.0)
        sys_msg = system_prompt or "You are JARVIS, an autonomous sovereign executive assistant."
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ]

        # Layer 1: Attempt LiteLLM Proxy
        content = await self._try_litellm_proxy(actual_tier, messages, timeout=timeout_budget)
        if content:
            elapsed = time.time() - start_time
            logger.debug(f"Completion from LiteLLM proxy [{actual_tier}] in {elapsed:.2f}s")
            return content

        # Layer 2: In-process Cognitive Brain
        try:
            if actual_tier == "reflex":
                brain_res = await brain.reflex(prompt, system_prompt=sys_msg)
            elif actual_tier == "reasoning":
                brain_res = await brain.reason(prompt, system_prompt=sys_msg)
            else:
                brain_res = await brain.auto(prompt, system_prompt=sys_msg)

            if brain_res and not brain_res.startswith("[JARVIS Offline Mock Response"):
                return brain_res
        except Exception as e:
            logger.warning(f"Brain execution failed: {e}")

        # Layer 3: FreeLLMAPI Multiplexer Pool
        pool_res = await self._try_freellmapi_fallback(prompt, sys_msg, timeout=timeout_budget)
        if pool_res:
            return pool_res

        # Fallback to brain response if pool is empty/unconfigured
        return brain_res if 'brain_res' in locals() and brain_res else "[JARVIS System Ready]"


# Global gateway singleton
llm_gateway = LLMGateway()
