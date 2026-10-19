"""Supplier-facing product catalog (PLAT-040) -- reuses the existing
MarketplaceProduct table and marketplace_supplier_service's add_product/
update_product exactly as platform staff already use them; the only new
logic here is enforcing that a supplier can only ever touch its own rows
(ownership was previously implicit in staff being trusted; it's now an
explicit check on every call)."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.marketplace_supplier import MarketplaceProduct
from app.schemas.marketplace_supplier import MarketplaceProductCreate, MarketplaceProductRead, MarketplaceProductUpdate
from app.schemas.supplier_portal import SupplierProductCreate, SupplierProductRead, SupplierProductUpdate
from app.services import marketplace_supplier_service


def list_products(db: Session, marketplace_supplier_id: uuid.UUID, search: str | None = None, active_only: bool = False) -> list[SupplierProductRead]:
    query = db.query(MarketplaceProduct).filter(MarketplaceProduct.supplier_id == marketplace_supplier_id)
    if active_only:
        query = query.filter(MarketplaceProduct.is_active.is_(True))
    if search:
        query = query.filter(MarketplaceProduct.name.ilike(f"%{search}%"))
    rows = query.order_by(MarketplaceProduct.name.asc()).all()
    return [SupplierProductRead.model_validate(p) for p in rows]


def get_product(db: Session, marketplace_supplier_id: uuid.UUID, product_id: uuid.UUID) -> SupplierProductRead:
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.supplier_id == marketplace_supplier_id, MarketplaceProduct.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return SupplierProductRead.model_validate(product)


def create_product(db: Session, marketplace_supplier_id: uuid.UUID, payload: SupplierProductCreate) -> SupplierProductRead:
    created = marketplace_supplier_service.add_product(db, marketplace_supplier_id, MarketplaceProductCreate(**payload.model_dump()))
    return SupplierProductRead(**created.model_dump())


def update_product(db: Session, marketplace_supplier_id: uuid.UUID, product_id: uuid.UUID, payload: SupplierProductUpdate) -> SupplierProductRead:
    # Ownership check first -- marketplace_supplier_service.update_product only
    # looks up by product_id, so this is what actually prevents a supplier
    # from editing another supplier's product.
    get_product(db, marketplace_supplier_id, product_id)
    updated = marketplace_supplier_service.update_product(db, product_id, MarketplaceProductUpdate(**payload.model_dump(exclude_unset=True)))
    return SupplierProductRead(**updated.model_dump())
