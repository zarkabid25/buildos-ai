"""RFQs, supplier quotations and their comparison (BUILD-041..043).

Awarding a quotation does not buy anything: it drafts a purchase order at the quoted
rates through the normal PO service, which then needs approval like any other PO
(CLAUDE.md rule 14)."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.enums import MaterialRequestStatus, RfqStatus
from app.models.material import Material
from app.models.procurement import PurchaseOrder
from app.models.project import Project
from app.models.rfq import Quotation, QuotationItem, Rfq, RfqItem, RfqSupplier
from app.models.supplier import Supplier
from app.schemas.procurement import PurchaseOrderCreate, PurchaseOrderItemInput
from app.schemas.rfq import (
    InvitedSupplier,
    QuotationCreate,
    QuotationItemRead,
    QuotationRead,
    RfqCreate,
    RfqItemInput,
    RfqItemRead,
    RfqRead,
    RfqSummary,
)
from app.services import audit_service, procurement_service
from app.services.material_service import get_material
from app.services.project_service import get_project
from app.services.supplier_service import get_supplier


def _next_rfq_number(db: Session, company_id: uuid.UUID) -> str:
    count = db.query(Rfq).filter(Rfq.company_id == company_id).count()
    return f"RFQ-{1000 + count + 1}"


def get_rfq(db: Session, company_id: uuid.UUID, rfq_id: uuid.UUID) -> Rfq:
    rfq = (
        db.query(Rfq)
        .options(
            selectinload(Rfq.items),
            selectinload(Rfq.invited),
            selectinload(Rfq.quotations).selectinload(Quotation.items),
        )
        .filter(Rfq.company_id == company_id, Rfq.id == rfq_id)
        .first()
    )
    if not rfq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "RFQ not found")
    return rfq


def _require_open(rfq: Rfq) -> None:
    if rfq.status != RfqStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{rfq.rfq_number} is already {rfq.status.value}")


def _quote_total(quotation: Quotation, quantities: dict[uuid.UUID, Decimal]) -> Decimal:
    return sum((qi.rate * quantities[qi.rfq_item_id] for qi in quotation.items), Decimal("0"))


def create_rfq(db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: RfqCreate) -> Rfq:
    project_id = payload.project_id
    items = list(payload.items)
    if payload.material_request_id:
        request = procurement_service.get_material_request(db, company_id, payload.material_request_id)
        if request.status not in (MaterialRequestStatus.PENDING, MaterialRequestStatus.APPROVED):
            raise HTTPException(status.HTTP_409_CONFLICT, f"This material request is already {request.status.value}")
        if project_id and project_id != request.project_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The material request belongs to a different project")
        project_id = request.project_id
        if not items:
            items = [RfqItemInput(material_id=i.material_id, quantity=i.quantity) for i in request.items]
    if not items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "An RFQ needs at least one item")
    if project_id:
        get_project(db, company_id, project_id)

    material_ids = [i.material_id for i in items]
    if len(set(material_ids)) != len(material_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Each material can appear only once in an RFQ")
    for material_id in material_ids:
        get_material(db, company_id, material_id)
    supplier_ids = list(dict.fromkeys(payload.supplier_ids))
    for supplier_id in supplier_ids:
        get_supplier(db, company_id, supplier_id)

    rfq = Rfq(
        company_id=company_id,
        rfq_number=_next_rfq_number(db, company_id),
        title=payload.title.strip(),
        project_id=project_id,
        material_request_id=payload.material_request_id,
        response_due=payload.response_due,
        notes=payload.notes,
        status=RfqStatus.OPEN,
        created_by_id=user_id,
    )
    db.add(rfq)
    db.flush()
    for item in items:
        db.add(RfqItem(company_id=company_id, rfq_id=rfq.id, material_id=item.material_id, quantity=item.quantity))
    for supplier_id in supplier_ids:
        db.add(RfqSupplier(company_id=company_id, rfq_id=rfq.id, supplier_id=supplier_id))
    db.commit()
    return get_rfq(db, company_id, rfq.id)


def record_quotation(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, rfq_id: uuid.UUID, payload: QuotationCreate
) -> Rfq:
    """Enter (or replace) one supplier's quote. It must price every item on the RFQ,
    so quotations are always comparable like for like."""
    rfq = get_rfq(db, company_id, rfq_id)
    _require_open(rfq)
    get_supplier(db, company_id, payload.supplier_id)

    rfq_item_ids = {i.id for i in rfq.items}
    quoted_ids = [i.rfq_item_id for i in payload.items]
    if len(set(quoted_ids)) != len(quoted_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An item is priced more than once")
    if set(quoted_ids) != rfq_item_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A quotation must give a rate for every item on the RFQ")

    # A supplier who quotes without having been invited is added to the invite list.
    if payload.supplier_id not in {s.supplier_id for s in rfq.invited}:
        db.add(RfqSupplier(company_id=company_id, rfq_id=rfq.id, supplier_id=payload.supplier_id))

    quotation = next((q for q in rfq.quotations if q.supplier_id == payload.supplier_id), None)
    if quotation is None:
        quotation = Quotation(company_id=company_id, rfq_id=rfq.id, supplier_id=payload.supplier_id, created_by_id=user_id)
        db.add(quotation)
    quotation.delivery_days = payload.delivery_days
    quotation.valid_until = payload.valid_until
    quotation.notes = payload.notes
    quotation.items.clear()
    db.flush()
    for item in payload.items:
        quotation.items.append(
            QuotationItem(company_id=company_id, quotation_id=quotation.id, rfq_item_id=item.rfq_item_id, rate=item.rate)
        )
    db.commit()
    db.expire_all()
    return get_rfq(db, company_id, rfq_id)


def award(db: Session, company_id: uuid.UUID, user_id: uuid.UUID, rfq_id: uuid.UUID, quotation_id: uuid.UUID) -> Rfq:
    rfq = get_rfq(db, company_id, rfq_id)
    _require_open(rfq)
    quotation = next((q for q in rfq.quotations if q.id == quotation_id), None)
    if quotation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quotation not found on this RFQ")
    if quotation.valid_until and quotation.valid_until < date.today():
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"This quotation expired on {quotation.valid_until}; ask the supplier to re-quote"
        )

    quantities = {i.id: i.quantity for i in rfq.items}
    materials = {i.id: i.material_id for i in rfq.items}
    supplier = get_supplier(db, company_id, quotation.supplier_id)
    total = _quote_total(quotation, quantities).quantize(Decimal("0.01"))

    # Marked awarded in the same transaction that drafts the PO (create_purchase_order
    # commits), so an RFQ can't be awarded twice or end up awarded with no PO.
    rfq.status = RfqStatus.AWARDED
    rfq.awarded_quotation_id = quotation.id
    audit_service.record(
        db, company_id, user_id, "rfq.awarded", "rfq", rfq.id,
        f"{rfq.rfq_number} awarded to {supplier.name} for {total:,.2f}",
        {"quotation_id": str(quotation.id), "supplier_id": str(supplier.id), "total": str(total)},
    )
    try:
        po = procurement_service.create_purchase_order(
            db,
            company_id,
            user_id,
            PurchaseOrderCreate(
                supplier_id=quotation.supplier_id,
                project_id=rfq.project_id,
                material_request_id=rfq.material_request_id,
                items=[
                    PurchaseOrderItemInput(
                        material_id=materials[qi.rfq_item_id], quantity=quantities[qi.rfq_item_id], rate=qi.rate
                    )
                    for qi in quotation.items
                ],
            ),
        )
    except Exception:
        db.rollback()
        raise
    rfq.purchase_order_id = po.id
    db.commit()
    return get_rfq(db, company_id, rfq_id)


def cancel(db: Session, company_id: uuid.UUID, user_id: uuid.UUID, rfq_id: uuid.UUID) -> Rfq:
    rfq = get_rfq(db, company_id, rfq_id)
    _require_open(rfq)
    rfq.status = RfqStatus.CANCELLED
    audit_service.record(db, company_id, user_id, "rfq.cancelled", "rfq", rfq.id, f"{rfq.rfq_number} cancelled")
    db.commit()
    return get_rfq(db, company_id, rfq_id)


def to_read(db: Session, company_id: uuid.UUID, rfq: Rfq) -> RfqRead:
    """Lay the quotations out for comparison: totals, the cheapest rate per item and
    the cheapest quotation overall. Plain arithmetic over the entered rates."""
    material_ids = {i.material_id for i in rfq.items}
    materials = {
        m.id: m for m in db.query(Material).filter(Material.company_id == company_id, Material.id.in_(material_ids))
    } if material_ids else {}
    supplier_ids = {s.supplier_id for s in rfq.invited} | {q.supplier_id for q in rfq.quotations}
    suppliers = dict(
        db.query(Supplier.id, Supplier.name).filter(Supplier.company_id == company_id, Supplier.id.in_(supplier_ids))
    ) if supplier_ids else {}
    project_name = None
    if rfq.project_id:
        project_name = db.query(Project.name).filter(Project.id == rfq.project_id).scalar()
    po_number = None
    if rfq.purchase_order_id:
        po_number = db.query(PurchaseOrder.po_number).filter(PurchaseOrder.id == rfq.purchase_order_id).scalar()

    quantities = {i.id: i.quantity for i in rfq.items}
    lowest_rate: dict[uuid.UUID, Decimal] = {}
    for q in rfq.quotations:
        for qi in q.items:
            if qi.rfq_item_id not in lowest_rate or qi.rate < lowest_rate[qi.rfq_item_id]:
                lowest_rate[qi.rfq_item_id] = qi.rate
    totals = {q.id: _quote_total(q, quantities) for q in rfq.quotations}
    lowest_total = min(totals.values()) if totals else None
    today = date.today()

    quotations = sorted(
        (
            QuotationRead(
                id=q.id,
                supplier_id=q.supplier_id,
                supplier_name=suppliers.get(q.supplier_id, "Unknown supplier"),
                delivery_days=q.delivery_days,
                valid_until=q.valid_until,
                expired=bool(q.valid_until and q.valid_until < today),
                notes=q.notes,
                total=totals[q.id],
                is_lowest_total=totals[q.id] == lowest_total,
                created_at=q.created_at,
                items=[
                    QuotationItemRead(
                        rfq_item_id=qi.rfq_item_id,
                        rate=qi.rate,
                        amount=qi.rate * quantities[qi.rfq_item_id],
                        is_lowest=qi.rate == lowest_rate[qi.rfq_item_id],
                    )
                    for qi in q.items
                ],
            )
            for q in rfq.quotations
        ),
        key=lambda q: (q.total, q.supplier_name),
    )
    quoted = {q.supplier_id for q in rfq.quotations}
    return RfqRead(
        id=rfq.id,
        rfq_number=rfq.rfq_number,
        title=rfq.title,
        project_id=rfq.project_id,
        project_name=project_name,
        material_request_id=rfq.material_request_id,
        response_due=rfq.response_due,
        notes=rfq.notes,
        status=rfq.status,
        created_at=rfq.created_at,
        items=[
            RfqItemRead(
                id=i.id,
                material_id=i.material_id,
                material_name=materials[i.material_id].name if i.material_id in materials else "Unknown",
                unit=materials[i.material_id].unit if i.material_id in materials else "",
                quantity=i.quantity,
            )
            for i in rfq.items
        ],
        invited=sorted(
            (
                InvitedSupplier(
                    supplier_id=s.supplier_id,
                    supplier_name=suppliers.get(s.supplier_id, "Unknown supplier"),
                    has_quoted=s.supplier_id in quoted,
                )
                for s in rfq.invited
            ),
            key=lambda s: s.supplier_name,
        ),
        quotations=quotations,
        awarded_quotation_id=rfq.awarded_quotation_id,
        purchase_order_id=rfq.purchase_order_id,
        po_number=po_number,
    )


def list_rfqs(db: Session, company_id: uuid.UUID) -> list[RfqSummary]:
    rfqs = (
        db.query(Rfq)
        .options(selectinload(Rfq.items), selectinload(Rfq.invited), selectinload(Rfq.quotations).selectinload(Quotation.items))
        .filter(Rfq.company_id == company_id)
        .order_by(Rfq.created_at.desc())
        .all()
    )
    project_ids = {r.project_id for r in rfqs if r.project_id}
    names = dict(
        db.query(Project.id, Project.name).filter(Project.company_id == company_id, Project.id.in_(project_ids))
    ) if project_ids else {}
    out = []
    for r in rfqs:
        quantities = {i.id: i.quantity for i in r.items}
        totals = [_quote_total(q, quantities) for q in r.quotations]
        out.append(
            RfqSummary(
                id=r.id,
                rfq_number=r.rfq_number,
                title=r.title,
                project_name=names.get(r.project_id),
                status=r.status,
                response_due=r.response_due,
                item_count=len(r.items),
                invited_count=len(r.invited),
                quotation_count=len(r.quotations),
                lowest_total=min(totals) if totals else None,
                created_at=r.created_at,
            )
        )
    return out
