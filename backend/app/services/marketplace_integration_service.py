"""The bridge between the marketplace supplier registry and the existing ERP
procurement flow (PLAT-021..027). This module never duplicates ERP business
logic -- it only calls rfq_service, procurement_service and supplier_service
exactly as any other caller would, with the marketplace-specific bookkeeping
(connections, invitations, delivery reports) layered on top. Nothing here
posts to InventoryTransaction directly; that only ever happens inside
procurement_service.create_goods_receipt."""

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.enums import MarketplaceSupplierStatus, RfqStatus
from app.models.marketplace_supplier import (
    MarketplaceCompanySupplierLink,
    MarketplaceDeliveryReport,
    MarketplaceMaterialMapping,
    MarketplaceProduct,
    MarketplaceQuotationAttribution,
    MarketplaceRfqInvitation,
    MarketplaceSupplier,
    MarketplaceSupplierCategory,
    MarketplaceSupplierCoverageArea,
)
from app.models.material import MaterialCategory
from app.models.platform_admin import PlatformAdmin
from app.models.procurement import GoodsReceipt
from app.models.rfq import Rfq, RfqSupplier
from app.schemas.marketplace_integration import (
    AssistedQuotationCreate,
    CompanySupplierConnectionRead,
    ConnectSupplierRequest,
    DeliveryReportCreate,
    DeliveryReportRead,
    DiscoveryProductRead,
    DiscoverySupplierDetail,
    DiscoverySupplierRead,
    MarketplaceInvitationRead,
    MarketplaceOrderStatus,
    QuotationAttributionRead,
    SupplierMatch,
    UpdateConnectionRequest,
)
from app.schemas.rfq import QuotationCreate
from app.schemas.supplier import SupplierCreate
from app.services import audit_service, platform_audit_service, procurement_service, rfq_service, supplier_service
from app.services.material_service import get_material


def ensure_marketplace_enabled(db: Session, company_id: uuid.UUID) -> None:
    """The single choke point every marketplace *action* (never a read of
    already-existing historical data) passes through. Disabled by default per
    company (Phase 4.1 Task 4); a future subscription/entitlement check can be
    added here without touching any call site."""
    enabled = db.query(Company.marketplace_enabled).filter(Company.id == company_id).scalar()
    if enabled is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    if not enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The marketplace isn't enabled for this company yet")


def _get_marketplace_supplier(db: Session, marketplace_supplier_id: uuid.UUID) -> MarketplaceSupplier:
    supplier = db.query(MarketplaceSupplier).filter(MarketplaceSupplier.id == marketplace_supplier_id).first()
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marketplace supplier not found")
    return supplier


def _tags(db: Session, model, supplier_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    out: dict[uuid.UUID, list[str]] = {sid: [] for sid in supplier_ids}
    if not supplier_ids:
        return out
    col = model.category if model is MarketplaceSupplierCategory else model.area
    rows = db.query(model.supplier_id, col).filter(model.supplier_id.in_(supplier_ids)).all()
    for sid, value in rows:
        out.setdefault(sid, []).append(value)
    return out


def _connections_for_company(db: Session, company_id: uuid.UUID) -> dict[uuid.UUID, MarketplaceCompanySupplierLink]:
    links = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(MarketplaceCompanySupplierLink.company_id == company_id)
        .all()
    )
    return {link.marketplace_supplier_id: link for link in links}


# ---- PLAT-021: company-facing discovery (verified suppliers only) --------------------


def discover_suppliers(
    db: Session, company_id: uuid.UUID, search: str | None = None, category: str | None = None, area: str | None = None
) -> list[DiscoverySupplierRead]:
    ensure_marketplace_enabled(db, company_id)
    query = db.query(MarketplaceSupplier).filter(MarketplaceSupplier.verification_status == MarketplaceSupplierStatus.VERIFIED)
    if search:
        query = query.filter(MarketplaceSupplier.name.ilike(f"%{search.strip()}%"))
    if category:
        query = query.join(MarketplaceSupplierCategory).filter(
            MarketplaceSupplierCategory.category.ilike(category.strip())
        )
    if area:
        query = query.join(MarketplaceSupplierCoverageArea).filter(
            MarketplaceSupplierCoverageArea.area.ilike(area.strip())
        )
    suppliers = query.order_by(MarketplaceSupplier.name.asc()).all()

    ids = [s.id for s in suppliers]
    cats = _tags(db, MarketplaceSupplierCategory, ids)
    areas = _tags(db, MarketplaceSupplierCoverageArea, ids)
    connections = _connections_for_company(db, company_id)

    return [
        DiscoverySupplierRead(
            id=s.id,
            name=s.name,
            categories=sorted(set(cats.get(s.id, []))),
            coverage_areas=sorted(set(areas.get(s.id, []))),
            verification_status=s.verification_status,
            is_connected=s.id in connections,
            is_preferred=connections[s.id].is_preferred if s.id in connections else False,
        )
        for s in suppliers
    ]


