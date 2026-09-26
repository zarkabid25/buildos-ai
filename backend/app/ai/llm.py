"""Thin wrapper over the official Anthropic SDK.

The copilot talks to `LLMClient` (a Protocol), so the orchestration can be tested
with a scripted fake, and this real implementation is only built when an API key
is configured.

Request choices, from the Claude API reference:
- Model comes from settings (default claude-opus-5). Opus 5 runs adaptive
  thinking by default, so `thinking` is left out.
- No temperature/top_p/top_k: Opus 5 rejects sampling parameters with a 400.
- Server-side refusal fallbacks are on by default (`fallbacks="default"`).
"""

from typing import Any, Protocol

import anthropic

from app.ai.errors import AINotConfigured
from app.core.config import get_settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMClient(Protocol):
    def create_message(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any: ...


class AnthropicLLMClient:
    def __init__(self, api_key: str, model: str, max_tokens: int, use_fallbacks: bool, sdk_client: Any = None):
        self._client = sdk_client or anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._use_fallbacks = use_fallbacks

    def create_message(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": messages,
            "tools": tools,
        }
        if self._use_fallbacks:
            return self._client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **params)
        return self._client.messages.create(**params)


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if not settings.llm_api_key:
        raise AINotConfigured("No LLM API key is configured (set LLM_API_KEY).")
    return AnthropicLLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        use_fallbacks=settings.llm_use_fallbacks,
    )
