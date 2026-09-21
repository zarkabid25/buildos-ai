import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.supplier import (
    SupplierContactCreate,
    SupplierContactRead,
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
)
from app.services import supplier_service

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER, UserRole.STOREKEEPER)


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SupplierRead]:
    return supplier_service.list_suppliers(db, current_user.company_id)


@router.post("", response_model=SupplierRead, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> SupplierRead:
    return supplier_service.create_supplier(db, current_user.company_id, payload)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupplierRead:
    return supplier_service.get_supplier(db, current_user.company_id, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> SupplierRead:
    return supplier_service.update_supplier(db, current_user.company_id, supplier_id, payload)


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN)),
    db: Session = Depends(get_db),
) -> None:
    supplier_service.delete_supplier(db, current_user.company_id, supplier_id)


@router.get("/{supplier_id}/contacts", response_model=list[SupplierContactRead])
def list_contacts(
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SupplierContactRead]:
    return supplier_service.list_contacts(db, current_user.company_id, supplier_id)


@router.post("/{supplier_id}/contacts", response_model=SupplierContactRead, status_code=201)
def add_contact(
    supplier_id: uuid.UUID,
    payload: SupplierContactCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> SupplierContactRead:
    return supplier_service.add_contact(db, current_user.company_id, supplier_id, payload)


@router.delete("/{supplier_id}/contacts/{contact_id}", status_code=204)
def remove_contact(
    supplier_id: uuid.UUID,
    contact_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    supplier_service.remove_contact(db, current_user.company_id, supplier_id, contact_id)