def get_supplier_detail(db: Session, company_id: uuid.UUID, marketplace_supplier_id: uuid.UUID) -> DiscoverySupplierDetail:
    ensure_marketplace_enabled(db, company_id)
    supplier = _get_marketplace_supplier(db, marketplace_supplier_id)
    if supplier.verification_status != MarketplaceSupplierStatus.VERIFIED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marketplace supplier not found")

    cats = _tags(db, MarketplaceSupplierCategory, [supplier.id])
    areas = _tags(db, MarketplaceSupplierCoverageArea, [supplier.id])
    connection = _connections_for_company(db, company_id).get(supplier.id)
    products = (
        db.query(MarketplaceProduct)
        .filter(MarketplaceProduct.supplier_id == supplier.id, MarketplaceProduct.is_active.is_(True))
        .order_by(MarketplaceProduct.name.asc())
        .all()
    )
    return DiscoverySupplierDetail(
        id=supplier.id,
        name=supplier.name,
        categories=sorted(set(cats.get(supplier.id, []))),
        coverage_areas=sorted(set(areas.get(supplier.id, []))),
        verification_status=supplier.verification_status,
        is_connected=connection is not None,
        is_preferred=connection.is_preferred if connection else False,
        products=[DiscoveryProductRead.model_validate(p) for p in products],
    )


# ---- PLAT-022: company-supplier relationships ------------------------------------------


