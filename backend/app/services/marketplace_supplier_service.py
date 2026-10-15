import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.storage import DOCUMENT_TYPES, save_upload
from app.models.company import Company
from app.models.enums import MarketplaceSupplierStatus
from app.models.marketplace_supplier import (
    MarketplaceCompanySupplierLink,
    MarketplaceMaterialMapping,
    MarketplaceProduct,
    MarketplaceSupplier,
    MarketplaceSupplierCategory,
    MarketplaceSupplierContact,
    MarketplaceSupplierCoverageArea,
    MarketplaceSupplierDocument,
)
from app.models.material import Material
from app.models.platform_admin import PlatformAdmin
from app.schemas.marketplace_supplier import (
    MarketplaceCompanyLinkCreate,
    MarketplaceCompanyLinkRead,
    MarketplaceMaterialMappingCreate,
    MarketplaceMaterialMappingRead,
    MarketplaceProductCreate,
    MarketplaceProductRead,
    MarketplaceProductUpdate,
    MarketplaceSupplierContactCreate,
    MarketplaceSupplierContactRead,
    MarketplaceSupplierCreate,
    MarketplaceSupplierCreated,
    MarketplaceSupplierDetail,
    MarketplaceSupplierDocumentRead,
    MarketplaceSupplierList,
    MarketplaceSupplierRead,
    MarketplaceSupplierUpdate,
    MarketplaceVerificationUpdate,
)
from app.services import platform_audit_service

# PENDING is the only starting state; a supplier can move back and forth between
# verified/suspended, and a rejection can be reconsidered by sending it back to
# pending. Nothing can jump straight from pending to suspended (it must be
# verified first) or stay a no-op transition to itself.
_ALLOWED_TRANSITIONS = {
    MarketplaceSupplierStatus.PENDING: {MarketplaceSupplierStatus.VERIFIED, MarketplaceSupplierStatus.REJECTED},
    MarketplaceSupplierStatus.VERIFIED: {MarketplaceSupplierStatus.SUSPENDED, MarketplaceSupplierStatus.REJECTED},
    MarketplaceSupplierStatus.SUSPENDED: {MarketplaceSupplierStatus.VERIFIED},
    MarketplaceSupplierStatus.REJECTED: {MarketplaceSupplierStatus.PENDING},
}


