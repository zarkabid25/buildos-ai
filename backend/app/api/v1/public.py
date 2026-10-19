from fastapi import APIRouter, Depends, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.billing import SubscriptionPlanRead
from app.schemas.public_site import (
    DemoRequestCreate,
    DemoRequestRead,
    SupplierApplicationCreate,
    SupplierApplicationDocumentRead,
    SupplierApplicationRead,
)
from app.services import public_site_service, subscription_plan_service

router = APIRouter(prefix="/public", tags=["public"])

TOO_MANY = "Too many attempts. Please wait and try again."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/plans", response_model=list[SubscriptionPlanRead])
def public_plans(db: Session = Depends(get_db)) -> list[SubscriptionPlanRead]:
    """No auth at all -- the marketing pricing page needs real plan data,
    never hardcoded figures (CLAUDE.md rule). Reuses the exact same service
    function the authenticated tenant /billing/plans route already calls."""
    return subscription_plan_service.list_plans(db, include_inactive=False)


@router.post("/demo-requests", response_model=DemoRequestRead, status_code=201)
def request_demo(payload: DemoRequestCreate, request: Request, db: Session = Depends(get_db)) -> DemoRequestRead:
    settings = get_settings()
    key = f"public-form:{_client_ip(request)}"
    limiter.check(key, settings.public_form_max_per_ip, settings.public_form_window_seconds, TOO_MANY)
    limiter.hit(key)
    return public_site_service.create_demo_request(db, payload)


@router.post("/supplier-applications", response_model=SupplierApplicationRead, status_code=201)
def submit_supplier_application(payload: SupplierApplicationCreate, request: Request, db: Session = Depends(get_db)) -> SupplierApplicationRead:
    settings = get_settings()
    key = f"public-form:{_client_ip(request)}"
    limiter.check(key, settings.public_form_max_per_ip, settings.public_form_window_seconds, TOO_MANY)
    limiter.hit(key)
    return public_site_service.create_supplier_application(db, payload)


@router.post("/supplier-applications/{application_id}/documents", response_model=SupplierApplicationDocumentRead, status_code=201)
async def upload_supplier_application_document(
    application_id: str, file: UploadFile, request: Request, title: str = Form(""), db: Session = Depends(get_db)
) -> SupplierApplicationDocumentRead:
    import uuid as _uuid

    settings = get_settings()
    key = f"public-form:{_client_ip(request)}"
    limiter.check(key, settings.public_form_max_per_ip, settings.public_form_window_seconds, TOO_MANY)
    limiter.hit(key)
    return await public_site_service.upload_application_document(db, _uuid.UUID(application_id), file, title)
