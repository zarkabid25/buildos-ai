from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.company import CompanyRead, CompanyUpdate
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyRead)
def get_my_company(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CompanyRead:
    return company_service.get_company(db, current_user.company_id)


@router.patch("/me", response_model=CompanyRead)
def update_my_company(
    payload: CompanyUpdate,
    current_user: User = Depends(require_roles(UserRole.COMPANY_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> CompanyRead:
    return company_service.update_company(db, current_user.company_id, payload)
