"""
LLM Gateway
============
Single entry-point for all LLM calls in the system.

Design goals:
  1. **Provider agnostic** – callers never import Groq/Gemini directly.
  2. **Fallback chain** – if the primary provider errors, the gateway
     tries the next in line (Groq → Gemini → Mock).
  3. **Prompt templates** – registered, reusable prompt definitions that
     keep prompt engineering out of agent code.
  4. **Observability** – every call is logged with timing and token hints.

Usage::

    gateway = LLMGateway.default()
    result  = await gateway.generate_json(
        prompt="Analyze this lead ...",
        system_prompt="You are a sales strategist."
    )
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.llm.interface import BaseLLMProvider

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Wraps one or more ``BaseLLMProvider`` instances with fallback + logging.
    """

    def __init__(self, providers: List[BaseLLMProvider]):
        if not providers:
            raise ValueError("LLMGateway requires at least one provider.")
        self._providers = providers

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def default(cls) -> "LLMGateway":
        """
        Build the default fallback chain from whatever SDKs are available.
        Order: Groq (fast + cheap) → Gemini → MockLLM (deterministic tests).
        """
        chain: List[BaseLLMProvider] = []

        try:
            from app.llm.groq_provider import GroqLLMProvider
            provider = GroqLLMProvider()
            if provider.client is not None:
                chain.append(provider)
                logger.info("LLMGateway: Groq provider loaded (primary).")
        except Exception:
            pass

        try:
            from app.llm.gemini_provider import GeminiLLMProvider
            provider = GeminiLLMProvider()
            if provider.client is not None:
                chain.append(provider)
                logger.info("LLMGateway: Gemini provider loaded (fallback).")
        except Exception:
            pass

        # Always add mock as the last-resort fallback so the system never hard-crashes
        from app.llm.mock_provider import MockLLMProvider
        chain.append(MockLLMProvider())
        logger.info(f"LLMGateway: chain ready with {len(chain)} provider(s).")

        return cls(chain)

    # ── Public API ─────────────────────────────────────────────────────────

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call providers in order until one succeeds."""
        return await self._call_chain("generate_json", prompt, system_prompt)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call providers in order until one succeeds."""
        return await self._call_chain("generate_text", prompt, system_prompt)

    # ── Internals ──────────────────────────────────────────────────────────

    async def _call_chain(self, method: str, prompt: str, system_prompt: Optional[str]) -> Any:
        last_error: Optional[Exception] = None

        for provider in self._providers:
            provider_name = type(provider).__name__
            start = time.perf_counter()
            try:
                fn = getattr(provider, method)
                result = await fn(prompt, system_prompt)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"LLMGateway: {provider_name}.{method} succeeded in {elapsed:.0f}ms")
                return result
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                logger.warning(
                    f"LLMGateway: {provider_name}.{method} failed in {elapsed:.0f}ms – {exc}"
                )
                last_error = exc

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
