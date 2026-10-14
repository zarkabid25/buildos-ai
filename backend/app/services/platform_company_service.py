import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.platform_admin import PlatformAdmin
from app.models.user import User
from app.schemas.platform import PlatformCompanyList, PlatformCompanyRead, PlatformDashboard


def list_companies(db: Session, search: str | None = None) -> PlatformCompanyList:
    query = db.query(Company)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter((Company.name.ilike(pattern)) | (Company.code.ilike(pattern)))

    companies = query.order_by(Company.created_at.desc()).all()
    user_counts = dict(
        db.query(User.company_id, func.count(User.id)).group_by(User.company_id).all()
    )
    items = [
        PlatformCompanyRead(
            id=c.id,
            name=c.name,
            code=c.code,
            currency=c.currency,
            email=c.email,
            phone=c.phone,
            is_active=c.is_active,
            suspended_at=c.suspended_at,
            created_at=c.created_at,
            user_count=user_counts.get(c.id, 0),
        )
        for c in companies
    ]
    return PlatformCompanyList(total=len(items), companies=items)


def get_company(db: Session, company_id: uuid.UUID) -> PlatformCompanyRead:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    user_count = db.query(func.count(User.id)).filter(User.company_id == company_id).scalar() or 0
    return PlatformCompanyRead(
        id=company.id,
        name=company.name,
        code=company.code,
        currency=company.currency,
        email=company.email,
        phone=company.phone,
        is_active=company.is_active,
        suspended_at=company.suspended_at,
        created_at=company.created_at,
        user_count=user_count,
    )


def set_company_suspended(db: Session, company_id: uuid.UUID, suspended: bool) -> PlatformCompanyRead:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")

    company.is_active = not suspended
    company.suspended_at = None if not suspended else datetime.now(timezone.utc)
    db.commit()
    db.refresh(company)
    return get_company(db, company_id)


def dashboard(db: Session) -> PlatformDashboard:
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    active_companies = db.query(func.count(Company.id)).filter(Company.is_active.is_(True)).scalar() or 0
    suspended_companies = db.query(func.count(Company.id)).filter(Company.is_active.is_(False)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    recent_companies = (
        db.query(func.count(Company.id)).filter(Company.created_at >= thirty_days_ago).scalar() or 0
    )
    return PlatformDashboard(
        active_companies=active_companies,
        suspended_companies=suspended_companies,
        total_users=total_users,
        companies_created_last_30_days=recent_companies,
    )