def connect_supplier(
    db: Session,
    company_id: uuid.UUID,
    marketplace_supplier_id: uuid.UUID,
    payload: ConnectSupplierRequest,
    actor_user_id: uuid.UUID | None = None,
    actor_staff_id: uuid.UUID | None = None,
) -> CompanySupplierConnectionRead:
    ensure_marketplace_enabled(db, company_id)
    mkt_supplier = _get_marketplace_supplier(db, marketplace_supplier_id)
    if mkt_supplier.verification_status != MarketplaceSupplierStatus.VERIFIED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a verified supplier can be connected")

    existing = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(
            MarketplaceCompanySupplierLink.company_id == company_id,
            MarketplaceCompanySupplierLink.marketplace_supplier_id == marketplace_supplier_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This company is already connected to this supplier")

    if payload.link_existing_erp_supplier_id and payload.create_new_erp_supplier:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Give either an existing supplier to link or ask to create one, not both")

    erp_supplier_id = None
    if payload.link_existing_erp_supplier_id:
        erp_supplier = supplier_service.get_supplier(db, company_id, payload.link_existing_erp_supplier_id)
        erp_supplier_id = erp_supplier.id
    elif payload.create_new_erp_supplier:
        erp_supplier = supplier_service.create_supplier(
            db,
            company_id,
            SupplierCreate(name=mkt_supplier.name, email=mkt_supplier.email, phone=mkt_supplier.phone, address=mkt_supplier.address),
        )
        erp_supplier_id = erp_supplier.id

    link = MarketplaceCompanySupplierLink(
        company_id=company_id,
        marketplace_supplier_id=marketplace_supplier_id,
        erp_supplier_id=erp_supplier_id,
        is_preferred=payload.is_preferred,
        linked_by_user_id=actor_user_id,
        linked_by_id=actor_staff_id,
        notes=payload.notes,
    )
    db.add(link)
    if actor_user_id:
        audit_service.record(
            db, company_id, actor_user_id, "marketplace.supplier_connected", "marketplace_supplier", marketplace_supplier_id,
            f"Connected to {mkt_supplier.name}",
        )
    if actor_staff_id:
        platform_audit_service.record(
            db, actor_staff_id, "marketplace_supplier.company_linked", "marketplace_supplier", marketplace_supplier_id,
            f"Connected to company (assisted)",
        )
    db.commit()
    db.refresh(link)
    return CompanySupplierConnectionRead(**CompanySupplierConnectionRead.model_validate(link).model_dump(exclude={"marketplace_supplier_name"}), marketplace_supplier_name=mkt_supplier.name)


def list_connections(db: Session, company_id: uuid.UUID) -> list[CompanySupplierConnectionRead]:
    rows = (
        db.query(MarketplaceCompanySupplierLink, MarketplaceSupplier.name)
        .join(MarketplaceSupplier, MarketplaceSupplier.id == MarketplaceCompanySupplierLink.marketplace_supplier_id)
        .filter(MarketplaceCompanySupplierLink.company_id == company_id)
        .order_by(MarketplaceCompanySupplierLink.created_at.desc())
        .all()
    )
    return [
        CompanySupplierConnectionRead(**CompanySupplierConnectionRead.model_validate(link).model_dump(exclude={"marketplace_supplier_name"}), marketplace_supplier_name=name)
        for link, name in rows
    ]


def update_connection(
    db: Session, company_id: uuid.UUID, link_id: uuid.UUID, payload: UpdateConnectionRequest
) -> CompanySupplierConnectionRead:
    link = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(MarketplaceCompanySupplierLink.id == link_id, MarketplaceCompanySupplierLink.company_id == company_id)
        .first()
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    if payload.is_preferred is not None:
        link.is_preferred = payload.is_preferred
    if payload.status is not None:
        link.status = payload.status
    db.commit()
    db.refresh(link)
    name = db.query(MarketplaceSupplier.name).filter(MarketplaceSupplier.id == link.marketplace_supplier_id).scalar()
    return CompanySupplierConnectionRead(**CompanySupplierConnectionRead.model_validate(link).model_dump(exclude={"marketplace_supplier_name"}), marketplace_supplier_name=name)


# ---- PLAT-023: marketplace RFQ invitations, reusing the real RFQ/RfqSupplier ----------


def invite_suppliers(
    db: Session,
    company_id: uuid.UUID,
    rfq_id: uuid.UUID,
    marketplace_supplier_ids: list[uuid.UUID],
    actor_user_id: uuid.UUID | None = None,
    actor_staff_id: uuid.UUID | None = None,
) -> list[MarketplaceInvitationRead]:
    ensure_marketplace_enabled(db, company_id)
    # get_rfq enforces tenant isolation: a company can never invite marketplace
    # suppliers onto an RFQ it doesn't own, the same way every other RFQ action does.
    rfq = rfq_service.get_rfq(db, company_id, rfq_id)
    if rfq.status != RfqStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{rfq.rfq_number} is already {rfq.status.value}")

    links = _connections_for_company(db, company_id)
    already_invited_erp_ids = {s.supplier_id for s in rfq.invited}
    created: list[MarketplaceRfqInvitation] = []

    for marketplace_supplier_id in dict.fromkeys(marketplace_supplier_ids):
        link = links.get(marketplace_supplier_id)
        if not link or link.status != "active":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This company isn't connected to that supplier")
        if not link.erp_supplier_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This connection has no linked ERP supplier yet -- link or create one first")

        mkt_supplier = _get_marketplace_supplier(db, marketplace_supplier_id)
        if mkt_supplier.verification_status != MarketplaceSupplierStatus.VERIFIED:
            # Requirement 7: only eligible (verified) suppliers may receive new
            # invitations -- a suspended or rejected supplier is refused here.
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{mkt_supplier.name} isn't currently eligible for new RFQ invitations")

        existing_invitation = (
            db.query(MarketplaceRfqInvitation)
            .filter(MarketplaceRfqInvitation.rfq_id == rfq_id, MarketplaceRfqInvitation.marketplace_supplier_id == marketplace_supplier_id)
            .first()
        )
        if existing_invitation:
            raise HTTPException(status.HTTP_409_CONFLICT, f"{mkt_supplier.name} has already been invited to this RFQ")

        if link.erp_supplier_id not in already_invited_erp_ids:
            db.add(RfqSupplier(company_id=company_id, rfq_id=rfq_id, supplier_id=link.erp_supplier_id))
            already_invited_erp_ids.add(link.erp_supplier_id)

        invitation = MarketplaceRfqInvitation(
            company_id=company_id,
            rfq_id=rfq_id,
            marketplace_supplier_id=marketplace_supplier_id,
            invited_by_user_id=actor_user_id,
            invited_by_staff_id=actor_staff_id,
        )
        db.add(invitation)
        created.append(invitation)

    if actor_user_id:
        audit_service.record(db, company_id, actor_user_id, "marketplace.rfq_invitations_sent", "rfq", rfq.id, f"{len(created)} marketplace supplier(s) invited to {rfq.rfq_number}")
    if actor_staff_id:
        platform_audit_service.record(db, actor_staff_id, "marketplace_supplier.rfq_invited", "rfq", rfq.id, f"Assisted inviting {len(created)} supplier(s) to {rfq.rfq_number}")

    db.commit()
    names = {s.id: s.name for s in db.query(MarketplaceSupplier).filter(MarketplaceSupplier.id.in_([i.marketplace_supplier_id for i in created]))}
    for i in created:
        db.refresh(i)
    return [
        MarketplaceInvitationRead(**MarketplaceInvitationRead.model_validate(i).model_dump(exclude={"marketplace_supplier_name"}), marketplace_supplier_name=names.get(i.marketplace_supplier_id))
        for i in created
    ]


def list_invitations(db: Session, company_id: uuid.UUID, rfq_id: uuid.UUID) -> list[MarketplaceInvitationRead]:
    rfq_service.get_rfq(db, company_id, rfq_id)  # isolation
    rows = (
        db.query(MarketplaceRfqInvitation, MarketplaceSupplier.name)
        .join(MarketplaceSupplier, MarketplaceSupplier.id == MarketplaceRfqInvitation.marketplace_supplier_id)
        .filter(MarketplaceRfqInvitation.rfq_id == rfq_id)
        .order_by(MarketplaceRfqInvitation.created_at.desc())
        .all()
    )
    return [
        MarketplaceInvitationRead(**MarketplaceInvitationRead.model_validate(inv).model_dump(exclude={"marketplace_supplier_name"}), marketplace_supplier_name=name)
        for inv, name in rows
    ]


def mark_invitation_quoted(db: Session, company_id: uuid.UUID, rfq_id: uuid.UUID, erp_supplier_id: uuid.UUID) -> None:
    """Called after a quotation is recorded for a supplier that came from the
    marketplace, so the invitation list reflects reality. A no-op if this
    wasn't a marketplace-sourced supplier."""
    link = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(MarketplaceCompanySupplierLink.company_id == company_id, MarketplaceCompanySupplierLink.erp_supplier_id == erp_supplier_id)
        .first()
    )
    if not link:
        return
    invitation = (
        db.query(MarketplaceRfqInvitation)
        .filter(MarketplaceRfqInvitation.rfq_id == rfq_id, MarketplaceRfqInvitation.marketplace_supplier_id == link.marketplace_supplier_id)
        .first()
    )
    if invitation and invitation.status == "invited":
        invitation.status = "quoted"


