import io
import os
from pathlib import Path

PDF = b"%PDF-1.4\n" + b"1 0 obj\n<<>>\nendobj\n" * 8


def minimal_docx() -> bytes:
    """Uploads are checked against their real content now, so this must be a genuine .docx package."""
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


def upload(client, headers, *, content=PDF, content_type="application/pdf", name="contract.pdf",
           title="Main Contract", category="contract", project_id=None, description=None):
    data = {"title": title, "category": category}
    if project_id:
        data["project_id"] = project_id
    if description:
        data["description"] = description
    return client.post(
        "/api/v1/documents", headers=headers, data=data, files={"file": (name, io.BytesIO(content), content_type)}
    )


def stored_files() -> list[Path]:
    root = Path(os.environ["STORAGE_DIR"])
    return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


def make_project(client, headers, code="DOC1") -> str:
    return client.post("/api/v1/projects", headers=headers, json={"name": "Tower", "code": code, "budget": "1"}).json()["id"]


def test_upload_and_download_roundtrip(client, auth_a):
    res = upload(client, auth_a)
    assert res.status_code == 201, res.text
    doc = res.json()
    assert doc["category"] == "contract" and doc["size_bytes"] == len(PDF)
    assert "storage_key" not in doc  # internal path never leaks through the API

    dl = client.get(f"/api/v1/documents/{doc['id']}/download", headers=auth_a)
    assert dl.status_code == 200 and dl.content == PDF
    assert dl.headers["x-content-type-options"] == "nosniff"
    assert dl.headers["content-disposition"].startswith("attachment")


def test_inline_preview_only_for_safe_types(client, auth_a):
    pdf = upload(client, auth_a).json()
    r = client.get(f"/api/v1/documents/{pdf['id']}/download?inline=true", headers=auth_a)
    assert r.headers["content-disposition"].startswith("inline")

    docx_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    docx = upload(client, auth_a, content=minimal_docx(), content_type=docx_type, name="spec.docx").json()
    r = client.get(f"/api/v1/documents/{docx['id']}/download?inline=true", headers=auth_a)
    assert r.headers["content-disposition"].startswith("attachment")


def test_html_and_executables_are_rejected(client, auth_a):
    assert upload(client, auth_a, content=b"<script>alert(1)</script>", content_type="text/html", name="x.html").status_code == 415
    assert upload(client, auth_a, content=b"MZ\x90\x00", content_type="application/x-msdownload", name="x.exe").status_code == 415
    assert stored_files() == []


def test_oversize_and_empty_and_missing_title(client, auth_a):
    assert upload(client, auth_a, content=b"\x00" * (1024 * 1024 + 1)).status_code == 413
    assert upload(client, auth_a, content=b"").status_code == 400
    res = client.post("/api/v1/documents", headers=auth_a, data={"category": "other"},
                      files={"file": ("a.pdf", io.BytesIO(PDF), "application/pdf")})
    assert res.status_code == 422


def test_list_filters_by_category_and_project(client, auth_a):
    pid = make_project(client, auth_a)
    upload(client, auth_a, title="Contract A", category="contract", project_id=pid)
    upload(client, auth_a, title="Drawing B", category="drawing", project_id=pid)
    upload(client, auth_a, title="Company policy", category="other")

    titles = lambda url: sorted(d["title"] for d in client.get(url, headers=auth_a).json())
    assert titles("/api/v1/documents") == ["Company policy", "Contract A", "Drawing B"]
    assert titles(f"/api/v1/documents?project_id={pid}") == ["Contract A", "Drawing B"]
    assert titles("/api/v1/documents?category=drawing") == ["Drawing B"]


def test_metadata_update_does_not_touch_the_file(client, auth_a):
    doc = upload(client, auth_a).json()
    res = client.patch(f"/api/v1/documents/{doc['id']}", headers=auth_a,
                       json={"title": "Signed Contract", "category": "invoice", "description": "v2"})
    assert res.status_code == 200
    assert (res.json()["title"], res.json()["category"], res.json()["description"]) == ("Signed Contract", "invoice", "v2")
    assert client.get(f"/api/v1/documents/{doc['id']}/download", headers=auth_a).content == PDF


def test_cannot_attach_to_another_companys_project(client, auth_a, auth_b):
    foreign_project = make_project(client, auth_b, code="FOREIGN")
    assert upload(client, auth_a, project_id=foreign_project).status_code == 404
    assert stored_files() == []  # rejected before anything was written


def test_other_company_cannot_read_change_or_delete(client, auth_a, auth_b):
    doc = upload(client, auth_a).json()
    for method, url, kwargs in [
        ("get", f"/api/v1/documents/{doc['id']}", {}),
        ("get", f"/api/v1/documents/{doc['id']}/download", {}),
        ("patch", f"/api/v1/documents/{doc['id']}", {"json": {"title": "pwned"}}),
        ("delete", f"/api/v1/documents/{doc['id']}", {}),
    ]:
        assert getattr(client, method)(url, headers=auth_b, **kwargs).status_code == 404, (method, url)
    assert client.get("/api/v1/documents", headers=auth_b).json() == []
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth_a).json()["title"] == "Main Contract"


def test_viewer_can_read_but_not_upload_or_delete(client, auth_a, viewer_a):
    doc = upload(client, auth_a).json()
    assert client.get("/api/v1/documents", headers=viewer_a).status_code == 200
    assert client.get(f"/api/v1/documents/{doc['id']}/download", headers=viewer_a).status_code == 200
    assert upload(client, viewer_a).status_code == 403
    assert client.patch(f"/api/v1/documents/{doc['id']}", headers=viewer_a, json={"title": "x"}).status_code == 403
    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=viewer_a).status_code == 403
    assert len(stored_files()) == 1


def test_delete_removes_record_and_file(client, auth_a):
    doc = upload(client, auth_a).json()
    assert len(stored_files()) == 1
    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=auth_a).status_code == 204
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth_a).status_code == 404
    assert stored_files() == []


def test_content_must_match_the_declared_type(client, auth_a):
    """BUILD-124: the Content-Type header is the client's claim; the bytes are checked."""
    exe = b"MZ\x90\x00" + b"\x00" * 64
    html = b"<html><script>alert(1)</script></html>"
    docx_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    rejected = [
        (exe, "application/pdf", "invoice.pdf"),
        (html, "application/pdf", "invoice.pdf"),
        (exe, "image/png", "photo.png"),
        (b"PK\x03\x04" + b"\x00" * 30, docx_type, "fake.docx"),  # zip header, but not a Word package
        (b"a,b\x00\x01\x02", "text/csv", "data.csv"),  # binary posing as text
    ]
    for content, content_type, name in rejected:
        res = upload(client, auth_a, content=content, content_type=content_type, name=name)
        assert res.status_code == 415, (name, res.status_code)
    assert stored_files() == []
    # Real files of those types still go through, including a non-UTF-8 (cp1252) CSV.
    assert upload(client, auth_a, content="name,amount\nCafé,10\n".encode("cp1252"),
                  content_type="text/csv", name="costs.csv").status_code == 201
    assert upload(client, auth_a, content=minimal_docx(), content_type=docx_type, name="spec.docx").status_code == 201
