import uuid

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.storage import IMAGE_TYPES
from app.db.session import get_db
from app.models.enums import DocumentCategory, UserRole
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentUpdate
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])

CAN_WRITE = (
    UserRole.SUPER_ADMIN,
    UserRole.COMPANY_ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
    UserRole.STOREKEEPER,
    UserRole.ACCOUNTANT,
)
CAN_DELETE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER)

# Only these render safely in a browser tab. Word/Excel files can't be previewed
# inline anyway, so they always download.
INLINE_PREVIEW_TYPES = {"application/pdf", "text/plain", "text/csv", *IMAGE_TYPES}


@router.get("", response_model=list[DocumentRead])
def list_documents(
    project_id: uuid.UUID | None = None,
    category: DocumentCategory | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    return document_service.list_documents(db, current_user.company_id, project_id, category)


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(
    file: UploadFile,
    title: str = Form(min_length=1, max_length=255),
    category: DocumentCategory = Form(DocumentCategory.OTHER),
    project_id: uuid.UUID | None = Form(None),
    description: str | None = Form(None),
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> DocumentRead:
    return await document_service.upload_document(
        db, current_user.company_id, current_user.id, file, title, category, project_id, description
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRead:
    return document_service.get_document(db, current_user.company_id, document_id)


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> DocumentRead:
    return document_service.update_document(db, current_user.company_id, document_id, payload)


@router.get("/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    inline: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    document, path = document_service.get_document_file(db, current_user.company_id, document_id)
    disposition = "inline" if inline and document.content_type in INLINE_PREVIEW_TYPES else "attachment"
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.original_filename,
        content_disposition_type=disposition,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_DELETE)),
    db: Session = Depends(get_db),
) -> None:
    document_service.delete_document(db, current_user.company_id, document_id)
