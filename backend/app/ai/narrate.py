"""Single-shot AI narration (Phase 9, PLAT-048): for "summarize/explain this
real data" features across all three portals that don't need a
back-and-forth conversation or a tool-calling loop -- the chat copilot
(app/ai/copilot.py) already covers that case for the company portal.
Always reuses the one configured LLM client (app/ai/llm.py); never a
second provider integration.

The caller is always responsible for fetching the data through an existing,
already-authorized service call and serializing only that into the prompt.
This module never queries anything itself, so there's no way for it to see
data the caller wasn't already allowed to see. Every system prompt used
with this module must instruct the model to use only the data it's given
and never invent figures -- enforced by convention at each call site, the
same discipline as copilot.py's own system prompt."""

import logging
from typing import Any

import anthropic
from fastapi import HTTPException

from app.ai.llm import LLMClient
from app.core.config import get_settings
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

TOO_MANY_AI_REQUESTS = "You've reached the AI usage limit for now. Try again shortly."

NO_ANSWER_REPLY = "Couldn't generate a summary right now. Try again in a moment."

DATA_DISCIPLINE = (
    "Use only the data given to you below. Never invent prices, names, dates, statuses or amounts "
    "that aren't present in it. If the data is insufficient to answer part of the request, say so "
    "plainly rather than guessing. Clearly mark any suggestion or interpretation as your own "
    "assessment, distinct from the verified data it's based on."
)


def _text_of(content: Any) -> str:
    return "".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text").strip()


def generate_narration(llm: LLMClient, system_prompt: str, user_content: str, actor_key: str, feature: str) -> str:
    """Raises the same HTTPException shapes api/v1/ai.py's /chat endpoint
    already raises for provider failures, so every caller degrades
    identically and predictably. `actor_key` scopes the usage limit (one
    bucket per actor, not globally shared); `feature` is logged as metadata
    only, never the prompt or response text."""
    settings = get_settings()
    limiter.check(f"ai-narration:{actor_key}", settings.ai_narration_max_per_actor, settings.ai_narration_window_seconds, TOO_MANY_AI_REQUESTS)
    limiter.hit(f"ai-narration:{actor_key}")
    log_usage(feature, actor_key)

    try:
        response = llm.create_message(f"{system_prompt}\n\n{DATA_DISCIPLINE}", [{"role": "user", "content": user_content}], [])
    except anthropic.AuthenticationError:
        logger.error("Anthropic rejected the configured API key")
        raise HTTPException(502, "The AI provider rejected the configured API key.")
    except anthropic.RateLimitError:
        raise HTTPException(429, "The AI provider is rate limiting requests. Try again in a moment.")
    except anthropic.APIConnectionError:
        raise HTTPException(503, "Couldn't reach the AI provider. Try again in a moment.")
    except anthropic.APIStatusError:
        logger.exception("Anthropic API error")
        raise HTTPException(502, "The AI provider returned an error.")

    if response.stop_reason == "refusal":
        raise HTTPException(422, "The AI assistant declined to answer that.")
    text = _text_of(response.content)
    if response.stop_reason == "max_tokens":
        text += "\n\n(Cut off due to length limit.)"
    return text or NO_ANSWER_REPLY


def log_usage(feature: str, actor_id: Any) -> None:
    """Metadata only -- never the prompt or response text (PLAT-048's
    "without storing unnecessary sensitive prompt content")."""
    logger.info("ai_narration feature=%s actor=%s", feature, actor_id)
