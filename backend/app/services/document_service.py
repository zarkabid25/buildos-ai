import re
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.updates import apply_changes
from app.core.storage import DOCUMENT_TYPES, delete_file, resolve_path, save_upload
from app.models.document import Document, DocumentChunk
from app.models.project import Project
from app.models.enums import DocumentCategory
from app.schemas.document import DocumentSearchHit, DocumentUpdate
from app.services import document_text
from app.services.project_service import get_project
from app.services import audit_service


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
    db.flush()
    index_document(db, document)
    db.commit()
    db.refresh(document)
    return document


def update_document(
    db: Session, company_id: uuid.UUID, document_id: uuid.UUID, payload: DocumentUpdate
) -> Document:
    document = get_document(db, company_id, document_id)
    apply_changes(document, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(document)
    return document


def get_document_file(db: Session, company_id: uuid.UUID, document_id: uuid.UUID):
    document = get_document(db, company_id, document_id)
    return document, resolve_path(document.storage_key)


def delete_document(db: Session, company_id: uuid.UUID, actor_id: uuid.UUID, document_id: uuid.UUID) -> None:
    document = get_document(db, company_id, document_id)
    key = document.storage_key
    audit_service.record(
        db, company_id, actor_id, "document.deleted", "document", document.id,
        f'Document deleted: "{document.title}" ({document.original_filename})',
    )
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.delete(document)
    db.commit()
    delete_file(key)


def index_document(db: Session, document: Document) -> None:
    """(Re)build a document's searchable passages from its stored file. Never raises
    for a bad file: the document is kept and marked so the UI can say why."""
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    try:
        content = resolve_path(document.storage_key).read_bytes()
    except HTTPException:
        document.text_status, document.text_chars, document.page_count = "failed", None, None
        return
    result = document_text.extract(document.content_type, content)
    passages = document_text.chunk(result.pages) if result.status == "indexed" else []
    for index, (page, text) in enumerate(passages):
        db.add(DocumentChunk(company_id=document.company_id, document_id=document.id, chunk_index=index, page=page, text=text))
    document.text_status = result.status
    document.text_chars = sum(len(text) for _, text in result.pages)
    document.page_count = result.page_count


def reindex_document(db: Session, company_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = get_document(db, company_id, document_id)
    index_document(db, document)
    db.commit()
    db.refresh(document)
    return document


def _snippet(text: str, terms: list[str], width: int = 240) -> str:
    """The part of a passage around the first match, so results show why they matched."""
    lower = text.lower()
    first = min((i for i in (lower.find(t) for t in terms) if i >= 0), default=0)
    start = max(0, first - width // 3)
    end = min(len(text), start + width)
    return ("…" if start > 0 else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def search_documents(
    db: Session, company_id: uuid.UUID, q: str, project_id: uuid.UUID | None = None, limit: int = 20
) -> list[DocumentSearchHit]:
    """Keyword search inside document text (BUILD-080, lexical version): passages
    containing every word of the query, best-matching first. No embeddings needed."""
    terms = [t for t in re.findall(r"\w+", q.lower()) if len(t) >= 2][:8]
    if not terms:
        return []
    query = (
        db.query(DocumentChunk, Document, Project.name)
        .join(Document, (Document.id == DocumentChunk.document_id) & (Document.company_id == company_id))
        .outerjoin(Project, (Project.id == Document.project_id) & (Project.company_id == company_id))
        .filter(DocumentChunk.company_id == company_id)
    )
    for term in terms:
        # "_" is a LIKE wildcard and \w matches it, so escape it.
        escaped = term.replace("_", "\\_")
        query = query.filter(DocumentChunk.text.ilike(f"%{escaped}%", escape="\\"))
    if project_id:
        query = query.filter(Document.project_id == project_id)
    rows = query.limit(500).all()

    def score(row) -> tuple:
        chunk, document, _ = row
        lower = chunk.text.lower()
        phrase = " ".join(terms)
        # Exact phrase first, then how often the words appear, then a title match.
        return (
            phrase in lower,
            sum(lower.count(t) for t in terms),
            any(t in document.title.lower() for t in terms),
        )

    hits = []
    for chunk, document, project_name in sorted(rows, key=score, reverse=True)[:limit]:
        hits.append(
            DocumentSearchHit(
                document_id=document.id,
                title=document.title,
                category=document.category,
                project_id=document.project_id,
                project_name=project_name,
                page=chunk.page,
                snippet=_snippet(chunk.text, terms),
                terms=terms,
            )
        )
    return hits
