import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentCategory


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: DocumentCategory | None = None
    description: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    category: DocumentCategory
    description: str | None
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by_id: uuid.UUID
    created_at: datetime
    text_status: str | None = None
    text_chars: int | None = None
    page_count: int | None = None



class DocumentSearchHit(BaseModel):
    """A passage inside a document that matches a search (BUILD-080)."""

    document_id: uuid.UUID
    title: str
    category: DocumentCategory
    project_id: uuid.UUID | None
    project_name: str | None
    page: int | None
    snippet: str
    terms: list[str]