# ---- PLAT-024: platform-staff-assisted quotation entry, reusing rfq_service -----------


def record_quotation_for_marketplace_supplier(
    db: Session,
    actor_staff_id: uuid.UUID,
    company_id: uuid.UUID,
    rfq_id: uuid.UUID,
    marketplace_supplier_id: uuid.UUID,
    payload: AssistedQuotationCreate,
) -> Rfq:
    """Platform staff entering a quotation on a connected marketplace supplier's
    behalf. Quotation.created_by_id is never repurposed for this: it keeps
    correctly recording the RFQ's own creator (a real tenant user), since
    platform staff deliberately aren't in the users table (see PlatformAdmin's
    own docstring) and that FK's existing meaning/behaviour is left untouched.
    The real actor, the supplier represented, the resulting quotation id, and
    the submission time are instead recorded in a separate, additive,
    insert-only MarketplaceQuotationAttribution row -- the immutable audit
    trail for "who actually typed this in." See get_quotation_attributions."""
    ensure_marketplace_enabled(db, company_id)
    rfq = rfq_service.get_rfq(db, company_id, rfq_id)
    link = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(MarketplaceCompanySupplierLink.company_id == company_id, MarketplaceCompanySupplierLink.marketplace_supplier_id == marketplace_supplier_id)
        .first()
    )
    if not link or not link.erp_supplier_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This supplier isn't connected with a linked ERP supplier yet")

    quotation_payload = QuotationCreate(supplier_id=link.erp_supplier_id, **payload.model_dump())
    result = rfq_service.record_quotation(db, company_id, rfq.created_by_id, rfq_id, quotation_payload)
    mark_invitation_quoted(db, company_id, rfq_id, link.erp_supplier_id)
    mkt_supplier = _get_marketplace_supplier(db, marketplace_supplier_id)

    quotation = next(q for q in result.quotations if q.supplier_id == link.erp_supplier_id)
    total = sum((qi.rate * next(i.quantity for i in result.items if i.id == qi.rfq_item_id) for qi in quotation.items), Decimal("0"))
    db.add(
        MarketplaceQuotationAttribution(
            company_id=company_id,
            rfq_id=rfq_id,
            quotation_id=quotation.id,
            marketplace_supplier_id=marketplace_supplier_id,
            submitted_by_staff_id=actor_staff_id,
            total_amount=total.quantize(Decimal("0.01")),
        )
    )
    platform_audit_service.record(
        db, actor_staff_id, "marketplace_supplier.quotation_recorded", "rfq", rfq_id,
        f"Recorded a quotation from {mkt_supplier.name} on {rfq.rfq_number} (on their behalf)",
        {"quotation_id": str(quotation.id), "total": str(total.quantize(Decimal('0.01')))},
    )
    db.commit()
    return result


