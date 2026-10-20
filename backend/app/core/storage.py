"""File storage behind a tiny interface.

Phase 10 (Task 3): two backends now exist, chosen by `STORAGE_BACKEND`
("local", the default, or "s3"). Callers never see which one is active --
they deal only in opaque storage keys and the response-building helper
below, never a filesystem path directly (that's new: Phase <10 callers used
to call `resolve_path()` and build a `FileResponse` themselves, which only
works for local disk; `get_file_response()` replaces that call site so the
same code path works for either backend). No S3 bucket has ever actually
been provisioned or credentialed for this project -- the S3 backend is
implemented and tested against `moto`'s in-memory S3 double
(tests/test_storage_s3_http.py), not a real AWS account."""

import io
import uuid
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse, Response

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


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def response(self, key: str, filename: str, media_type: str, inline: bool) -> Response: ...

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...


class LocalStorageBackend(StorageBackend):
    """Unchanged behavior from before Phase 10 -- a plain local directory,
    path-traversal-checked, used directly in development and (today) in
    every real deployment of this project, since no S3 credentials have
    ever been provisioned."""

    def _root(self) -> Path:
        root = Path(get_settings().storage_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _resolved(self, key: str) -> Path:
        root = self._root()
        path = (root / key).resolve()
        if root not in path.parents:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage key")
        return path

    def save(self, key: str, content: bytes) -> None:
        path = self._resolved(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def delete(self, key: str) -> None:
        self._resolved(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._resolved(key).is_file()

    def response(self, key: str, filename: str, media_type: str, inline: bool) -> Response:
        path = self._resolved(key)
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found in storage")
        disposition = "inline" if inline else "attachment"
        return FileResponse(path, media_type=media_type, filename=filename, content_disposition_type=disposition, headers={"X-Content-Type-Options": "nosniff"})

    def read_bytes(self, key: str) -> bytes:
        path = self._resolved(key)
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found in storage")
        return path.read_bytes()


class S3StorageBackend(StorageBackend):
    """Private by construction: objects are uploaded with no ACL (bucket
    policy / Block Public Access is expected to deny public reads --
    nothing here ever requests public-read), and the only way to fetch one
    is a short-lived presigned URL minted per request, after this app's own
    authorization checks have already run (the same checks that gate
    `get_file_response` for local storage). A payment proof or verification
    document is therefore never reachable by a bare, guessable S3 URL."""

    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._expiry = settings.s3_presigned_url_expiry_seconds
        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region or None,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key_id.get_secret_value() or None,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value() or None,
        )

    def save(self, key: str, content: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def response(self, key: str, filename: str, media_type: str, inline: bool) -> Response:
        if not self.exists(key):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found in storage")
        disposition = "inline" if inline else "attachment"
        url = self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket, "Key": key,
                "ResponseContentType": media_type,
                "ResponseContentDisposition": f'{disposition}; filename="{filename}"',
            },
            ExpiresIn=self._expiry,
        )
        # A redirect, not a proxy: the backend's own bandwidth/CPU is never
        # spent streaming file bytes, and the signed URL expires quickly.
        return RedirectResponse(url, status_code=302)

    def read_bytes(self, key: str) -> bytes:
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found in storage") from exc
        return obj["Body"].read()


_local_singleton: LocalStorageBackend | None = None


def _backend() -> StorageBackend:
    """Re-reads settings.storage_backend on every call (cheap) rather than
    caching the choice for the process lifetime, so tests that monkeypatch
    it mid-run behave as expected -- the S3 client itself is still only
    constructed when actually selected."""
    global _local_singleton
    if get_settings().storage_backend == "s3":
        return S3StorageBackend()
    if _local_singleton is None:
        _local_singleton = LocalStorageBackend()
    return _local_singleton


async def save_upload(
    file: UploadFile, company_id: uuid.UUID, folder: str, allowed_types: dict[str, str]
) -> tuple[str, int]:
    """Validate and store an upload. Returns (storage_key, size_bytes).

    The content type is checked against an allow-list, the bytes must match that
    type, and the size is capped.
    The stored filename is a fresh UUID plus an extension derived from the
    validated content type, so the client's filename can't influence the path
    or (for the S3 backend) the object key.
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
    _backend().save(key, content)
    return key, len(content)


def delete_file(storage_key: str) -> None:
    """Best-effort removal. A missing file is fine (already gone)."""
    _backend().delete(storage_key)


def get_file_response(storage_key: str, filename: str, media_type: str, inline: bool = False) -> Response:
    """The one place a storage key becomes an HTTP response -- a real local
    file stream for the local backend, a redirect to a short-lived signed
    URL for S3. Every caller must already have done its own authorization
    check (ownership/tenant/role) before calling this; this function only
    knows about the storage key, never who's allowed to see it."""
    return _backend().response(storage_key, filename, media_type, inline)


def read_bytes(storage_key: str) -> bytes:
    """For internal use (text extraction/indexing), never for serving a
    response directly to a client -- that's get_file_response's job."""
    return _backend().read_bytes(storage_key)
