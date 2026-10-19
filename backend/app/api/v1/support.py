import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.support import SupportTicketCreate, SupportTicketMessageCreate, SupportTicketRead, SupportTicketSummary
from app.services import support_ticket_service

router = APIRouter(prefix="/support", tags=["support"])


@router.post("", response_model=SupportTicketRead, status_code=201)
def create_ticket(payload: SupportTicketCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SupportTicketRead:
    return support_ticket_service.create_company_ticket(db, current_user.company_id, current_user, payload)


@router.get("", response_model=list[SupportTicketSummary])
def list_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SupportTicketSummary]:
    return support_ticket_service.list_company_tickets(db, current_user.company_id)


@router.get("/{ticket_id}", response_model=SupportTicketRead)
def get_ticket(ticket_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SupportTicketRead:
    return support_ticket_service.get_company_ticket(db, current_user.company_id, ticket_id)


@router.post("/{ticket_id}/messages", response_model=SupportTicketRead, status_code=201)
def reply(ticket_id: uuid.UUID, payload: SupportTicketMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SupportTicketRead:
    return support_ticket_service.reply_as_company(db, current_user.company_id, current_user, ticket_id, payload)