def _names(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    return dict(db.query(PlatformAdmin.id, PlatformAdmin.full_name).filter(PlatformAdmin.id.in_(ids)).all())


def _read(supplier: MarketplaceSupplier, onboarded_by_name: str | None) -> MarketplaceSupplierRead:
    return MarketplaceSupplierRead(
        id=supplier.id,
        name=supplier.name,
        legal_name=supplier.legal_name,
        email=supplier.email,
        phone=supplier.phone,
        website=supplier.website,
        address=supplier.address,
        notes=supplier.notes,
        verification_status=supplier.verification_status,
        onboarded_by_id=supplier.onboarded_by_id,
        onboarded_by_name=onboarded_by_name,
        categories=sorted({c.category for c in supplier.categories}),
        coverage_areas=sorted({a.area for a in supplier.coverage_areas}),
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
    )


def _find_possible_duplicates(db: Session, name: str, exclude_id: uuid.UUID | None = None) -> list[MarketplaceSupplier]:
    # Deliberately simple and deterministic (case-insensitive exact match), not
    # fuzzy matching that could silently miss or over-flag -- this only ever
    # produces a review hint, and never merges or blocks creation.
    query = db.query(MarketplaceSupplier).filter(func.lower(MarketplaceSupplier.name) == name.strip().lower())
    if exclude_id:
        query = query.filter(MarketplaceSupplier.id != exclude_id)
    return query.all()


def create_supplier(db: Session, actor: PlatformAdmin, payload: MarketplaceSupplierCreate) -> MarketplaceSupplierCreated:
    duplicates = _find_possible_duplicates(db, payload.name)

    supplier = MarketplaceSupplier(
        name=payload.name.strip(),
        legal_name=payload.legal_name,
        email=payload.email,
        phone=payload.phone,
        website=payload.website,
        address=payload.address,
        notes=payload.notes,
        onboarded_by_id=actor.id,
    )
    db.add(supplier)
    db.flush()
    for cat in dict.fromkeys(c.strip() for c in payload.categories if c.strip()):
        db.add(MarketplaceSupplierCategory(supplier_id=supplier.id, category=cat))
    for area in dict.fromkeys(a.strip() for a in payload.coverage_areas if a.strip()):
        db.add(MarketplaceSupplierCoverageArea(supplier_id=supplier.id, area=area))

    platform_audit_service.record(
        db, actor.id, "marketplace_supplier.onboarded", "marketplace_supplier", supplier.id,
        f"{supplier.name} added to the supplier registry"
        + (f" ({len(duplicates)} possible duplicate(s) found)" if duplicates else ""),
    )
    db.commit()
    db.refresh(supplier)

    names = _names(db, [supplier.onboarded_by_id])
    dup_names = _names(db, [d.onboarded_by_id for d in duplicates])
    return MarketplaceSupplierCreated(
        supplier=_read(supplier, names.get(supplier.onboarded_by_id)),
        possible_duplicates=[_read(d, dup_names.get(d.onboarded_by_id)) for d in duplicates],
    )


def list_suppliers(
    db: Session,
    search: str | None = None,
    category: str | None = None,
    area: str | None = None,
    verification_status: MarketplaceSupplierStatus | None = None,
) -> MarketplaceSupplierList:
    query = db.query(MarketplaceSupplier).options(
        selectinload(MarketplaceSupplier.categories), selectinload(MarketplaceSupplier.coverage_areas)
    )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(MarketplaceSupplier.name.ilike(pattern))
    if verification_status:
        query = query.filter(MarketplaceSupplier.verification_status == verification_status)
    if category:
        query = query.join(MarketplaceSupplierCategory).filter(
            func.lower(MarketplaceSupplierCategory.category) == category.strip().lower()
        )
    if area:
        query = query.join(MarketplaceSupplierCoverageArea).filter(
            func.lower(MarketplaceSupplierCoverageArea.area) == area.strip().lower()
        )

    suppliers = query.order_by(MarketplaceSupplier.created_at.desc()).all()
    names = _names(db, [s.onboarded_by_id for s in suppliers])
    items = [_read(s, names.get(s.onboarded_by_id)) for s in suppliers]
    return MarketplaceSupplierList(total=len(items), suppliers=items)


def _get(db: Session, supplier_id: uuid.UUID) -> MarketplaceSupplier:
    supplier = (
        db.query(MarketplaceSupplier)
        .options(
            selectinload(MarketplaceSupplier.categories),
            selectinload(MarketplaceSupplier.coverage_areas),
            selectinload(MarketplaceSupplier.contacts),
            selectinload(MarketplaceSupplier.documents),
            selectinload(MarketplaceSupplier.products),
        )
        .filter(MarketplaceSupplier.id == supplier_id)
        .first()
    )
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marketplace supplier not found")
    return supplier


def get_supplier(db: Session, supplier_id: uuid.UUID) -> MarketplaceSupplierDetail:
    supplier = _get(db, supplier_id)
    names = _names(db, [supplier.onboarded_by_id])
    base = _read(supplier, names.get(supplier.onboarded_by_id))
    return MarketplaceSupplierDetail(
        **base.model_dump(),
        contacts=[MarketplaceSupplierContactRead.model_validate(c) for c in supplier.contacts],
        documents=[MarketplaceSupplierDocumentRead.model_validate(d) for d in supplier.documents],
        products=[MarketplaceProductRead.model_validate(p) for p in supplier.products],
    )


def update_supplier(
    db: Session, supplier_id: uuid.UUID, payload: MarketplaceSupplierUpdate
) -> MarketplaceSupplierRead:
    supplier = _get(db, supplier_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"categories", "coverage_areas"})
    for field, value in changes.items():
        setattr(supplier, field, value)

    if payload.categories is not None:
        for c in list(supplier.categories):
            db.delete(c)
        db.flush()
        for cat in dict.fromkeys(c.strip() for c in payload.categories if c.strip()):
            db.add(MarketplaceSupplierCategory(supplier_id=supplier.id, category=cat))
    if payload.coverage_areas is not None:
        for a in list(supplier.coverage_areas):
            db.delete(a)
        db.flush()
        for area in dict.fromkeys(a.strip() for a in payload.coverage_areas if a.strip()):
            db.add(MarketplaceSupplierCoverageArea(supplier_id=supplier.id, area=area))

    db.commit()
    db.refresh(supplier)
    names = _names(db, [supplier.onboarded_by_id])
    return _read(supplier, names.get(supplier.onboarded_by_id))


def set_verification_status(
    db: Session, actor: PlatformAdmin, supplier_id: uuid.UUID, payload: MarketplaceVerificationUpdate
) -> MarketplaceSupplierRead:
    supplier = _get(db, supplier_id)
    current = supplier.verification_status
    if payload.status == current:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Supplier is already {current.value}")
    if payload.status not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Can't move a supplier from {current.value} to {payload.status.value}"
        )

    supplier.verification_status = payload.status
    summary = f"{supplier.name}: {current.value} -> {payload.status.value}"
    if payload.reason:
        summary += f" ({payload.reason})"
    platform_audit_service.record(
        db, actor.id, "marketplace_supplier.verification_changed", "marketplace_supplier", supplier.id, summary,
        {"from": current.value, "to": payload.status.value, "reason": payload.reason},
    )
    db.commit()
    db.refresh(supplier)
    names = _names(db, [supplier.onboarded_by_id])
    return _read(supplier, names.get(supplier.onboarded_by_id))


# ---- Contacts -----------------------------------------------------------------------


