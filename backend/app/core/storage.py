"""File storage behind a tiny interface.

Only a local-disk backend exists today. The spec calls for S3-compatible storage,
but no object store is available in the dev environment, so this stands in for it.
Swapping in S3/MinIO later means replacing save_file/open_path here; callers only
deal in opaque storage keys, never filesystem paths or user-supplied filenames.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    **IMAGE_TYPES,
}


def _root() -> Path:
    root = Path(get_settings().storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload(
    file: UploadFile, company_id: uuid.UUID, folder: str, allowed_types: dict[str, str]
) -> tuple[str, int]:
    """Validate and store an upload. Returns (storage_key, size_bytes).

    The content type is checked against an allow-list and the size is capped.
    The stored filename is a fresh UUID plus an extension derived from the
    validated content type, so the client's filename can't influence the path.
    """
    settings = get_settings()

    if file.content_type not in allowed_types:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File type not allowed")

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            413,
            f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit",
        )
    if len(content) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")

    key = f"{company_id}/{folder}/{uuid.uuid4()}{allowed_types[file.content_type]}"
    path = _root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return key, len(content)


def resolve_path(storage_key: str) -> Path:
    root = _root()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage key")
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found in storage")
    return path
