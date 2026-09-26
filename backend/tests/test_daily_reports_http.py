import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def project_id(client, auth_a) -> str:
    res = client.post("/api/v1/projects", headers=auth_a, json={"name": "Tower", "code": "TWR", "budget": "1000"})
    return res.json()["id"]


@pytest.fixture
def report_id(client, auth_a, project_id) -> str:
    res = client.post(
        f"/api/v1/projects/{project_id}/daily-reports",
        headers=auth_a,
        json={"report_date": "2026-09-20", "weather": "Sunny", "workers_count": 12, "work_completed": "Block B foundation"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def upload(client, headers, report_id, content=PNG, content_type="image/png", name="site.png"):
    return client.post(
        f"/api/v1/daily-reports/{report_id}/photos",
        headers=headers,
        files={"file": (name, io.BytesIO(content), content_type)},
    )


def test_create_and_list_reports(client, auth_a, project_id, report_id):
    res = client.get(f"/api/v1/projects/{project_id}/daily-reports", headers=auth_a)
    assert res.status_code == 200
    assert [r["work_completed"] for r in res.json()] == ["Block B foundation"]


def test_one_report_per_project_per_day(client, auth_a, project_id, report_id):
    res = client.post(
        f"/api/v1/projects/{project_id}/daily-reports", headers=auth_a, json={"report_date": "2026-09-20"}
    )
    assert res.status_code == 409


def test_photo_upload_and_download_roundtrip(client, auth_a, report_id):
    res = upload(client, auth_a, report_id)
    assert res.status_code == 201, res.text
    photo = res.json()
    assert photo["size_bytes"] == len(PNG)

    dl = client.get(f"/api/v1/daily-reports/{report_id}/photos/{photo['id']}", headers=auth_a)
    assert dl.status_code == 200
    assert dl.content == PNG
    assert dl.headers["content-type"] == "image/png"

    report = client.get(f"/api/v1/daily-reports/{report_id}", headers=auth_a).json()
    assert len(report["photos"]) == 1


def test_rejects_disallowed_file_type(client, auth_a, report_id):
    res = upload(client, auth_a, report_id, content=b"MZ\x90\x00", content_type="application/x-msdownload", name="a.exe")
    assert res.status_code == 415


def test_rejects_oversized_file(client, auth_a, report_id):
    res = upload(client, auth_a, report_id, content=b"\x00" * (1024 * 1024 + 1))
    assert res.status_code == 413


def test_rejects_empty_file(client, auth_a, report_id):
    assert upload(client, auth_a, report_id, content=b"").status_code == 400


def test_malicious_filename_cannot_influence_storage_path(client, auth_a, report_id, tmp_path):
    res = upload(client, auth_a, report_id, name="../../../../etc/passwd.png")
    assert res.status_code == 201
    # the original name is kept only as display metadata; the file itself is a uuid
    photo = res.json()
    dl = client.get(f"/api/v1/daily-reports/{report_id}/photos/{photo['id']}", headers=auth_a)
    assert dl.status_code == 200 and dl.content == PNG


def test_other_company_cannot_see_or_download_photos(client, auth_a, auth_b, report_id):
    photo = upload(client, auth_a, report_id).json()
    assert client.get(f"/api/v1/daily-reports/{report_id}", headers=auth_b).status_code == 404
    assert client.get(f"/api/v1/daily-reports/{report_id}/photos/{photo['id']}", headers=auth_b).status_code == 404
    assert upload(client, auth_b, report_id).status_code == 404


def test_creating_a_report_requires_authentication(client, project_id):
    res = client.post(f"/api/v1/projects/{project_id}/daily-reports", json={"report_date": "2026-09-21"})
    assert res.status_code == 401
