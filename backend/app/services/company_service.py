import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.updates import apply_changes
from app.models.company import Company
from app.schemas.company import CompanyUpdate
from app.services import audit_service


def get_company(db: Session, company_id: uuid.UUID) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


def update_company(db: Session, company_id: uuid.UUID, actor_id: uuid.UUID, payload: CompanyUpdate) -> Company:
    company = get_company(db, company_id)
    changes = payload.model_dump(exclude_unset=True)
    before = {field: getattr(company, field) for field in changes}
    apply_changes(company, changes)
    changed = {f: {"from": before[f], "to": v} for f, v in changes.items() if before[f] != v}
    if changed:
        audit_service.record(
            db, company_id, actor_id, "company.settings_updated", "company", company.id,
            "Company settings changed: " + ", ".join(sorted(changed)), changed,
        )
    db.commit()
    db.refresh(company)
    return company
