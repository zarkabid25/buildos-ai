"""Phase 10 (Task 3): the S3-compatible storage backend, tested against
`moto`'s in-memory S3 double -- not a real AWS account (none has ever been
provisioned for this project). Confirms the backend itself behaves
correctly (save/read/delete/404, presigned-not-public access) and that the
real upload/download HTTP endpoints work unchanged when STORAGE_BACKEND is
switched to "s3" -- the whole point of the adapter being swappable without
touching caller business logic."""

import io

import pytest
from moto import mock_aws

from app.core.config import get_settings
from app.core.storage import S3StorageBackend


@pytest.fixture
def s3_settings(monkeypatch):
    """Switches the live app settings to the S3 backend, pointed at a
    region moto will mock, for the duration of one test."""
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "buildos-test-bucket")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_access_key_id", type(settings.s3_access_key_id)("test-key"))
    monkeypatch.setattr(settings, "s3_secret_access_key", type(settings.s3_secret_access_key)("test-secret"))
    return settings


@mock_aws
def test_s3_backend_save_read_delete_roundtrip(s3_settings):
    import boto3

    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_settings.s3_bucket)
    backend = S3StorageBackend()

    backend.save("co1/docs/file.pdf", b"%PDF-1.4 fake content")
    assert backend.exists("co1/docs/file.pdf")
    assert backend.read_bytes("co1/docs/file.pdf") == b"%PDF-1.4 fake content"

    backend.delete("co1/docs/file.pdf")
    assert not backend.exists("co1/docs/file.pdf")


@mock_aws
def test_s3_backend_response_is_a_presigned_redirect_not_a_bare_public_url(s3_settings):
    import boto3

    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_settings.s3_bucket)
    backend = S3StorageBackend()
    backend.save("co1/proofs/proof.pdf", b"%PDF-1.4 fake")

    response = backend.response("co1/proofs/proof.pdf", "proof.pdf", "application/pdf", inline=False)
    assert response.status_code == 302
    url = response.headers["location"]
    # A real presigned URL carries a signature query param -- confirms this
    # is NOT a bare, permanently-public object URL anyone could guess.
    assert "Signature" in url or "X-Amz-Signature" in url


@mock_aws
def test_s3_backend_response_404s_for_a_missing_key(s3_settings):
    import boto3

    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_settings.s3_bucket)
    backend = S3StorageBackend()
    with pytest.raises(Exception) as exc_info:
        backend.response("co1/does/not/exist.pdf", "x.pdf", "application/pdf", inline=False)
    assert "404" in str(exc_info.value) or getattr(exc_info.value, "status_code", None) == 404


@mock_aws
def test_document_upload_and_download_work_unchanged_against_the_s3_backend(client, auth_a, s3_settings):
    """The real, unmodified /documents upload+download endpoints, exercised
    end-to-end with STORAGE_BACKEND=s3 -- confirms get_file_response's
    swap is actually transparent to the business logic that calls it."""
    import boto3

    from tests.test_marketplace_integration_http import make

    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_settings.s3_bucket)
    project = make(client, auth_a, "/projects", {"name": "S3 Proj", "code": "S3P1", "budget": "1"})

    res = client.post(
        "/api/v1/documents",
        data={"title": "S3 doc", "category": "other", "project_id": project["id"]},
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4\nreal enough for the magic-byte check"), "application/pdf")},
        headers=auth_a,
    )
    assert res.status_code == 201, res.text
    document_id = res.json()["id"]

    download = client.get(f"/api/v1/documents/{document_id}/download", headers=auth_a, follow_redirects=False)
    assert download.status_code == 302, download.text
    assert "amazonaws.com" in download.headers["location"] or "Signature" in download.headers["location"]
