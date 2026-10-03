import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.v1.procurement import CAN_APPROVE, CAN_REQUEST
from app.db.session import get_db
from app.models.user import User
from app.schemas.rfq import AwardRequest, QuotationCreate, RfqCreate, RfqRead, RfqSummary
from app.services import rfq_service

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