def add_contact(db: Session, supplier_id: uuid.UUID, payload: MarketplaceSupplierContactCreate) -> MarketplaceSupplierContactRead:
    _get(db, supplier_id)
    contact = MarketplaceSupplierContact(supplier_id=supplier_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return MarketplaceSupplierContactRead.model_validate(contact)


# ---- Documents (verification workflow) -----------------------------------------------


async def upload_document(
    db: Session, actor: PlatformAdmin, supplier_id: uuid.UUID, file: UploadFile, title: str
) -> MarketplaceSupplierDocumentRead:
    supplier = _get(db, supplier_id)
    key, size = await save_upload(file, supplier_id, "marketplace-suppliers", DOCUMENT_TYPES)
    document = MarketplaceSupplierDocument(
        supplier_id=supplier_id,
        title=title.strip() or (file.filename or "Untitled"),
        original_filename=(file.filename or "document")[:255],
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        storage_key=key,
        uploaded_by_id=actor.id,
    )
    db.add(document)
    platform_audit_service.record(
        db, actor.id, "marketplace_supplier.document_uploaded", "marketplace_supplier", supplier.id,
        f"{document.title} uploaded for {supplier.name}",
    )
    db.commit()
    db.refresh(document)
    return MarketplaceSupplierDocumentRead.model_validate(document)


def get_document(db: Session, supplier_id: uuid.UUID, document_id: uuid.UUID) -> MarketplaceSupplierDocument:
    document = (
        db.query(MarketplaceSupplierDocument)
        .filter(MarketplaceSupplierDocument.id == document_id, MarketplaceSupplierDocument.supplier_id == supplier_id)
        .first()
    )
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


# ---- Products / catalog (PLAT-019) ---------------------------------------------------


def add_product(db: Session, supplier_id: uuid.UUID, payload: MarketplaceProductCreate) -> MarketplaceProductRead:
    _get(db, supplier_id)
    product = MarketplaceProduct(supplier_id=supplier_id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return MarketplaceProductRead.model_validate(product)


def update_product(db: Session, product_id: uuid.UUID, payload: MarketplaceProductUpdate) -> MarketplaceProductRead:
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return MarketplaceProductRead.model_validate(product)


# ---- Activity history ------------------------------------------------------------------


def activity_history(db: Session, supplier_id: uuid.UUID):
    _get(db, supplier_id)
    return platform_audit_service.list_entries(db, entity_type="marketplace_supplier", entity_id=supplier_id)


# ---- Future-integration groundwork (PLAT-020) ------------------------------------------


def link_company(
    db: Session, actor: PlatformAdmin, supplier_id: uuid.UUID, payload: MarketplaceCompanyLinkCreate
) -> MarketplaceCompanyLinkRead:
    _get(db, supplier_id)
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    existing = (
        db.query(MarketplaceCompanySupplierLink)
        .filter(
            MarketplaceCompanySupplierLink.company_id == payload.company_id,
            MarketplaceCompanySupplierLink.marketplace_supplier_id == supplier_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This company is already linked to this supplier")

    link = MarketplaceCompanySupplierLink(
        company_id=payload.company_id, marketplace_supplier_id=supplier_id, linked_by_id=actor.id, notes=payload.notes
    )
    db.add(link)
    platform_audit_service.record(
        db, actor.id, "marketplace_supplier.company_linked", "marketplace_supplier", supplier_id,
        f"Linked to {company.name}",
    )
    db.commit()
    db.refresh(link)
    return MarketplaceCompanyLinkRead(**MarketplaceCompanyLinkRead.model_validate(link).model_dump(exclude={"company_name"}), company_name=company.name)


def list_company_links(db: Session, supplier_id: uuid.UUID) -> list[MarketplaceCompanyLinkRead]:
    rows = (
        db.query(MarketplaceCompanySupplierLink, Company.name)
        .join(Company, Company.id == MarketplaceCompanySupplierLink.company_id)
        .filter(MarketplaceCompanySupplierLink.marketplace_supplier_id == supplier_id)
        .all()
    )
    return [
        MarketplaceCompanyLinkRead(**MarketplaceCompanyLinkRead.model_validate(link).model_dump(exclude={"company_name"}), company_name=name)
        for link, name in rows
    ]


def create_material_mapping(
    db: Session, actor: PlatformAdmin, payload: MarketplaceMaterialMappingCreate
) -> MarketplaceMaterialMappingRead:
    if not db.query(Company).filter(Company.id == payload.company_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    if not db.query(Material).filter(Material.id == payload.material_id, Material.company_id == payload.company_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found for that company")
    if not db.query(MarketplaceProduct).filter(MarketplaceProduct.id == payload.marketplace_product_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marketplace product not found")

    existing = (
        db.query(MarketplaceMaterialMapping)
        .filter(
            MarketplaceMaterialMapping.company_id == payload.company_id,
            MarketplaceMaterialMapping.material_id == payload.material_id,
            MarketplaceMaterialMapping.marketplace_product_id == payload.marketplace_product_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This mapping already exists")

    mapping = MarketplaceMaterialMapping(
        company_id=payload.company_id,
        material_id=payload.material_id,
        marketplace_product_id=payload.marketplace_product_id,
        mapped_by_id=actor.id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return MarketplaceMaterialMappingRead.model_validate(mapping)
