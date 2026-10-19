"""Supplier-side RFQ inbox and quotation submission (PLAT-041). Reuses the
existing rfq_service.record_quotation exactly as the platform-staff-assisted
path does (marketplace_integration_service.record_quotation_for_marketplace_supplier)
-- same trick of passing the RFQ's own creator as the nominal tenant actor,
since Quotation.created_by_id FKs users.id and neither platform staff nor a
SupplierUser are ever in that table. The real actor is recorded separately
in MarketplaceQuotationAttribution.submitted_by_supplier_user_id, with
method="supplier_self_submitted" -- never silently attributed to staff."""

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.marketplace_supplier import MarketplaceCompanySupplierLink, MarketplaceQuotationAttribution, MarketplaceRfqInvitation
from app.models.material import Material
from app.models.rfq import Quotation, QuotationItem, Rfq, RfqItem
from app.schemas.rfq import QuotationCreate, QuotationItemInput
from app.schemas.supplier_portal import (
    SupplierOwnQuotation,
    SupplierOwnQuotationItem,
    SupplierQuotationHistoryItem,
    SupplierQuotationSubmit,
    SupplierRfqDetail,
    SupplierRfqInboxItem,
    SupplierRfqItemRead,
)
from app.services import marketplace_integration_service, rfq_service


def list_inbox(db: Session, marketplace_supplier_id: uuid.UUID, status_filter: str | None = None) -> list[SupplierRfqInboxItem]:
    query = (
        db.query(MarketplaceRfqInvitation, Rfq, Company.name)
        .join(Rfq, Rfq.id == MarketplaceRfqInvitation.rfq_id)
        .join(Company, Company.id == MarketplaceRfqInvitation.company_id)
        .filter(MarketplaceRfqInvitation.marketplace_supplier_id == marketplace_supplier_id)
    )
    if status_filter:
        query = query.filter(MarketplaceRfqInvitation.status == status_filter)
    rows = query.order_by(MarketplaceRfqInvitation.created_at.desc()).all()
    return [
        SupplierRfqInboxItem(
            invitation_id=inv.id, rfq_id=rfq.id, rfq_number=rfq.rfq_number, title=rfq.title, company_name=company_name,
            status=inv.status, response_due=rfq.response_due, created_at=inv.created_at,
        )
        for inv, rfq, company_name in rows
    ]


def _get_invitation(db: Session, marketplace_supplier_id: uuid.UUID, rfq_id: uuid.UUID) -> MarketplaceRfqInvitation:
    invitation = (
        db.query(MarketplaceRfqInvitation)
        .filter(MarketplaceRfqInvitation.marketplace_supplier_id == marketplace_supplier_id, MarketplaceRfqInvitation.rfq_id == rfq_id)
        .first()
    )
    if not invitation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You weren't invited to this RFQ")
    return invitation


def get_detail(db: Session, marketplace_supplier_id: uuid.UUID, rfq_id: uuid.UUID) -> SupplierRfqDetail:
    """Never returns other suppliers' invitation rows or quotations -- only
    this RFQ's own material requirements and the caller's own state."""
    invitation = _get_invitation(db, marketplace_supplier_id, rfq_id)
    rfq = db.query(Rfq).filter(Rfq.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "RFQ not found")
    company = db.query(Company).filter(Company.id == rfq.company_id).first()

    items = (
        db.query(RfqItem, Material.name, Material.unit)
        .join(Material, Material.id == RfqItem.material_id)
        .filter(RfqItem.rfq_id == rfq_id)
        .all()
    )
    item_reads = [SupplierRfqItemRead(id=i.id, material_name=name, unit=unit, quantity=i.quantity) for i, name, unit in items]

    link = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(MarketplaceCompanySupplierLink.company_id == rfq.company_id, MarketplaceCompanySupplierLink.marketplace_supplier_id == marketplace_supplier_id)
        .first()
    )
    my_quotation = None
    if link and link.erp_supplier_id:
        quotation = db.query(Quotation).filter(Quotation.rfq_id == rfq_id, Quotation.supplier_id == link.erp_supplier_id).first()
        if quotation:
            q_items = db.query(QuotationItem).filter(QuotationItem.quotation_id == quotation.id).all()
            quantities = {i.id: i.quantity for i in [row[0] for row in items]}
            my_quotation = SupplierOwnQuotation(
                id=quotation.id, delivery_days=quotation.delivery_days, valid_until=quotation.valid_until, notes=quotation.notes,
                total=sum((qi.rate * quantities.get(qi.rfq_item_id, Decimal("0")) for qi in q_items), Decimal("0")).quantize(Decimal("0.01")),
                created_at=quotation.created_at,
                items=[SupplierOwnQuotationItem(rfq_item_id=qi.rfq_item_id, rate=qi.rate, amount=(qi.rate * quantities.get(qi.rfq_item_id, Decimal("0"))).quantize(Decimal("0.01"))) for qi in q_items],
            )

    return SupplierRfqDetail(
        rfq_id=rfq.id, rfq_number=rfq.rfq_number, title=rfq.title, company_name=company.name if company else "Unknown",
        notes=rfq.notes, response_due=rfq.response_due, rfq_status=rfq.status.value, invitation_status=invitation.status,
        items=item_reads, my_quotation=my_quotation,
    )


