"""Support desk (Phase 8, PLAT-046). One ticket table, three actor types.
`is_internal` messages are filtered out of every non-staff read path at the
query/service level -- never relying on the frontend to hide them."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.enums import SupportAuthorType, SupportRequesterType, SupportTicketStatus
from app.models.marketplace_supplier import MarketplaceSupplier
from app.models.platform_admin import PlatformAdmin
from app.models.support import SupportTicket, SupportTicketMessage
from app.models.supplier_user import SupplierUser
from app.models.user import User
from app.schemas.support import SupportTicketCreate, SupportTicketMessageCreate, SupportTicketMessageRead, SupportTicketRead, SupportTicketSummary, SupportTicketUpdate
from app.services import notification_service, platform_notification_service, supplier_notification_service


def _message_read(m: SupportTicketMessage, name: str | None) -> SupportTicketMessageRead:
    return SupportTicketMessageRead(id=m.id, body=m.body, is_internal=m.is_internal, author_type=m.author_type, author_name=name, created_at=m.created_at)


def _author_names(db: Session, messages: list[SupportTicketMessage]) -> dict[uuid.UUID, str]:
    user_ids = [m.author_user_id for m in messages if m.author_user_id]
    supplier_user_ids = [m.author_supplier_user_id for m in messages if m.author_supplier_user_id]
    staff_ids = [m.author_staff_id for m in messages if m.author_staff_id]
    names: dict[uuid.UUID, str] = {}
    if user_ids:
        names.update(dict(db.query(User.id, User.full_name).filter(User.id.in_(user_ids)).all()))
    if supplier_user_ids:
        names.update(dict(db.query(SupplierUser.id, SupplierUser.full_name).filter(SupplierUser.id.in_(supplier_user_ids)).all()))
    if staff_ids:
        names.update(dict(db.query(PlatformAdmin.id, PlatformAdmin.full_name).filter(PlatformAdmin.id.in_(staff_ids)).all()))
    return names


def _read(ticket: SupportTicket, company_name: str | None, supplier_name: str | None, staff_name: str | None, author_names: dict[uuid.UUID, str], include_internal: bool) -> SupportTicketRead:
    messages = [m for m in ticket.messages if include_internal or not m.is_internal]
    return SupportTicketRead(
        id=ticket.id, requester_type=ticket.requester_type, company_id=ticket.company_id, company_name=company_name,
        marketplace_supplier_id=ticket.marketplace_supplier_id, marketplace_supplier_name=supplier_name,
        subject=ticket.subject, category=ticket.category, priority=ticket.priority, status=ticket.status,
        assigned_staff_id=ticket.assigned_staff_id, assigned_staff_name=staff_name, resolved_at=ticket.resolved_at,
        messages=[_message_read(m, author_names.get(m.author_user_id or m.author_supplier_user_id or m.author_staff_id)) for m in messages],
        created_at=ticket.created_at,
    )


def _names_for(db: Session, ticket: SupportTicket) -> tuple[str | None, str | None, str | None]:
    company_name = db.query(Company.name).filter(Company.id == ticket.company_id).scalar() if ticket.company_id else None
    supplier_name = db.query(MarketplaceSupplier.name).filter(MarketplaceSupplier.id == ticket.marketplace_supplier_id).scalar() if ticket.marketplace_supplier_id else None
    staff_name = db.query(PlatformAdmin.full_name).filter(PlatformAdmin.id == ticket.assigned_staff_id).scalar() if ticket.assigned_staff_id else None
    return company_name, supplier_name, staff_name


def _get(db: Session, ticket_id: uuid.UUID) -> SupportTicket:
    ticket = db.query(SupportTicket).options(selectinload(SupportTicket.messages)).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


# ---- Company-side -----------------------------------------------------------------------------


def create_company_ticket(db: Session, company_id: uuid.UUID, user: User, payload: SupportTicketCreate) -> SupportTicketRead:
    ticket = SupportTicket(
        requester_type=SupportRequesterType.COMPANY, company_id=company_id, opened_by_user_id=user.id,
        subject=payload.subject, category=payload.category, priority=payload.priority,
    )
    db.add(ticket)
    db.flush()
    db.add(SupportTicketMessage(ticket_id=ticket.id, body=payload.message, author_type=SupportAuthorType.COMPANY_USER, author_user_id=user.id))
    platform_notification_service.notify_staff(db, "support_ticket_opened", f"New ticket: {payload.subject}", link=f"/platform-admin/support/{ticket.id}")
    db.commit()
    return get_company_ticket(db, company_id, ticket.id)


def list_company_tickets(db: Session, company_id: uuid.UUID) -> list[SupportTicketSummary]:
    rows = db.query(SupportTicket).filter(SupportTicket.company_id == company_id).order_by(SupportTicket.created_at.desc()).all()
    return [SupportTicketSummary(id=t.id, requester_type=t.requester_type, subject=t.subject, category=t.category, priority=t.priority, status=t.status, created_at=t.created_at) for t in rows]


def get_company_ticket(db: Session, company_id: uuid.UUID, ticket_id: uuid.UUID) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    if ticket.company_id != company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    company_name, supplier_name, staff_name = _names_for(db, ticket)
    return _read(ticket, company_name, supplier_name, staff_name, _author_names(db, ticket.messages), include_internal=False)


def reply_as_company(db: Session, company_id: uuid.UUID, user: User, ticket_id: uuid.UUID, payload: SupportTicketMessageCreate) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    if ticket.company_id != company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    db.add(SupportTicketMessage(ticket_id=ticket.id, body=payload.body, author_type=SupportAuthorType.COMPANY_USER, author_user_id=user.id))
    if ticket.status in (SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED):
        ticket.status = SupportTicketStatus.OPEN
    db.commit()
    return get_company_ticket(db, company_id, ticket_id)


# ---- Supplier-side ------------------------------------------------------------------------------


def create_supplier_ticket(db: Session, marketplace_supplier_id: uuid.UUID, supplier_user: SupplierUser, payload: SupportTicketCreate) -> SupportTicketRead:
    ticket = SupportTicket(
        requester_type=SupportRequesterType.SUPPLIER, marketplace_supplier_id=marketplace_supplier_id, opened_by_supplier_user_id=supplier_user.id,
        subject=payload.subject, category=payload.category, priority=payload.priority,
    )
    db.add(ticket)
    db.flush()
    db.add(SupportTicketMessage(ticket_id=ticket.id, body=payload.message, author_type=SupportAuthorType.SUPPLIER_USER, author_supplier_user_id=supplier_user.id))
    platform_notification_service.notify_staff(db, "support_ticket_opened", f"New ticket: {payload.subject}", link=f"/platform-admin/support/{ticket.id}")
    db.commit()
    return get_supplier_ticket(db, marketplace_supplier_id, ticket.id)


def list_supplier_tickets(db: Session, marketplace_supplier_id: uuid.UUID) -> list[SupportTicketSummary]:
    rows = db.query(SupportTicket).filter(SupportTicket.marketplace_supplier_id == marketplace_supplier_id).order_by(SupportTicket.created_at.desc()).all()
    return [SupportTicketSummary(id=t.id, requester_type=t.requester_type, subject=t.subject, category=t.category, priority=t.priority, status=t.status, created_at=t.created_at) for t in rows]


def get_supplier_ticket(db: Session, marketplace_supplier_id: uuid.UUID, ticket_id: uuid.UUID) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    if ticket.marketplace_supplier_id != marketplace_supplier_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    company_name, supplier_name, staff_name = _names_for(db, ticket)
    return _read(ticket, company_name, supplier_name, staff_name, _author_names(db, ticket.messages), include_internal=False)


def reply_as_supplier(db: Session, marketplace_supplier_id: uuid.UUID, supplier_user: SupplierUser, ticket_id: uuid.UUID, payload: SupportTicketMessageCreate) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    if ticket.marketplace_supplier_id != marketplace_supplier_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    db.add(SupportTicketMessage(ticket_id=ticket.id, body=payload.body, author_type=SupportAuthorType.SUPPLIER_USER, author_supplier_user_id=supplier_user.id))
    if ticket.status in (SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED):
        ticket.status = SupportTicketStatus.OPEN
    db.commit()
    return get_supplier_ticket(db, marketplace_supplier_id, ticket_id)


# ---- Platform-staff side -------------------------------------------------------------------------


def list_all_tickets(db: Session, status_filter: SupportTicketStatus | None = None, assigned_staff_id: uuid.UUID | None = None) -> list[SupportTicketSummary]:
    query = db.query(SupportTicket)
    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    if assigned_staff_id:
        query = query.filter(SupportTicket.assigned_staff_id == assigned_staff_id)
    rows = query.order_by(SupportTicket.created_at.desc()).all()
    results = []
    for t in rows:
        company_name, supplier_name, _staff = _names_for(db, t)
        results.append(SupportTicketSummary(id=t.id, requester_type=t.requester_type, company_name=company_name, marketplace_supplier_name=supplier_name, subject=t.subject, category=t.category, priority=t.priority, status=t.status, created_at=t.created_at))
    return results


def get_ticket_for_staff(db: Session, ticket_id: uuid.UUID) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    company_name, supplier_name, staff_name = _names_for(db, ticket)
    return _read(ticket, company_name, supplier_name, staff_name, _author_names(db, ticket.messages), include_internal=True)


def update_ticket(db: Session, actor: PlatformAdmin, ticket_id: uuid.UUID, payload: SupportTicketUpdate) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    changes = payload.model_dump(exclude_unset=True)
    was_resolved = ticket.status in (SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED)
    for field, value in changes.items():
        setattr(ticket, field, value)
    if "status" in changes and changes["status"] in (SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED) and not was_resolved:
        ticket.resolved_at = datetime.now(timezone.utc)
        _notify_requester_resolved(db, ticket)
    from app.services import platform_audit_service

    platform_audit_service.record(db, actor.id, "support.ticket_updated", "support_ticket", ticket.id, f"Ticket updated: {changes}")
    db.commit()
    return get_ticket_for_staff(db, ticket_id)


def reply_as_staff(db: Session, actor: PlatformAdmin, ticket_id: uuid.UUID, body: str, is_internal: bool) -> SupportTicketRead:
    ticket = _get(db, ticket_id)
    db.add(SupportTicketMessage(ticket_id=ticket.id, body=body, is_internal=is_internal, author_type=SupportAuthorType.STAFF, author_staff_id=actor.id))
    if not is_internal:
        _notify_requester_reply(db, ticket)
    db.commit()
    return get_ticket_for_staff(db, ticket_id)


def _notify_requester_reply(db: Session, ticket: SupportTicket) -> None:
    if ticket.requester_type == SupportRequesterType.COMPANY and ticket.opened_by_user_id:
        notification_service.notify_support_ticket_reply(db, ticket.company_id, ticket.opened_by_user_id, ticket.subject, ticket.id)
    elif ticket.requester_type == SupportRequesterType.SUPPLIER:
        supplier_notification_service.notify_members(db, ticket.marketplace_supplier_id, "support_ticket_reply", f"New reply on \"{ticket.subject}\"", link=f"/supplier-portal/support/{ticket.id}")


def _notify_requester_resolved(db: Session, ticket: SupportTicket) -> None:
    if ticket.requester_type == SupportRequesterType.COMPANY and ticket.opened_by_user_id:
        notification_service.notify_support_ticket_resolved(db, ticket.company_id, ticket.opened_by_user_id, ticket.subject, ticket.id)
    elif ticket.requester_type == SupportRequesterType.SUPPLIER:
        supplier_notification_service.notify_members(db, ticket.marketplace_supplier_id, "support_ticket_resolved", f"\"{ticket.subject}\" marked resolved", link=f"/supplier-portal/support/{ticket.id}")
