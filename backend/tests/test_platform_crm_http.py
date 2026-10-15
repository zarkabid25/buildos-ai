"""CRM organizations, contacts, activities, follow-ups and conversion (PLAT-011..015)."""

from app.models.enums import PlatformStaffRole
from tests.test_platform_http import platform_login


def owner_headers(client, email="crm-owner@buildos.ai"):
    return platform_login(client, email=email, role=PlatformStaffRole.OWNER)


def make_org(client, headers, name="Acme Builders", pipeline_type="saas_sales"):
    res = client.post(
        "/api/v1/platform/crm/organizations",
        json={"name": name, "pipeline_type": pipeline_type, "source": "website"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---- CRM records stay distinct from ERP companies until conversion --------------------


def test_crm_organizations_are_not_erp_companies(client):
    headers = owner_headers(client)
    org = make_org(client, headers)
    assert org["converted_company_id"] is None
    # A fresh CRM lead must never collide with /platform/companies.
    res = client.get("/api/v1/platform/companies", headers=headers)
    codes = {c["code"] for c in res.json()["companies"]}
    assert org["name"] not in [c["name"] for c in res.json()["companies"]]
    assert codes is not None  # sanity: endpoint still works untouched


# ---- Lead creation, assignment, pipelines ---------------------------------------------


def test_create_and_list_organizations_by_pipeline(client):
    headers = owner_headers(client)
    make_org(client, headers, name="SaaS Prospect", pipeline_type="saas_sales")
    make_org(client, headers, name="Cement Supplier Co", pipeline_type="supplier_acquisition")

    res = client.get("/api/v1/platform/crm/organizations?pipeline_type=supplier_acquisition", headers=headers)
    names = [o["name"] for o in res.json()]
    assert "Cement Supplier Co" in names
    assert "SaaS Prospect" not in names


def test_lead_assignment_to_staff(client):
    headers = owner_headers(client)
    me = client.get("/api/v1/platform/auth/me", headers=headers).json()
    org = make_org(client, headers)

    res = client.patch(
        f"/api/v1/platform/crm/organizations/{org['id']}", json={"owner_staff_id": me["id"]}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["owner_staff_id"] == me["id"]
    assert res.json()["owner_staff_name"] == "Platform Admin"


def test_support_role_cannot_create_or_edit_leads_but_can_view(client):
    owner = owner_headers(client)
    org = make_org(client, owner)
    support = platform_login(client, email="crm-support@buildos.ai", role=PlatformStaffRole.SUPPORT)

    res = client.post(
        "/api/v1/platform/crm/organizations",
        json={"name": "Blocked Co", "pipeline_type": "saas_sales"},
        headers=support,
    )
    assert res.status_code == 403

    res = client.patch(f"/api/v1/platform/crm/organizations/{org['id']}", json={"stage": "won"}, headers=support)
    assert res.status_code == 403

    res = client.get("/api/v1/platform/crm/organizations", headers=support)
    assert res.status_code == 200


# ---- Pipeline stage changes -------------------------------------------------------------


def test_stage_change_is_audit_logged(client):
    headers = owner_headers(client)
    org = make_org(client, headers)
    res = client.patch(f"/api/v1/platform/crm/organizations/{org['id']}", json={"stage": "qualified"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["stage"] == "qualified"

    res = client.get("/api/v1/platform/audit-log", headers=headers)
    actions = [e["action"] for e in res.json()]
    assert "crm.stage_changed" in actions


# ---- Contacts, activities, follow-ups -----------------------------------------------------


def test_contacts_and_activities(client):
    headers = owner_headers(client)
    org = make_org(client, headers)

    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/contacts",
        json={"name": "Jane Doe", "title": "Procurement Lead", "email": "jane@acme.example.com", "is_primary": True},
        headers=headers,
    )
    assert res.status_code == 201, res.text

    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/activities",
        json={"type": "call", "summary": "Intro call, interested in RFQ module"},
        headers=headers,
    )
    assert res.status_code == 201, res.text

    res = client.get(f"/api/v1/platform/crm/organizations/{org['id']}", headers=headers)
    detail = res.json()
    assert len(detail["contacts"]) == 1
    assert len(detail["activities"]) == 1
    assert detail["activities"][0]["created_by_name"] == "Platform Admin"


def test_follow_up_dashboard_shows_only_open_dated_tasks(client):
    headers = owner_headers(client)
    org = make_org(client, headers)

    client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/activities",
        json={"type": "note", "summary": "No due date, shouldn't show up"},
        headers=headers,
    )
    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/activities",
        json={"type": "task", "summary": "Follow up next week", "due_at": "2026-12-01T09:00:00Z"},
        headers=headers,
    )
    task_id = res.json()["id"]

    res = client.get("/api/v1/platform/crm/follow-ups", headers=headers)
    summaries = [a["summary"] for a in res.json()]
    assert "Follow up next week" in summaries
    assert "No due date, shouldn't show up" not in summaries

    res = client.post(f"/api/v1/platform/crm/activities/{task_id}/complete", headers=headers)
    assert res.status_code == 200
    assert res.json()["completed_at"] is not None

    res = client.get("/api/v1/platform/crm/follow-ups", headers=headers)
    assert "Follow up next week" not in [a["summary"] for a in res.json()]


# ---- Conversion: idempotent, distinct-until-converted, authorized linking ------------------


def test_convert_creates_a_new_company(client):
    headers = owner_headers(client)
    org = make_org(client, headers, name="New Co Prospect")

    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/convert",
        json={"create_company_name": "New Co", "create_company_code": "NEWCO"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["already_converted"] is False
    assert body["organization"]["converted_company_id"] == body["company_id"]
    assert body["organization"]["stage"] == "won"

    # The company really exists and is pending (not approved -- CRM conversion
    # doesn't bypass the platform-staff approval workflow).
    res = client.get(f"/api/v1/platform/companies/{body['company_id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["onboarding_status"] == "pending"


def test_conversion_is_idempotent(client):
    headers = owner_headers(client)
    org = make_org(client, headers, name="Idempotent Co")

    res1 = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/convert",
        json={"create_company_name": "Idempotent Co", "create_company_code": "IDEMCO"},
        headers=headers,
    )
    company_id = res1.json()["company_id"]

    res2 = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/convert",
        json={"create_company_name": "Idempotent Co", "create_company_code": "IDEMCO"},
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["already_converted"] is True
    assert res2.json()["company_id"] == company_id

    # Only one company was actually created.
    res = client.get("/api/v1/platform/companies?search=Idempotent", headers=headers)
    assert res.json()["total"] == 1


def test_convert_links_an_existing_company(client, auth_a):
    headers = owner_headers(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    org = make_org(client, headers, name="Already Registered Co")

    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/convert",
        json={"link_existing_company_id": company_id},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["company_id"] == company_id


def test_cannot_link_a_company_already_linked_to_another_lead(client, auth_a):
    headers = owner_headers(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    org1 = make_org(client, headers, name="First Claimant")
    org2 = make_org(client, headers, name="Second Claimant")

    client.post(
        f"/api/v1/platform/crm/organizations/{org1['id']}/convert",
        json={"link_existing_company_id": company_id},
        headers=headers,
    )
    res = client.post(
        f"/api/v1/platform/crm/organizations/{org2['id']}/convert",
        json={"link_existing_company_id": company_id},
        headers=headers,
    )
    assert res.status_code == 409


def test_convert_requires_exactly_one_option(client):
    headers = owner_headers(client)
    org = make_org(client, headers)
    res = client.post(f"/api/v1/platform/crm/organizations/{org['id']}/convert", json={}, headers=headers)
    assert res.status_code == 400

    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/convert",
        json={"link_existing_company_id": org["id"], "create_company_name": "XX", "create_company_code": "XXCODE"},
        headers=headers,
    )
    assert res.status_code == 400


def test_support_role_cannot_convert(client):
    owner = owner_headers(client)
    org = make_org(client, owner, name="Support Cannot Convert")
    support = platform_login(client, email="crm-support2@buildos.ai", role=PlatformStaffRole.SUPPORT)

    res = client.post(
        f"/api/v1/platform/crm/organizations/{org['id']}/convert",
        json={"create_company_name": "X", "create_company_code": "XCODE"},
        headers=support,
    )
    assert res.status_code == 403
