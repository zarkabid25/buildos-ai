import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.ai.llm import LLMClient, get_llm_dependency
from app.ai.narrate import generate_narration
from app.api.deps import get_current_user, require_roles
from app.api.v1.procurement import CAN_REQUEST
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.ai import AiNarrationResponse
from app.schemas.marketplace_integration import (
    CompanySupplierConnectionRead,
    ConnectSupplierRequest,
    DiscoverySupplierDetail,
    DiscoverySupplierRead,
    InviteSuppliersRequest,
    MarketplaceInvitationRead,
    MarketplaceOrderStatus,
    QuotationAttributionRead,
    UpdateConnectionRequest,
)
from app.services import ai_quota_service, entitlement_service, marketplace_integration_service

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class MarketplaceStatus(BaseModel):
    enabled: bool


@router.get("/status", response_model=MarketplaceStatus)
def marketplace_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MarketplaceStatus:
    operational_flag = db.query(Company.marketplace_enabled).filter(Company.id == current_user.company_id).scalar()
    enabled = entitlement_service.effective_marketplace_enabled(db, current_user.company_id, bool(operational_flag))
    return MarketplaceStatus(enabled=enabled)


@router.get("/suppliers", response_model=list[DiscoverySupplierRead])
def discover_suppliers(
    search: str | None = None,
    category: str | None = None,
    area: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DiscoverySupplierRead]:
    return marketplace_integration_service.discover_suppliers(db, current_user.company_id, search, category, area)


@router.get("/suppliers/{supplier_id}", response_model=DiscoverySupplierDetail)
def get_supplier_detail(
    supplier_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DiscoverySupplierDetail:
    return marketplace_integration_service.get_supplier_detail(db, current_user.company_id, supplier_id)


@router.get("/suppliers/{supplier_id}/ai/recommendation", response_model=AiNarrationResponse)
def ai_recommendation(
    supplier_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_dependency),
) -> AiNarrationResponse:
    """Explains why this specific, real supplier profile might fit the
    company's needs (PLAT-048) -- never invents a price, since none of this
    supplier's real product prices are included unless they're already on
    its real catalog below."""
    supplier = marketplace_integration_service.get_supplier_detail(db, current_user.company_id, supplier_id)
    data = (
        f"Supplier: {supplier.name}\nVerification: {supplier.verification_status.value}\nCategories: {supplier.categories}\n"
        f"Coverage areas: {supplier.coverage_areas}\nAlready connected: {supplier.is_connected}\nPreferred: {supplier.is_preferred}\n"
        f"Products: {[(p.name, p.category, str(p.price), p.unit, p.lead_time_days) for p in supplier.products]}"
    )
    ai_quota_service.reserve_usage(db, current_user.company_id)
    text = generate_narration(
        llm,
        "You are an assistant for a construction company evaluating a marketplace supplier. You are advisory only -- "
        "you never create a connection, an RFQ invitation, or a purchase order; a human does that separately.",
        f"Based only on the real supplier profile below, explain what this supplier might be a good fit for and anything worth double-checking:\n\n{data}",
        actor_key=f"user:{current_user.id}", feature="supplier_recommendation",
    )
    return AiNarrationResponse(narration=text)


@router.post("/suppliers/{supplier_id}/connect", response_model=CompanySupplierConnectionRead, status_code=201)
def connect_supplier(
    supplier_id: uuid.UUID,
    payload: ConnectSupplierRequest,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> CompanySupplierConnectionRead:
    return marketplace_integration_service.connect_supplier(
        db, current_user.company_id, supplier_id, payload, actor_user_id=current_user.id
    )


@router.get("/connections", response_model=list[CompanySupplierConnectionRead])
def list_connections(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[CompanySupplierConnectionRead]:
    return marketplace_integration_service.list_connections(db, current_user.company_id)


@router.patch("/connections/{link_id}", response_model=CompanySupplierConnectionRead)
def update_connection(
    link_id: uuid.UUID,
    payload: UpdateConnectionRequest,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> CompanySupplierConnectionRead:
    return marketplace_integration_service.update_connection(db, current_user.company_id, link_id, payload)


@router.post("/rfqs/{rfq_id}/invite-suppliers", response_model=list[MarketplaceInvitationRead], status_code=201)
def invite_suppliers(
    rfq_id: uuid.UUID,
    payload: InviteSuppliersRequest,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> list[MarketplaceInvitationRead]:
    return marketplace_integration_service.invite_suppliers(
        db, current_user.company_id, rfq_id, payload.marketplace_supplier_ids, actor_user_id=current_user.id
    )


@router.get("/rfqs/{rfq_id}/invitations", response_model=list[MarketplaceInvitationRead])
def list_invitations(
    rfq_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MarketplaceInvitationRead]:
    return marketplace_integration_service.list_invitations(db, current_user.company_id, rfq_id)


@router.get("/purchase-orders/{po_id}/status", response_model=MarketplaceOrderStatus)
def order_status(
    po_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MarketplaceOrderStatus:
    return marketplace_integration_service.get_order_status(db, current_user.company_id, po_id)


@router.get("/rfqs/{rfq_id}/quotation-attributions", response_model=list[QuotationAttributionRead])
def quotation_attributions(
    rfq_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[QuotationAttributionRead]:
    return marketplace_integration_service.get_quotation_attributions(db, current_user.company_id, rfq_id)
