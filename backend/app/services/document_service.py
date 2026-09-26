import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.storage import DOCUMENT_TYPES, delete_file, resolve_path, save_upload
from app.models.document import Document
from app.models.enums import DocumentCategory
from app.schemas.document import DocumentUpdate
from app.services.project_service import get_project


def list_documents(
    db: Session,
    company_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    category: DocumentCategory | None = None,
) -> list[Document]:
    query = db.query(Document).filter(Document.company_id == company_id)
    if project_id:
        query = query.filter(Document.project_id == project_id)
    if category:
        query = query.filter(Document.category == category)
    return query.order_by(Document.created_at.desc()).all()


def get_document(db: Session, company_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = (
        db.query(Document)
        .filter(Document.company_id == company_id, Document.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


async def upload_document(
    db: Session,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    file: UploadFile,
    title: str,
    category: DocumentCategory,
    project_id: uuid.UUID | None,
    description: str | None,
) -> Document:
    if project_id:
        get_project(db, company_id, project_id)  # 404s for another company's project

    key, size = await save_upload(file, company_id, "documents", DOCUMENT_TYPES)
    document = Document(
        company_id=company_id,
        project_id=project_id,
        title=title.strip() or (file.filename or "Untitled"),
        category=category,
        description=description,
        original_filename=(file.filename or "document")[:255],
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        storage_key=key,
        uploaded_by_id=user_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update_document(
    db: Session, company_id: uuid.UUID, document_id: uuid.UUID, payload: DocumentUpdate
) -> Document:
    document = get_document(db, company_id, document_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document


def get_document_file(db: Session, company_id: uuid.UUID, document_id: uuid.UUID):
    document = get_document(db, company_id, document_id)
    return document, resolve_path(document.storage_key)


def delete_document(db: Session, company_id: uuid.UUID, document_id: uuid.UUID) -> None:
    document = get_document(db, company_id, document_id)
    key = document.storage_key
    db.delete(document)
    db.commit()
    delete_file(key)
