import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyUpdate


def get_company(db: Session, company_id: uuid.UUID) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


def update_company(db: Session, company_id: uuid.UUID, payload: CompanyUpdate) -> Company:
    company = get_company(db, company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company