def get_quotation_attributions(db: Session, company_id: uuid.UUID, rfq_id: uuid.UUID) -> list[QuotationAttributionRead]:
    """Every platform-staff-assisted submission on this RFQ, in order -- the
    honest record of who actually entered each quotation, separate from
    (and never overriding) Quotation.created_by_id."""
    rfq_service.get_rfq(db, company_id, rfq_id)  # isolation
    rows = (
        db.query(MarketplaceQuotationAttribution, MarketplaceSupplier.name, PlatformAdmin.full_name)
        .join(MarketplaceSupplier, MarketplaceSupplier.id == MarketplaceQuotationAttribution.marketplace_supplier_id)
        .join(PlatformAdmin, PlatformAdmin.id == MarketplaceQuotationAttribution.submitted_by_staff_id)
        .filter(MarketplaceQuotationAttribution.rfq_id == rfq_id)
        .order_by(MarketplaceQuotationAttribution.created_at.desc())
        .all()
    )
    return [
        QuotationAttributionRead(
            id=a.id,
            quotation_id=a.quotation_id,
            marketplace_supplier_id=a.marketplace_supplier_id,
            marketplace_supplier_name=supplier_name,
            submitted_by_staff_id=a.submitted_by_staff_id,
            submitted_by_staff_name=staff_name,
            method=a.method,
            total_amount=a.total_amount,
            created_at=a.created_at,
        )
        for a, supplier_name, staff_name in rows
    ]


# ---- PLAT-025/026: real PO status, idempotent delivery reporting ----------------------


def get_order_status(db: Session, company_id: uuid.UUID, po_id: uuid.UUID) -> MarketplaceOrderStatus:
    po = procurement_service.get_purchase_order(db, company_id, po_id)  # isolation
    receipt_count = db.query(GoodsReceipt).filter(GoodsReceipt.company_id == company_id, GoodsReceipt.purchase_order_id == po_id).count()
    last_report = (
        db.query(MarketplaceDeliveryReport)
        .filter(MarketplaceDeliveryReport.purchase_order_id == po_id)
        .order_by(MarketplaceDeliveryReport.created_at.desc())
        .first()
    )
    return MarketplaceOrderStatus(
        purchase_order_id=po.id,
        po_number=po.po_number,
        status=po.status.value,
        total_amount=po.total_amount.quantize(Decimal("0.01")),
        amount_paid=po.amount_paid.quantize(Decimal("0.01")),
        goods_receipt_count=receipt_count,
        fully_received=all(item.quantity_received >= item.quantity for item in po.items),
        delivery_reported=last_report is not None,
        last_delivery_report_at=last_report.created_at if last_report else None,
    )


