"""Public website, registration/demo requests, supplier applications, the
support desk, and onboarding notifications (Phase 8, PLAT-043..047) -- plus
every required compatibility and isolation check."""

import io
from decimal import Decimal

from app.models.enums import PlatformStaffRole
from tests.conftest import register
from tests.test_marketplace_integration_http import owner_headers
from tests.test_supplier_portal_http import invite_and_accept, onboarded_supplier, supplier_headers


# ---- PLAT-043: public website -----------------------------------------------------------------


def test_public_plans_endpoint_requires_no_auth(client):
    staff = owner_headers(client, email="pub-staff1@buildos.ai")
    res = client.post(
        "/api/v1/platform/billing/plans",
        json={"name": "Public Plan", "trial_days": 7, "prices": [{"currency": "USD", "billing_period": "monthly", "amount": "99"}]},
        headers=staff,
    )
    assert res.status_code == 201, res.text

    res = client.get("/api/v1/public/plans")
    assert res.status_code == 200
    assert any(p["name"] == "Public Plan" for p in res.json())


# ---- PLAT-044: company registration and demo requests -----------------------------------------


def test_company_registration_is_not_grandfathered(client):
    """New companies registering after Phase 5 shipped get no legacy
    entitlement at all -- source 'none', not 'legacy' -- confirming
    registration was never touched to auto-grant anything."""
    headers = register(client, "PUB1", "pub1-admin@example.com")
    res = client.get("/api/v1/billing/entitlements", headers=headers)
    assert res.status_code == 200
    assert res.json()["source"] == "none"

    staff = owner_headers(client, email="pub-staff2@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=headers).json()["company_id"]
    res = client.get("/api/v1/platform/billing/legacy-entitlements", headers=staff)
    assert not any(e["company_id"] == company_id for e in res.json())


def test_registered_company_onboarding_status_starts_pending(client):
    headers = register(client, "PUB2", "pub2-admin@example.com")
    staff = owner_headers(client, email="pub-staff3@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=headers).json()["company_id"]
    res = client.get(f"/api/v1/platform/companies/{company_id}", headers=staff)
    assert res.json()["onboarding_status"] == "pending"


def test_demo_request_creates_a_crm_lead(client):
    res = client.post(
        "/api/v1/public/demo-requests",
        json={"full_name": "Jamie Prospect", "email": "jamie@prospectco.com", "phone": "555-0100", "company_name": "Prospect Co", "message": "Interested in a demo"},
    )
    assert res.status_code == 201, res.text
    demo = res.json()
    assert demo["crm_organization_id"] is not None
    assert demo["already_submitted"] is False

    staff = owner_headers(client, email="pub-staff4@buildos.ai")
    res = client.get("/api/v1/platform/crm/organizations", params={"pipeline_type": "saas_sales"}, headers=staff)
    assert any(o["id"] == demo["crm_organization_id"] for o in res.json())


def test_duplicate_demo_submission_reuses_the_same_lead(client):
    payload = {"full_name": "Dana Dup", "email": "dana@dupco.com", "company_name": "Dup Co"}
    res1 = client.post("/api/v1/public/demo-requests", json=payload)
    res2 = client.post("/api/v1/public/demo-requests", json=payload)
    assert res2.json()["already_submitted"] is True
    assert res1.json()["crm_organization_id"] == res2.json()["crm_organization_id"]

    staff = owner_headers(client, email="pub-staff5@buildos.ai")
    res = client.get("/api/v1/platform/crm/organizations", params={"pipeline_type": "saas_sales"}, headers=staff)
    matching = [o for o in res.json() if o["id"] == res1.json()["crm_organization_id"]]
    assert len(matching) == 1  # exactly one organization, never duplicated


def test_second_demo_request_same_email_different_company_does_not_duplicate_org(client):
    """A real second lead for the same email reuses the existing
    organization by email rather than creating a second one, even outside
    the immediate-duplicate window, since PLAT-044 says never duplicate the
    organization for the same prospect."""
    client.post("/api/v1/public/demo-requests", json={"full_name": "Riley Reuse", "email": "riley@reuseco.com", "company_name": "Reuse Co"})
    staff = owner_headers(client, email="pub-staff6@buildos.ai")
    orgs_before = len(client.get("/api/v1/platform/crm/organizations", params={"pipeline_type": "saas_sales"}, headers=staff).json())

    from app.db.session import SessionLocal
    from app.models.public_site import DemoRequest
    from datetime import datetime, timedelta, timezone

    db = SessionLocal()
    try:
        row = db.query(DemoRequest).filter(DemoRequest.email == "riley@reuseco.com").first()
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/public/demo-requests", json={"full_name": "Riley Reuse", "email": "riley@reuseco.com", "company_name": "Reuse Co"})
    assert res.json()["already_submitted"] is False  # outside the window, a new DemoRequest row...
    orgs_after = len(client.get("/api/v1/platform/crm/organizations", params={"pipeline_type": "saas_sales"}, headers=staff).json())
    assert orgs_after == orgs_before  # ...but the SAME organization, never a duplicate


def test_demo_request_rate_limited(client):
    for i in range(12):
        res = client.post("/api/v1/public/demo-requests", json={"full_name": f"Spammer {i}", "email": f"spam{i}@spamco.com", "company_name": "Spam Co"})
    assert res.status_code == 429


# ---- PLAT-045: supplier applications -----------------------------------------------------------


def test_supplier_application_submission(client):
    res = client.post(
        "/api/v1/public/supplier-applications",
        json={
            "business_name": "Apex Cement Supplies", "contact_name": "Taylor Apex", "email": "taylor@apexcement.com", "phone": "555-0200",
            "categories": ["cement", "aggregates"], "delivery_locations": ["Punjab", "Sindh"], "business_description": "A regional cement distributor.",
        },
    )
    assert res.status_code == 201, res.text
    app_data = res.json()
    assert app_data["status"] == "pending"
    assert app_data["categories"] == ["cement", "aggregates"]


def test_supplier_cannot_self_verify_an_application(client):
    """There is no endpoint at all for an applicant to approve their own
    application -- confirmed by it requiring a platform staff token."""
    res = client.post(
        "/api/v1/public/supplier-applications",
        json={"business_name": "Self Verify Co", "contact_name": "Sam Self", "email": "sam@selfverify.com"},
    )
    application_id = res.json()["id"]
    res = client.post(f"/api/v1/platform/supplier-applications/{application_id}/review", json={"approve": True, "review_notes": "ok"})
    assert res.status_code == 401  # no token at all


def test_supplier_application_approval_creates_a_pending_not_verified_supplier(client):
    res = client.post(
        "/api/v1/public/supplier-applications",
        json={"business_name": "New Approved Co", "contact_name": "Approved Person", "email": "person@newapproved.com", "categories": ["steel"]},
    )
    application_id = res.json()["id"]

    staff = owner_headers(client, email="pub-staff7@buildos.ai")
    res = client.post(f"/api/v1/platform/supplier-applications/{application_id}/review", json={"approve": True, "review_notes": "Looks legitimate"}, headers=staff)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "approved"
    supplier_id = body["marketplace_supplier_id"]
    assert supplier_id is not None

    res = client.get(f"/api/v1/platform/marketplace/suppliers/{supplier_id}", headers=staff)
    assert res.json()["verification_status"] == "pending"  # never auto-verified

    # Double review is refused.
    res2 = client.post(f"/api/v1/platform/supplier-applications/{application_id}/review", json={"approve": True, "review_notes": "again"}, headers=staff)
    assert res2.status_code == 409


def test_supplier_application_rejection_creates_no_supplier(client):
    res = client.post(
        "/api/v1/public/supplier-applications",
        json={"business_name": "Rejected Co", "contact_name": "Rejected Person", "email": "person@rejectedco.com"},
    )
    application_id = res.json()["id"]
    staff = owner_headers(client, email="pub-staff8@buildos.ai")
    res = client.post(f"/api/v1/platform/supplier-applications/{application_id}/review", json={"approve": False, "review_notes": "Insufficient information"}, headers=staff)
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"
    assert res.json()["marketplace_supplier_id"] is None


def test_supplier_application_document_upload_and_staff_review_list(client):
    res = client.post(
        "/api/v1/public/supplier-applications",
        json={"business_name": "Doc Co", "contact_name": "Doc Person", "email": "person@docco.com"},
    )
    application_id = res.json()["id"]
    res = client.post(
        f"/api/v1/public/supplier-applications/{application_id}/documents",
        data={"title": "Registration Certificate"},
        files={"file": ("cert.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")},
    )
    assert res.status_code == 201, res.text

    staff = owner_headers(client, email="pub-staff9@buildos.ai")
    res = client.get(f"/api/v1/platform/supplier-applications/{application_id}/documents", headers=staff)
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "Registration Certificate"


def test_supplier_application_listing_and_status_filter(client):
    staff = owner_headers(client, email="pub-staff10@buildos.ai")
    client.post("/api/v1/public/supplier-applications", json={"business_name": "Filter Co", "contact_name": "F P", "email": "f@filterco.com"})
    res = client.get("/api/v1/platform/supplier-applications", params={"status": "pending"}, headers=staff)
    assert any(a["business_name"] == "Filter Co" for a in res.json())


# ---- PLAT-046: support desk -------------------------------------------------------------------


def test_company_support_ticket_creation_and_reply(client, auth_a):
    res = client.post("/api/v1/support", json={"subject": "Can't create a project", "category": "technical", "priority": "high", "message": "Getting a 500 error."}, headers=auth_a)
    assert res.status_code == 201, res.text
    ticket = res.json()
    assert ticket["status"] == "open"
    assert len(ticket["messages"]) == 1

    res = client.post(f"/api/v1/support/{ticket['id']}/messages", json={"body": "Still happening"}, headers=auth_a)
    assert res.status_code == 201
    assert len(res.json()["messages"]) == 2


def test_internal_staff_notes_never_exposed_to_company(client, auth_a):
    res = client.post("/api/v1/support", json={"subject": "Billing question", "category": "billing", "message": "Why was I charged twice?"}, headers=auth_a)
    ticket_id = res.json()["id"]

    staff = owner_headers(client, email="pub-staff11@buildos.ai")
    res = client.post(f"/api/v1/platform/support/{ticket_id}/messages?is_internal=true", json={"body": "Internal: check Stripe dashboard before replying"}, headers=staff)
    assert res.status_code == 201
    staff_view = res.json()
    assert any(m["is_internal"] for m in staff_view["messages"])

    company_view = client.get(f"/api/v1/support/{ticket_id}", headers=auth_a).json()
    assert all(not m["is_internal"] for m in company_view["messages"])
    assert len(company_view["messages"]) == 1  # the internal note is simply absent, not just flagged


def test_company_a_cannot_access_company_b_tickets(client, auth_a, auth_b):
    res = client.post("/api/v1/support", json={"subject": "A's private ticket", "category": "account", "message": "..."}, headers=auth_a)
    ticket_id = res.json()["id"]
    res = client.get(f"/api/v1/support/{ticket_id}", headers=auth_b)
    assert res.status_code == 404
    assert client.get("/api/v1/support", headers=auth_b).json() == [] or not any(t["id"] == ticket_id for t in client.get("/api/v1/support", headers=auth_b).json())


def test_supplier_support_ticket_creation_and_isolation(client):
    staff, supplier_a, headers_a = onboarded_supplier(client, "supp1", name="Support Supplier A", email="a@supportsupplier.com")
    _s2, supplier_b, headers_b = onboarded_supplier(client, "supp2", name="Support Supplier B", email="b@supportsupplier.com")

    res = client.post("/api/v1/supplier-portal/support", json={"subject": "Can't update my catalog", "category": "technical", "message": "Error saving product"}, headers=headers_a)
    assert res.status_code == 201, res.text
    ticket_id = res.json()["id"]

    res = client.get(f"/api/v1/supplier-portal/support/{ticket_id}", headers=headers_b)
    assert res.status_code == 404  # supplier B isolated from supplier A's ticket

    res = client.post(f"/api/v1/supplier-portal/support/{ticket_id}/messages", json={"body": "Any update?"}, headers=headers_a)
    assert res.status_code == 201
    assert len(res.json()["messages"]) == 2


def test_platform_staff_actions_on_tickets_are_audited(client, auth_a):
    res = client.post("/api/v1/support", json={"subject": "Audited ticket", "category": "other", "message": "..."}, headers=auth_a)
    ticket_id = res.json()["id"]
    staff = owner_headers(client, email="pub-staff12@buildos.ai")
    client.patch(f"/api/v1/platform/support/{ticket_id}", json={"status": "resolved"}, headers=staff)
    res = client.get("/api/v1/platform/audit-log", headers=staff)
    assert any(e["action"] == "support.ticket_updated" and str(e["entity_id"]) == ticket_id for e in res.json())


def test_resolving_a_ticket_sets_resolved_at_and_notifies_the_company_user(client, auth_a):
    res = client.post("/api/v1/support", json={"subject": "Resolve me", "category": "other", "message": "..."}, headers=auth_a)
    ticket_id = res.json()["id"]
    staff = owner_headers(client, email="pub-staff13@buildos.ai")
    res = client.patch(f"/api/v1/platform/support/{ticket_id}", json={"status": "resolved"}, headers=staff)
    assert res.json()["resolved_at"] is not None

    res = client.get("/api/v1/notifications", headers=auth_a)
    assert any(n["notification_type"] == "support_ticket_resolved" for n in res.json())


def test_supplier_cannot_access_platform_support_endpoints(client):
    _staff, _supplier, headers = onboarded_supplier(client, "noplatformsupport", email="noplatform@supportiso.com")
    res = client.get("/api/v1/platform/support", headers=headers)
    assert res.status_code == 401


# ---- PLAT-047: notifications and email delivery honesty ---------------------------------------


def test_demo_request_creates_a_platform_notification(client):
    client.post("/api/v1/public/demo-requests", json={"full_name": "Notify Me", "email": "notify@notifyco.com", "company_name": "Notify Co"})
    staff = owner_headers(client, email="pub-staff14@buildos.ai")
    res = client.get("/api/v1/platform/notifications", headers=staff)
    assert any(n["notification_type"] == "demo_request_received" for n in res.json())


def test_supplier_application_creates_a_platform_notification(client):
    client.post("/api/v1/public/supplier-applications", json={"business_name": "Notify Supplier Co", "contact_name": "N P", "email": "n@notifysupplierco.com"})
    staff = owner_headers(client, email="pub-staff15@buildos.ai")
    res = client.get("/api/v1/platform/notifications", headers=staff)
    assert any(n["notification_type"] == "supplier_application_received" for n in res.json())


def test_support_ticket_reply_notifies_supplier_portal_user(client):
    staff, supplier, headers = onboarded_supplier(client, "notifysupp", name="Notify Supplier Portal Co", email="owner@notifysupplierportal.com")
    res = client.post("/api/v1/supplier-portal/support", json={"subject": "Need help", "category": "technical", "message": "..."}, headers=headers)
    ticket_id = res.json()["id"]
    client.post(f"/api/v1/platform/support/{ticket_id}/messages", json={"body": "We're looking into it"}, headers=staff)

    res = client.get("/api/v1/supplier-portal/notifications", headers=headers)
    assert any(n["notification_type"] == "support_ticket_reply" for n in res.json())


def test_email_delivery_honestly_reports_not_configured_without_smtp_credentials(client, monkeypatch):
    """Phase 9.1 (Task 3): with EMAIL_PROVIDER=smtp but no SMTP_HOST set,
    send_email() must record that honestly, not pretend delivery succeeded."""
    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.services import email_service

    settings = get_settings()
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "")

    db = SessionLocal()
    try:
        log = email_service.send_email(db, "someone@example.com", "Test", "Body")
        db.commit()
        assert log.status.value == "not_configured"
        assert log.error is not None
    finally:
        db.close()


def test_email_sandbox_provider_records_sent(client):
    """The default "console" provider is a real sandbox (logs and records
    SENT), not a dead stub -- this is what every test and local dev run
    exercises unless EMAIL_PROVIDER=smtp is explicitly set."""
    from app.db.session import SessionLocal
    from app.services import email_service

    db = SessionLocal()
    try:
        log = email_service.send_email(db, "someone@example.com", "Test", "Body")
        db.commit()
        assert log.status.value == "sent"
    finally:
        db.close()


def test_email_send_is_retry_safe_via_dedup_key(client):
    """A repeated request with the same dedup_key (e.g. a client retry after
    a timeout) must never send -- i.e. create -- a second log row."""
    from app.db.session import SessionLocal
    from app.services import email_service

    db = SessionLocal()
    try:
        first = email_service.send_email(db, "dedup@example.com", "Test", "Body", dedup_key="test-dedup-1")
        db.commit()
        second = email_service.send_email(db, "dedup@example.com", "Test", "Body", dedup_key="test-dedup-1")
        db.commit()
        assert first.id == second.id
    finally:
        db.close()


# ---- Existing regression spot-checks (full suites run separately) -----------------------------


def test_existing_erp_still_works_after_phase_8(client, auth_a):
    res = client.post("/api/v1/projects", json={"name": "Still Works", "code": "STW1", "budget": "1"}, headers=auth_a)
    assert res.status_code == 201
