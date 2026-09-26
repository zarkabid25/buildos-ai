import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AiProposalStatus, AiProposalType


class AiStatus(BaseModel):
    configured: bool
    provider: str
    model: str


class Insight(BaseModel):
    severity: Literal["high", "medium", "low"]
    category: str
    title: str
    detail: str
    project_id: uuid.UUID | None = None
    data: dict[str, Any] = {}


class InsightsReport(BaseModel):
    # Always "rules": these are computed from company data with fixed thresholds,
    # never written by a language model.
    generated_by: Literal["rules"] = "rules"
    summary: str
    counts: dict[str, int]
    insights: list[Insight]


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class AiProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID | None
    proposal_type: AiProposalType
    status: AiProposalStatus
    summary: str
    payload: dict[str, Any]
    result_ref: uuid.UUID | None
    created_at: datetime


class ToolCallTrace(BaseModel):
    name: str
    input: dict[str, Any]
    is_error: bool = False


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    tool_calls: list[ToolCallTrace]
    proposals: list[AiProposalRead]


class AiMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class AiConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime


class AiConversationDetail(AiConversationRead):
    messages: list[AiMessageRead]
