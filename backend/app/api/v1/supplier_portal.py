import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.ai.llm import LLMClient, get_llm_dependency
from app.ai.narrate import generate_narration
from app.api.deps import SupplierSession, get_current_supplier_user, require_supplier_roles
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.ai import AiNarrationResponse
from app.models.enums import CommissionDisputeStatus, CommissionInvoiceStatus, SupplierMembershipRole
from app.schemas.commission import CommissionAgreementRead, CommissionDisputeRead, CommissionInvoiceRead, CommissionLedgerEntryRead
from app.schemas.supplier_portal import (
    SupplierAcceptInvitation,
    SupplierAuthResponse,
    SupplierDashboard,
    SupplierDeliveryUpdateCreate,
    SupplierDeliveryUpdateRead,
    SupplierDocumentRead,
    SupplierInvitationCreate,
    SupplierInvitationCreated,
    SupplierInvitationInfo,
    SupplierInvitationRead,
    SupplierLoginRequest,
    SupplierMembershipRead,
    SupplierMembershipRoleUpdate,
    SupplierMembershipSummary,
    SupplierOrderRead,
    SupplierOwnQuotation,
    SupplierProductCreate,
    SupplierProductRead,
    SupplierProductUpdate,
    SupplierProfileRead,
    SupplierProfileUpdate,
    SupplierQuotationHistoryItem,
    SupplierQuotationSubmit,
    SupplierRefreshRequest,
    SupplierRfqDetail,
    SupplierRfqInboxItem,
    SupplierSelectSupplierRequest,
    SupplierTokenPair,
    SupplierUserRead,
)
from app.schemas.support import SupportTicketCreate, SupportTicketMessageCreate, SupportTicketRead, SupportTicketSummary
from app.services import (
    support_ticket_service,
    supplier_auth_service,
    supplier_commission_service,
    supplier_invitation_service,
    supplier_membership_service,
    supplier_notification_service,
    supplier_order_service,
    supplier_portal_service,
    supplier_product_service,
    supplier_rfq_service,
)

router = APIRouter(prefix="/supplier-portal", tags=["supplier-portal"])

CAN_MANAGE_TEAM = require_supplier_roles(SupplierMembershipRole.OWNER, SupplierMembershipRole.ADMIN)
CAN_MANAGE_PROFILE = require_supplier_roles(SupplierMembershipRole.OWNER, SupplierMembershipRole.ADMIN)

TOO_MANY = "Too many attempts. Please wait and try again."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---- PLAT-038: auth, invitations, memberships -------------------------------------------------
# Phase 9 security audit (PLAT-049): this whole auth surface previously had
# no rate limiting at all -- unlike its tenant/platform equivalents in
# auth.py/platform.py. Same mechanism, same keying conventions, applied here.


@router.post("/auth/login", response_model=SupplierAuthResponse)
def login(payload: SupplierLoginRequest, request: Request, db: Session = Depends(get_db)) -> SupplierAuthResponse:
    settings = get_settings()
    key = f"supplier-login:{_client_ip(request)}:{payload.email.lower()}"
    limiter.check(key, settings.login_max_failures, settings.login_failure_window_seconds, TOO_MANY)
    try:
        result = supplier_auth_service.login(db, payload)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            limiter.hit(key)
        raise
    limiter.reset(key)
    return result


@router.post("/auth/select-supplier", response_model=SupplierTokenPair)
def select_supplier(payload: SupplierSelectSupplierRequest, request: Request, db: Session = Depends(get_db)) -> SupplierTokenPair:
    settings = get_settings()
    key = f"supplier-select:{_client_ip(request)}"
    limiter.check(key, settings.refresh_max_per_ip, settings.refresh_window_seconds, TOO_MANY)
    limiter.hit(key)
    return supplier_auth_service.select_supplier(db, payload.refresh_token, payload.marketplace_supplier_id)


@router.post("/auth/refresh", response_model=SupplierTokenPair)
def refresh(payload: SupplierRefreshRequest, request: Request, db: Session = Depends(get_db)) -> SupplierTokenPair:
    settings = get_settings()
    key = f"supplier-refresh:{_client_ip(request)}"
    limiter.check(key, settings.refresh_max_per_ip, settings.refresh_window_seconds, TOO_MANY)
    limiter.hit(key)
    return supplier_auth_service.refresh(db, payload.refresh_token)