def decline_invitation(db: Session, marketplace_supplier_id: uuid.UUID, rfq_id: uuid.UUID) -> None:
    invitation = _get_invitation(db, marketplace_supplier_id, rfq_id)
    if invitation.status != "invited":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Can't decline an invitation that's already {invitation.status}")
    invitation.status = "declined"
    db.commit()


def submit_quotation(db: Session, marketplace_supplier_id: uuid.UUID, supplier_user_id: uuid.UUID, rfq_id: uuid.UUID, payload: SupplierQuotationSubmit) -> SupplierOwnQuotation:
    """A supplier may submit a quotation only for an authorized invitation --
    enforced by requiring a real MarketplaceRfqInvitation row below -- and
    only one not already declined."""
    invitation = _get_invitation(db, marketplace_supplier_id, rfq_id)
    if invitation.status == "declined":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You declined this invitation and can no longer quote on it")

    rfq = db.query(Rfq).filter(Rfq.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "RFQ not found")

    marketplace_integration_service.ensure_marketplace_enabled(db, rfq.company_id)
    link = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(MarketplaceCompanySupplierLink.company_id == rfq.company_id, MarketplaceCompanySupplierLink.marketplace_supplier_id == marketplace_supplier_id, MarketplaceCompanySupplierLink.status == "active")
        .first()
    )
    if not link or not link.erp_supplier_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This company hasn't connected with you yet")

    quotation_payload = QuotationCreate(
        supplier_id=link.erp_supplier_id, delivery_days=payload.delivery_days, valid_until=payload.valid_until, notes=payload.notes,
        items=[QuotationItemInput(rfq_item_id=i.rfq_item_id, rate=i.rate) for i in payload.items],
    )
    result = rfq_service.record_quotation(db, rfq.company_id, rfq.created_by_id, rfq_id, quotation_payload)
    marketplace_integration_service.mark_invitation_quoted(db, rfq.company_id, rfq_id, link.erp_supplier_id)

    quotation = next(q for q in result.quotations if q.supplier_id == link.erp_supplier_id)
    quantities = {i.id: i.quantity for i in result.items}
    total = sum((qi.rate * quantities[qi.rfq_item_id] for qi in quotation.items), Decimal("0")).quantize(Decimal("0.01"))

    db.add(
        MarketplaceQuotationAttribution(
            company_id=rfq.company_id, rfq_id=rfq_id, quotation_id=quotation.id, marketplace_supplier_id=marketplace_supplier_id,
            submitted_by_supplier_user_id=supplier_user_id, method="supplier_self_submitted", total_amount=total,
        )
    )
    db.commit()
    return get_detail(db, marketplace_supplier_id, rfq_id).my_quotation


def list_quotation_history(db: Session, marketplace_supplier_id: uuid.UUID) -> list[SupplierQuotationHistoryItem]:
    rows = (
        db.query(MarketplaceQuotationAttribution, Rfq, Company.name)
        .join(Rfq, Rfq.id == MarketplaceQuotationAttribution.rfq_id)
        .join(Company, Company.id == MarketplaceQuotationAttribution.company_id)
        .filter(MarketplaceQuotationAttribution.marketplace_supplier_id == marketplace_supplier_id)
        .order_by(MarketplaceQuotationAttribution.created_at.desc())
        .all()
    )
    return [
        SupplierQuotationHistoryItem(rfq_id=rfq.id, rfq_number=rfq.rfq_number, company_name=company_name, total=a.total_amount, submitted_at=a.created_at)
        for a, rfq, company_name in rows
    ]