def report_delivery(
    db: Session, actor_staff_id: uuid.UUID, company_id: uuid.UUID, po_id: uuid.UUID, payload: DeliveryReportCreate
) -> DeliveryReportRead:
    procurement_service.get_purchase_order(db, company_id, po_id)  # isolation; never touched beyond this read

    existing = (
        db.query(MarketplaceDeliveryReport)
        .filter(MarketplaceDeliveryReport.purchase_order_id == po_id, MarketplaceDeliveryReport.external_reference == payload.external_reference)
        .first()
    )
    if existing:
        return DeliveryReportRead(**DeliveryReportRead.model_validate(existing).model_dump(exclude={"already_recorded"}), already_recorded=True)

    report = MarketplaceDeliveryReport(
        company_id=company_id,
        purchase_order_id=po_id,
        external_reference=payload.external_reference,
        note=payload.note,
        reported_by_staff_id=actor_staff_id,
    )
    db.add(report)
    platform_audit_service.record(
        db, actor_staff_id, "marketplace_supplier.delivery_reported", "purchase_order", po_id,
        f"Delivery reported (ref {payload.external_reference})",
    )
    db.commit()
    db.refresh(report)
    return DeliveryReportRead(**DeliveryReportRead.model_validate(report).model_dump(exclude={"already_recorded"}), already_recorded=False)


# ---- PLAT-027: deterministic supplier matching -----------------------------------------


def find_eligible_suppliers(db: Session, company_id: uuid.UUID, material_id: uuid.UUID, area: str | None = None) -> list[SupplierMatch]:
    material = get_material(db, company_id, material_id)  # isolation + 404
    category_name = None
    if material.category_id:
        category_name = db.query(MaterialCategory.name).filter(MaterialCategory.id == material.category_id).scalar()

    results: list[SupplierMatch] = []
    seen_product_ids: set[uuid.UUID] = set()

    # Preferred: an explicit, human-curated mapping (PLAT-020's groundwork, now used).
    mapped = (
        db.query(MarketplaceProduct, MarketplaceSupplier)
        .join(MarketplaceMaterialMapping, MarketplaceMaterialMapping.marketplace_product_id == MarketplaceProduct.id)
        .join(MarketplaceSupplier, MarketplaceSupplier.id == MarketplaceProduct.supplier_id)
        .filter(MarketplaceMaterialMapping.company_id == company_id, MarketplaceMaterialMapping.material_id == material_id)
        .filter(MarketplaceSupplier.verification_status == MarketplaceSupplierStatus.VERIFIED, MarketplaceProduct.is_active.is_(True))
        .all()
    )
    for product, supplier in mapped:
        results.append(_to_match(db, product, supplier, "material_mapping"))
        seen_product_ids.add(product.id)

    # Fallback: category match, only if a category is set on the material.
    # Matches either the supplier's own declared category tags (PLAT-019) or,
    # if set, the product's own (more granular) category field.
    if category_name:
        candidates = (
            db.query(MarketplaceProduct, MarketplaceSupplier)
            .join(MarketplaceSupplier, MarketplaceSupplier.id == MarketplaceProduct.supplier_id)
            .outerjoin(MarketplaceSupplierCategory, MarketplaceSupplierCategory.supplier_id == MarketplaceSupplier.id)
            .filter(MarketplaceSupplier.verification_status == MarketplaceSupplierStatus.VERIFIED, MarketplaceProduct.is_active.is_(True))
            .filter(
                (MarketplaceSupplierCategory.category.ilike(category_name))
                | (MarketplaceProduct.category.ilike(category_name))
            )
            .all()
        )
        for product, supplier in candidates:
            if product.id in seen_product_ids:
                continue
            results.append(_to_match(db, product, supplier, "category"))
            seen_product_ids.add(product.id)

    if area:
        area_lower = area.strip().lower()
        results = [r for r in results if any(a.lower() == area_lower for a in r.coverage_areas)]

    return sorted(results, key=lambda r: r.price)


def _to_match(db: Session, product: MarketplaceProduct, supplier: MarketplaceSupplier, matched_via: str) -> SupplierMatch:
    areas = [a for (a,) in db.query(MarketplaceSupplierCoverageArea.area).filter(MarketplaceSupplierCoverageArea.supplier_id == supplier.id)]
    return SupplierMatch(
        marketplace_supplier_id=supplier.id,
        supplier_name=supplier.name,
        verification_status=supplier.verification_status,
        product_id=product.id,
        product_name=product.name,
        price=product.price,
        minimum_order_quantity=product.minimum_order_quantity,
        lead_time_days=product.lead_time_days,
        coverage_areas=sorted(areas),
        matched_via=matched_via,
    )
