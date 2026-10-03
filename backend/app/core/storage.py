"""File storage behind a tiny interface.

Only a local-disk backend exists today. The spec calls for S3-compatible storage,
but no object store is available in the dev environment, so this stands in for it.
Swapping in S3/MinIO later means replacing save_file/open_path here; callers only
deal in opaque storage keys, never filesystem paths or user-supplied filenames.
"""

import io
import uuid
import zipfile
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


_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .doc / .xls container


def _zip_has(content: bytes, member: str) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return member in archive.namelist()
    except zipfile.BadZipFile:
        return False


def content_matches_type(content_type: str, content: bytes) -> bool:
    """Check the bytes really are the declared type (BUILD-124). The client chooses
    the Content-Type header, so without this an executable or HTML page could be
    stored as a "PDF" and later served back with that type."""
    if content_type == "application/pdf":
        return content.startswith(b"%PDF-")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if content_type.endswith("wordprocessingml.document"):
        return _zip_has(content, "word/document.xml")
    if content_type.endswith("spreadsheetml.sheet"):
        return _zip_has(content, "xl/workbook.xml")
    if content_type in ("application/msword", "application/vnd.ms-excel"):
        return content.startswith(_OLE2)
    if content_type in ("text/plain", "text/csv"):
        # Any 8-bit text encoding is fine (Excel CSVs are often cp1252); binary isn't.
        return b"\x00" not in content
    return False


def _root() -> Path:
    root = Path(get_settings().storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload(
    file: UploadFile, company_id: uuid.UUID, folder: str, allowed_types: dict[str, str]
) -> tuple[str, int]:
    """Validate and store an upload. Returns (storage_key, size_bytes).

    The content type is checked against an allow-list, the bytes must match that
    type, and the size is capped.
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
    if not content_matches_type(file.content_type, content):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content doesn't match its type")

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


def delete_file(storage_key: str) -> None:
    """Best-effort removal. A missing file is fine (already gone); a key that
    escapes the storage root is not, and resolve_path's check still applies."""
    root = _root()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage key")
    path.unlink(missing_ok=True)