@router.get("/auth/invitations/{token}", response_model=SupplierInvitationInfo)
def invitation_info(token: str, request: Request, db: Session = Depends(get_db)) -> SupplierInvitationInfo:
    settings = get_settings()
    key = f"supplier-invite:{_client_ip(request)}"
    limiter.check(key, settings.register_max_per_ip * 5, settings.register_window_seconds, TOO_MANY)
    limiter.hit(key)
    return supplier_invitation_service.get_invitation_info(db, token)


@router.post("/auth/accept-invite", response_model=SupplierUserRead, status_code=201)
def accept_invite(payload: SupplierAcceptInvitation, request: Request, db: Session = Depends(get_db)) -> SupplierUserRead:
    settings = get_settings()
    key = f"supplier-register:{_client_ip(request)}"
    limiter.check(key, settings.register_max_per_ip, settings.register_window_seconds, TOO_MANY)
    limiter.hit(key)
    user = supplier_invitation_service.accept_invitation(db, payload)
    return SupplierUserRead.model_validate(user)


@router.get("/auth/me", response_model=SupplierUserRead)
def me(session: SupplierSession = Depends(get_current_supplier_user)) -> SupplierUserRead:
    return SupplierUserRead.model_validate(session.user)


@router.get("/auth/my-memberships", response_model=list[SupplierMembershipSummary])
def my_memberships(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierMembershipSummary]:
    return supplier_auth_service.my_memberships(db, session.user.id)


