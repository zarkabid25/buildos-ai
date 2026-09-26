"""One chat turn: send the question to the model, run the tools it asks for
(through app.ai.tools, always as the signed-in user), and repeat until it
answers. Bounded by settings.llm_max_tool_iterations."""

from dataclasses import dataclass, field
from typing import Any

from app.ai.llm import LLMClient
from app.ai.tools import ToolContext, run_tool, tool_schemas
from app.core.config import get_settings
from app.schemas.ai import ToolCallTrace

SYSTEM_PROMPT = """You are BuildOS AI, the assistant inside a construction ERP used by contractors and site teams.

How to work:
- Answer only from data returned by your tools. Never invent numbers, names, ids or dates. If the tools don't have it, say so plainly.
- Look things up with tools, several if needed. Project and material ids come from the list tools.
- Quantities, forecasts and reorder suggestions are estimates a person should check before acting on them. Say so when you give them.
- You cannot create, change or delete records. To suggest ordering material, call propose_material_request: it only saves a draft that a person must approve. Tell the user that it needs their approval and where (the AI Command Center).
- Be concise. For an analysis of a problem, use: Summary, Why, Impact, Recommended actions, Data used. For a simple question, just answer it."""

REFUSAL_REPLY = "I can't help with that request."
NO_ANSWER_REPLY = "I couldn't finish working that out. Try asking a narrower question."


@dataclass
class TurnResult:
    reply: str
    tool_calls: list[ToolCallTrace] = field(default_factory=list)


def _text_of(content: Any) -> str:
    return "".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text").strip()


def run_turn(ctx: ToolContext, llm: LLMClient, history: list[dict[str, str]], user_text: str) -> TurnResult:
    messages: list[dict[str, Any]] = [*history, {"role": "user", "content": user_text}]
    trace: list[ToolCallTrace] = []
    schemas = tool_schemas()

    for _ in range(get_settings().llm_max_tool_iterations):
        response = llm.create_message(SYSTEM_PROMPT, messages, schemas)
        stop_reason = response.stop_reason

        # Check stop_reason before reading content: a refusal has no usable answer.
        if stop_reason == "refusal":
            return TurnResult(REFUSAL_REPLY, trace)

        if stop_reason in ("tool_use", "pause_turn"):
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                text, is_error = run_tool(ctx, block.name, block.input)
                trace.append(ToolCallTrace(name=block.name, input=dict(block.input or {}), is_error=is_error))
                result: dict[str, Any] = {"type": "tool_result", "tool_use_id": block.id, "content": text}
                if is_error:
                    result["is_error"] = True
                results.append(result)
            if results:
                # All results for one assistant turn go back together in a single user message.
                messages.append({"role": "user", "content": results})
            continue

        reply = _text_of(response.content)
        if stop_reason == "max_tokens":
            reply += "\n\n(This answer was cut off because it hit the length limit.)"
        return TurnResult(reply or NO_ANSWER_REPLY, trace)

    return TurnResult(NO_ANSWER_REPLY, trace)
