import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.ai.copilot import run_turn
from app.ai.llm import LLMClient
from app.ai.tools import ToolContext
from app.models.ai import AiConversation, AiMessage, AiProposal
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponse

MAX_HISTORY_MESSAGES = 20


def list_conversations(db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> list[AiConversation]:
    return (
        db.query(AiConversation)
        .filter(AiConversation.company_id == company_id, AiConversation.user_id == user_id)
        .order_by(AiConversation.created_at.desc())
        .all()
    )


def get_conversation(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> AiConversation:
    # Conversations are private to the user who started them, not just their company.
    conversation = (
        db.query(AiConversation)
        .options(joinedload(AiConversation.messages))
        .filter(
            AiConversation.id == conversation_id,
            AiConversation.company_id == company_id,
            AiConversation.user_id == user_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


def chat(db: Session, user: User, payload: ChatRequest, llm: LLMClient) -> ChatResponse:
    if payload.conversation_id:
        conversation = get_conversation(db, user.company_id, user.id, payload.conversation_id)
        created = False
    else:
        conversation = AiConversation(
            company_id=user.company_id, user_id=user.id, title=payload.message.strip()[:60] or "New chat"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        created = True

    history = [{"role": m.role, "content": m.content} for m in conversation.messages[-MAX_HISTORY_MESSAGES:]]
    while history and history[0]["role"] != "user":
        history.pop(0)  # the API needs the first message to be from the user

    ctx = ToolContext(db=db, company_id=user.company_id, user=user, conversation_id=conversation.id)
    try:
        result = run_turn(ctx, llm, history, payload.message)
    except Exception:
        db.rollback()
        if created:  # don't leave an empty conversation behind after a failed first message
            db.query(AiConversation).filter(AiConversation.id == conversation.id).delete()
            db.commit()
        raise

    db.add(AiMessage(company_id=user.company_id, conversation_id=conversation.id, role="user", content=payload.message))
    db.add(
        AiMessage(
            company_id=user.company_id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.reply,
            tool_trace=[t.model_dump(mode="json") for t in result.tool_calls] or None,
        )
    )
    db.commit()

    proposals = (
        db.query(AiProposal).filter(AiProposal.id.in_(ctx.proposal_ids)).all() if ctx.proposal_ids else []
    )
    return ChatResponse(
        conversation_id=conversation.id,
        reply=result.reply,
        tool_calls=result.tool_calls,
        proposals=proposals,
    )
