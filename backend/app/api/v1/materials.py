import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.material import (
    MaterialCategoryCreate,
    MaterialCategoryRead,
    MaterialCreate,
    MaterialRead,
    MaterialUpdate,
)
from app.services import material_service

router = APIRouter(tags=["materials"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.STOREKEEPER, UserRole.PROJECT_MANAGER)


@router.get("/material-categories", response_model=list[MaterialCategoryRead])
def list_categories(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialCategoryRead]:
    return material_service.list_categories(db, current_user.company_id)


@router.post("/material-categories", response_model=MaterialCategoryRead, status_code=201)
def create_category(
    payload: MaterialCategoryCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> MaterialCategoryRead:
    return material_service.create_category(db, current_user.company_id, payload)


@router.get("/materials", response_model=list[MaterialRead])
def list_materials(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialRead]:
    return material_service.list_materials(db, current_user.company_id)


@router.post("/materials", response_model=MaterialRead, status_code=201)
def create_material(
    payload: MaterialCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> MaterialRead:
    return material_service.create_material(db, current_user.company_id, payload)


@router.patch("/materials/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: uuid.UUID,
    payload: MaterialUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> MaterialRead:
    return material_service.update_material(db, current_user.company_id, material_id, payload)
