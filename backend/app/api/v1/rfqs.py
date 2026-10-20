import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.llm import LLMClient, get_llm_dependency
from app.ai.narrate import generate_narration
from app.api.deps import get_current_user, require_roles
from app.api.v1.procurement import CAN_APPROVE, CAN_REQUEST
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import AiNarrationResponse
from app.schemas.rfq import AwardRequest, QuotationCreate, RfqCreate, RfqRead, RfqSummary
from app.services import rfq_service

AI_SYSTEM_PROMPT = (
    "You are an assistant for a construction company's procurement team, helping them read an RFQ "
    "and compare quotations. You are advisory only -- you never award a quotation, create a purchase "
    "order, or change anything; a human does that separately through the existing RFQ screen."
)

router = APIRouter(prefix="/rfqs", tags=["rfqs"])


@router.get("", response_model=list[RfqSummary])
def list_rfqs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[RfqSummary]:
    return rfq_service.list_rfqs(db, current_user.company_id)


@router.post("", response_model=RfqRead, status_code=201)
def create_rfq(
    payload: RfqCreate,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> RfqRead:
    rfq = rfq_service.create_rfq(db, current_user.company_id, current_user.id, payload)
    return rfq_service.to_read(db, current_user.company_id, rfq)


@router.get("/{rfq_id}", response_model=RfqRead)
def get_rfq(
    rfq_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> RfqRead:
    return rfq_service.to_read(db, current_user.company_id, rfq_service.get_rfq(db, current_user.company_id, rfq_id))


@router.post("/{rfq_id}/quotations", response_model=RfqRead, status_code=201)
def record_quotation(
    rfq_id: uuid.UUID,
    payload: QuotationCreate,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> RfqRead:
    rfq = rfq_service.record_quotation(db, current_user.company_id, current_user.id, rfq_id, payload)
    return rfq_service.to_read(db, current_user.company_id, rfq)


@router.post("/{rfq_id}/award", response_model=RfqRead)
def award(
    rfq_id: uuid.UUID,
    payload: AwardRequest,
    current_user: User = Depends(require_roles(*CAN_APPROVE)),
    db: Session = Depends(get_db),
) -> RfqRead:
    rfq = rfq_service.award(db, current_user.company_id, current_user.id, rfq_id, payload.quotation_id)
    return rfq_service.to_read(db, current_user.company_id, rfq)


@router.post("/{rfq_id}/cancel", response_model=RfqRead)
def cancel(
    rfq_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_APPROVE)),
    db: Session = Depends(get_db),
) -> RfqRead:
    rfq = rfq_service.cancel(db, current_user.company_id, current_user.id, rfq_id)
    return rfq_service.to_read(db, current_user.company_id, rfq)


@router.get("/{rfq_id}/ai/summary", response_model=AiNarrationResponse)
def ai_summary(
    rfq_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_dependency),
) -> AiNarrationResponse:
    """A requirements summary, plus a quotation-comparison explanation when
    quotations exist -- both built only from this real, already-isolated-by-
    company RFQ (PLAT-048). Never exposes another company's RFQ or quotations:
    rfq_service.get_rfq already 404s on a cross-tenant id before this
    function is ever reached."""
    rfq = rfq_service.to_read(db, current_user.company_id, rfq_service.get_rfq(db, current_user.company_id, rfq_id))
    items = "\n".join(f"- {i.material_name}: {i.quantity} {i.unit}" for i in rfq.items)
    data = f"RFQ {rfq.rfq_number}: {rfq.title}\nStatus: {rfq.status.value}\nItems requested:\n{items}\nNotes: {rfq.notes or 'none'}"
    if rfq.quotations:
        data += "\n\nQuotations received:\n" + "\n".join(
            f"- {q.supplier_name}: total={q.total}, delivery_days={q.delivery_days}, valid_until={q.valid_until}, lowest_total={q.is_lowest_total}, expired={q.expired}"
            for q in rfq.quotations
        )
        prompt = f"Summarize what this RFQ is asking for, then explain how the received quotations compare (price, delivery, validity) -- using only the real data below:\n\n{data}"
    else:
        prompt = f"Summarize what this RFQ is asking for, in plain language, using only the real data below:\n\n{data}"
    text = generate_narration(llm, AI_SYSTEM_PROMPT, prompt, actor_key=f"user:{current_user.id}", feature="rfq_summary")
    return AiNarrationResponse(narration=text)
