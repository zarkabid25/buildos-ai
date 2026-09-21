import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.supplier import Supplier, SupplierContact
from app.schemas.supplier import SupplierContactCreate, SupplierCreate, SupplierUpdate


def list_suppliers(db: Session, company_id: uuid.UUID) -> list[Supplier]:
    return (
        db.query(Supplier)
        .filter(Supplier.company_id == company_id)
        .order_by(Supplier.name.asc())
        .all()
    )


def get_supplier(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier:
    supplier = (
        db.query(Supplier)
        .filter(Supplier.company_id == company_id, Supplier.id == supplier_id)
        .first()
    )
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return supplier


def create_supplier(db: Session, company_id: uuid.UUID, payload: SupplierCreate) -> Supplier:
    supplier = Supplier(company_id=company_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierUpdate
) -> Supplier:
    supplier = get_supplier(db, company_id, supplier_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    supplier = get_supplier(db, company_id, supplier_id)
    db.delete(supplier)
    db.commit()


def list_contacts(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> list[SupplierContact]:
    get_supplier(db, company_id, supplier_id)
    return (
        db.query(SupplierContact)
        .filter(SupplierContact.company_id == company_id, SupplierContact.supplier_id == supplier_id)
        .order_by(SupplierContact.name.asc())
        .all()
    )


def add_contact(
    db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierContactCreate
) -> SupplierContact:
    get_supplier(db, company_id, supplier_id)
    contact = SupplierContact(company_id=company_id, supplier_id=supplier_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def remove_contact(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    contact = (
        db.query(SupplierContact)
        .filter(
            SupplierContact.id == contact_id,
            SupplierContact.supplier_id == supplier_id,
            SupplierContact.company_id == company_id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier contact not found")
    db.delete(contact)
    db.commit()
