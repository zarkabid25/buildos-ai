import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.updates import apply_changes
from app.models.material import Material, MaterialCategory
from app.schemas.material import MaterialCategoryCreate, MaterialCreate, MaterialUpdate


def list_categories(db: Session, company_id: uuid.UUID) -> list[MaterialCategory]:
    return (
        db.query(MaterialCategory)
        .filter(MaterialCategory.company_id == company_id)
        .order_by(MaterialCategory.name.asc())
        .all()
    )


def create_category(
    db: Session, company_id: uuid.UUID, payload: MaterialCategoryCreate
) -> MaterialCategory:
    category = MaterialCategory(company_id=company_id, **payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_materials(db: Session, company_id: uuid.UUID) -> list[Material]:
    return (
        db.query(Material)
        .filter(Material.company_id == company_id)
        .order_by(Material.name.asc())
        .all()
    )


def get_material(db: Session, company_id: uuid.UUID, material_id: uuid.UUID) -> Material:
    material = (
        db.query(Material)
        .filter(Material.company_id == company_id, Material.id == material_id)
        .first()
    )
    if not material:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    return material


def _check_category(db: Session, company_id: uuid.UUID, category_id: uuid.UUID) -> None:
    exists = (
        db.query(MaterialCategory.id)
        .filter(MaterialCategory.company_id == company_id, MaterialCategory.id == category_id)
        .first()
    )
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material category not found")


def create_material(db: Session, company_id: uuid.UUID, payload: MaterialCreate) -> Material:
    if payload.category_id:
        _check_category(db, company_id, payload.category_id)
    exists = (
        db.query(Material)
        .filter(Material.company_id == company_id, Material.sku == payload.sku)
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Material SKU already in use")

    material = Material(company_id=company_id, **payload.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def update_material(
    db: Session, company_id: uuid.UUID, material_id: uuid.UUID, payload: MaterialUpdate
) -> Material:
    material = get_material(db, company_id, material_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("category_id"):
        _check_category(db, company_id, changes["category_id"])
    apply_changes(material, changes)
    db.commit()
    db.refresh(material)
    return material
