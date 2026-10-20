import logging
import uuid

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.insights import build_insights
from app.ai.llm import LLMClient, get_llm_dependency
from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import AiProposalStatus, UserRole
from app.models.user import User
from app.schemas.ai import (
    AiConversationDetail,
    AiConversationRead,
    AiProposalRead,
    AiStatus,
    ChatRequest,
    ChatResponse,
    InsightsReport,
)
from app.services import ai_chat_service, ai_proposal_service, ai_quota_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

# Whoever could create a material request directly may approve an AI draft of one.
CAN_DECIDE = (
    UserRole.SUPER_ADMIN,
    UserRole.COMPANY_ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
    UserRole.STOREKEEPER,
)


get_llm = get_llm_dependency


@router.get("/status", response_model=AiStatus)
def ai_status(current_user: User = Depends(get_current_user)) -> AiStatus:
    settings = get_settings()
    # Deliberately no key (not even a masked one): it's a server env var, never shown in the app.
    return AiStatus(
        configured=bool(settings.llm_api_key.get_secret_value()),
        provider="anthropic",
        model=settings.llm_model,
        use_fallbacks=settings.llm_use_fallbacks,
        max_tool_iterations=settings.llm_max_tool_iterations,
    )


@router.get("/insights", response_model=InsightsReport)
def insights(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> InsightsReport:
    return build_insights(db, current_user.company_id)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
) -> ChatResponse:
    # Phase 9.1 (Task 4): ai_monthly_messages was previously just a displayed
    # figure (see docs/RELEASE_READINESS.md). This is the one place the chat
    # copilot actually gates on it, atomically, before spending on a real
    # provider call.
    ai_quota_service.reserve_usage(db, current_user.company_id)
    try:
        return ai_chat_service.chat(db, current_user, payload, llm)
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


@router.get("/conversations", response_model=list[AiConversationRead])
def list_conversations(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AiConversationRead]:
    return ai_chat_service.list_conversations(db, current_user.company_id, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=AiConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiConversationDetail:
    return ai_chat_service.get_conversation(db, current_user.company_id, current_user.id, conversation_id)


@router.get("/proposals", response_model=list[AiProposalRead])
def list_proposals(
    status: AiProposalStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AiProposalRead]:
    return ai_proposal_service.list_proposals(db, current_user.company_id, status)


@router.post("/proposals/{proposal_id}/approve", response_model=AiProposalRead)
def approve_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_DECIDE)),
    db: Session = Depends(get_db),
) -> AiProposalRead:
    return ai_proposal_service.approve_proposal(db, current_user.company_id, current_user, proposal_id)


@router.post("/proposals/{proposal_id}/reject", response_model=AiProposalRead)
def reject_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_DECIDE)),
    db: Session = Depends(get_db),
) -> AiProposalRead:
    return ai_proposal_service.reject_proposal(db, current_user.company_id, current_user, proposal_id)