@router.post("/team/invitations", response_model=SupplierInvitationCreated, status_code=201)
def invite_team_member(payload: SupplierInvitationCreate, session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> SupplierInvitationCreated:
    return supplier_invitation_service.create_invitation_by_supplier(db, session.marketplace_supplier_id, session.user.id, session.user.full_name, payload)


@router.get("/team/invitations", response_model=list[SupplierInvitationRead])
def list_team_invitations(session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> list[SupplierInvitationRead]:
    return supplier_invitation_service.list_invitations(db, session.marketplace_supplier_id)


@router.post("/team/invitations/{invitation_id}/revoke", status_code=204)
def revoke_team_invitation(invitation_id: uuid.UUID, session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> None:
    supplier_invitation_service.revoke_invitation(db, session.marketplace_supplier_id, invitation_id)


@router.get("/team/members", response_model=list[SupplierMembershipRead])
def list_team_members(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierMembershipRead]:
    return supplier_membership_service.list_members(db, session.marketplace_supplier_id)


@router.post("/team/members/{membership_id}/suspend", response_model=SupplierMembershipRead)
def suspend_member(membership_id: uuid.UUID, session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> SupplierMembershipRead:
    return supplier_membership_service.suspend_member(db, session.marketplace_supplier_id, membership_id, session.membership.id)


@router.post("/team/members/{membership_id}/revoke", response_model=SupplierMembershipRead)
def revoke_member(membership_id: uuid.UUID, session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> SupplierMembershipRead:
    return supplier_membership_service.revoke_member(db, session.marketplace_supplier_id, membership_id, session.membership.id)


@router.post("/team/members/{membership_id}/reinstate", response_model=SupplierMembershipRead)
def reinstate_member(membership_id: uuid.UUID, session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> SupplierMembershipRead:
    return supplier_membership_service.reinstate_member(db, session.marketplace_supplier_id, membership_id)


@router.patch("/team/members/{membership_id}/role", response_model=SupplierMembershipRead)
def change_member_role(membership_id: uuid.UUID, payload: SupplierMembershipRoleUpdate, session: SupplierSession = Depends(CAN_MANAGE_TEAM), db: Session = Depends(get_db)) -> SupplierMembershipRead:
    return supplier_membership_service.change_role(db, session.marketplace_supplier_id, membership_id, payload.role)


# ---- PLAT-039: dashboard and profile ------------------------------------------------------------


@router.get("/dashboard", response_model=SupplierDashboard)
def dashboard(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierDashboard:
    return supplier_portal_service.get_dashboard(db, session.marketplace_supplier_id)


@router.get("/profile", response_model=SupplierProfileRead)
def get_profile(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierProfileRead:
    return supplier_portal_service.get_profile(db, session.marketplace_supplier_id)


@router.patch("/profile", response_model=SupplierProfileRead)
def update_profile(payload: SupplierProfileUpdate, session: SupplierSession = Depends(CAN_MANAGE_PROFILE), db: Session = Depends(get_db)) -> SupplierProfileRead:
    return supplier_portal_service.update_profile(db, session.marketplace_supplier_id, payload)


@router.get("/profile/documents", response_model=list[SupplierDocumentRead])
def list_documents(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierDocumentRead]:
    return supplier_portal_service.list_documents(db, session.marketplace_supplier_id)


@router.post("/profile/documents", response_model=SupplierDocumentRead, status_code=201)
async def upload_document(file: UploadFile, title: str = "", session: SupplierSession = Depends(CAN_MANAGE_PROFILE), db: Session = Depends(get_db)) -> SupplierDocumentRead:
    return await supplier_portal_service.upload_document(db, session.marketplace_supplier_id, session.user.id, file, title)


# ---- PLAT-040: product catalog -----------------------------------------------------------------


@router.get("/products", response_model=list[SupplierProductRead])
def list_products(search: str | None = None, active_only: bool = False, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierProductRead]:
    return supplier_product_service.list_products(db, session.marketplace_supplier_id, search, active_only)


@router.post("/products", response_model=SupplierProductRead, status_code=201)
def create_product(payload: SupplierProductCreate, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierProductRead:
    return supplier_product_service.create_product(db, session.marketplace_supplier_id, payload)


@router.get("/products/{product_id}", response_model=SupplierProductRead)
def get_product(product_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierProductRead:
    return supplier_product_service.get_product(db, session.marketplace_supplier_id, product_id)


@router.patch("/products/{product_id}", response_model=SupplierProductRead)
def update_product(product_id: uuid.UUID, payload: SupplierProductUpdate, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierProductRead:
    return supplier_product_service.update_product(db, session.marketplace_supplier_id, product_id, payload)


# ---- PLAT-041: RFQ inbox and quotations ----------------------------------------------------------


@router.get("/rfqs", response_model=list[SupplierRfqInboxItem])
def list_rfq_inbox(status: str | None = Query(default=None), session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierRfqInboxItem]:
    return supplier_rfq_service.list_inbox(db, session.marketplace_supplier_id, status)


@router.get("/rfqs/{rfq_id}", response_model=SupplierRfqDetail)
def get_rfq_detail(rfq_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierRfqDetail:
    return supplier_rfq_service.get_detail(db, session.marketplace_supplier_id, rfq_id)


@router.get("/rfqs/{rfq_id}/ai/summary", response_model=AiNarrationResponse)
def ai_rfq_summary(rfq_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_dependency)) -> AiNarrationResponse:
    """A requirements summary plus a suggested quotation checklist (PLAT-048)
    -- built only from this real RFQ, which get_detail already 404s on if
    this supplier wasn't actually invited to it (never a competitor's RFQ,
    never invented items)."""
    rfq = supplier_rfq_service.get_detail(db, session.marketplace_supplier_id, rfq_id)
    items = "\n".join(f"- {i.material_name}: {i.quantity} {i.unit}" for i in rfq.items)
    data = f"RFQ {rfq.rfq_number} from {rfq.company_name}: {rfq.title}\nYour invitation status: {rfq.invitation_status}\nItems requested:\n{items}\nNotes: {rfq.notes or 'none'}\nYour quotation so far: {'none submitted yet' if not rfq.my_quotation else f'total {rfq.my_quotation.total}, delivery_days {rfq.my_quotation.delivery_days}'}"
    text = generate_narration(
        llm,
        "You are an assistant for a marketplace supplier responding to a construction company's RFQ. You are "
        "advisory only -- you never submit a quotation or decline the invitation; the supplier does that separately.",
        f"Summarize what this RFQ is asking for, then give a short checklist of things to confirm before quoting "
        f"(pricing per item, delivery timeline, validity period, any notes) -- using only the real data below:\n\n{data}",
        actor_key=f"supplier-user:{session.user.id}", feature="supplier_rfq_summary",
    )
    return AiNarrationResponse(narration=text)


@router.post("/rfqs/{rfq_id}/decline", status_code=204)
def decline_rfq(rfq_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> None:
    supplier_rfq_service.decline_invitation(db, session.marketplace_supplier_id, rfq_id)


@router.post("/rfqs/{rfq_id}/quotations", response_model=SupplierOwnQuotation, status_code=201)
def submit_quotation(rfq_id: uuid.UUID, payload: SupplierQuotationSubmit, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierOwnQuotation:
    return supplier_rfq_service.submit_quotation(db, session.marketplace_supplier_id, session.user.id, rfq_id, payload)


@router.get("/quotations", response_model=list[SupplierQuotationHistoryItem])
def list_quotation_history(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierQuotationHistoryItem]:
    return supplier_rfq_service.list_quotation_history(db, session.marketplace_supplier_id)


# ---- PLAT-042: orders, delivery, commission statements --------------------------------------------


@router.get("/orders", response_model=list[SupplierOrderRead])
def list_orders(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierOrderRead]:
    return supplier_order_service.list_orders(db, session.marketplace_supplier_id)


@router.get("/orders/{po_id}", response_model=SupplierOrderRead)
def get_order(po_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierOrderRead:
    return supplier_order_service.get_order(db, session.marketplace_supplier_id, po_id)


@router.get("/orders/{po_id}/delivery-updates", response_model=list[SupplierDeliveryUpdateRead])
def list_delivery_updates(po_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupplierDeliveryUpdateRead]:
    return supplier_order_service.list_delivery_updates(db, session.marketplace_supplier_id, po_id)


@router.post("/orders/{po_id}/delivery-updates", response_model=SupplierDeliveryUpdateRead, status_code=201)
def submit_delivery_update(po_id: uuid.UUID, payload: SupplierDeliveryUpdateCreate, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupplierDeliveryUpdateRead:
    return supplier_order_service.submit_delivery_update(db, session.marketplace_supplier_id, session.user.id, po_id, payload)


@router.get("/commissions/agreements", response_model=list[CommissionAgreementRead])
def list_my_agreements(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[CommissionAgreementRead]:
    return supplier_commission_service.list_my_agreements(db, session.marketplace_supplier_id)


@router.get("/commissions/ledger", response_model=list[CommissionLedgerEntryRead])
def list_my_ledger(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[CommissionLedgerEntryRead]:
    return supplier_commission_service.list_my_ledger(db, session.marketplace_supplier_id)


@router.get("/commissions/invoices", response_model=list[CommissionInvoiceRead])
def list_my_invoices(status: CommissionInvoiceStatus | None = None, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[CommissionInvoiceRead]:
    invoices = supplier_commission_service.list_my_invoices(db, session.marketplace_supplier_id)
    return [i for i in invoices if status is None or i.status == status]


@router.get("/commissions/invoices/{invoice_id}", response_model=CommissionInvoiceRead)
def get_my_invoice(invoice_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> CommissionInvoiceRead:
    return supplier_commission_service.get_my_invoice(db, session.marketplace_supplier_id, invoice_id)


@router.get("/commissions/disputes", response_model=list[CommissionDisputeRead])
def list_my_disputes(status: CommissionDisputeStatus | None = None, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[CommissionDisputeRead]:
    disputes = supplier_commission_service.list_my_disputes(db, session.marketplace_supplier_id)
    return [d for d in disputes if status is None or d.status == status]


# ---- Phase 8 (PLAT-046): support desk -----------------------------------------------------------


@router.post("/support", response_model=SupportTicketRead, status_code=201)
def create_support_ticket(payload: SupportTicketCreate, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupportTicketRead:
    return support_ticket_service.create_supplier_ticket(db, session.marketplace_supplier_id, session.user, payload)


@router.get("/support", response_model=list[SupportTicketSummary])
def list_support_tickets(session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> list[SupportTicketSummary]:
    return support_ticket_service.list_supplier_tickets(db, session.marketplace_supplier_id)


@router.get("/support/{ticket_id}", response_model=SupportTicketRead)
def get_support_ticket(ticket_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupportTicketRead:
    return support_ticket_service.get_supplier_ticket(db, session.marketplace_supplier_id, ticket_id)


@router.post("/support/{ticket_id}/messages", response_model=SupportTicketRead, status_code=201)
def reply_support_ticket(ticket_id: uuid.UUID, payload: SupportTicketMessageCreate, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)) -> SupportTicketRead:
    return support_ticket_service.reply_as_supplier(db, session.marketplace_supplier_id, session.user, ticket_id, payload)


# ---- Phase 8 (PLAT-047): notifications ------------------------------------------------------------


@router.get("/notifications")
def list_notifications(unread_only: bool = False, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)):
    rows = supplier_notification_service.list_notifications(db, session.user.id, unread_only)
    return [
        {"id": n.id, "notification_type": n.notification_type, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read, "created_at": n.created_at}
        for n in rows
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: uuid.UUID, session: SupplierSession = Depends(get_current_supplier_user), db: Session = Depends(get_db)):
    n = supplier_notification_service.mark_read(db, session.user.id, notification_id)
    return {"id": n.id, "is_read": n.is_read}
