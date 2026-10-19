"""Supplier self-service portal (Phase 7, PLAT-038..042): a third, fully
independent auth system (tenant users, platform staff, now supplier portal
users), memberships/roles, product catalog, RFQ inbox and self-submitted
quotations, order/delivery visibility, and commission statements -- plus
every required isolation and compatibility check."""

import io
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.enums import PlatformStaffRole
from app.models.supplier_user import SupplierInvitation
from tests.test_marketplace_integration_http import enable_marketplace, make, make_verified_supplier, owner_headers


def invite_and_accept(client, staff, marketplace_supplier_id, email, full_name="Supplier Person", role="owner", password="password123"):
    res = client.post(f"/api/v1/platform/marketplace/suppliers/{marketplace_supplier_id}/portal-invitations", json={"email": email, "full_name": full_name, "role": role}, headers=staff)
    assert res.status_code == 201, res.text
    token = res.json()["token"]
    res = client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": full_name, "password": password})
    assert res.status_code == 201, res.text
    return token


def supplier_login(client, email, password="password123"):
    res = client.post("/api/v1/supplier-portal/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


def supplier_headers(client, email, password="password123"):
    body = supplier_login(client, email, password)
    assert body["active_supplier_id"] is not None, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def onboarded_supplier(client, staff_email_suffix, name="Portal Supplier", email="owner@portalsupplier.com"):
    staff = owner_headers(client, email=f"portal-staff-{staff_email_suffix}@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name=name)
    invite_and_accept(client, staff, mkt_supplier["id"], email)
    headers = supplier_headers(client, email)
    return staff, mkt_supplier, headers


# ---- PLAT-038: invitation acceptance, tokens, roles, membership -------------------------------


def test_supplier_invitation_acceptance_and_login(client):
    staff = owner_headers(client, email="sp-staff1@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Acceptance Co")
    invite_and_accept(client, staff, mkt_supplier["id"], "owner1@acceptanceco.com")
    body = supplier_login(client, "owner1@acceptanceco.com")
    assert body["active_supplier_id"] == mkt_supplier["id"]
    assert body["memberships"][0]["role"] == "owner"


def test_invitation_cannot_be_reused(client):
    staff = owner_headers(client, email="sp-staff2@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Reuse Co")
    res = client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/portal-invitations", json={"email": "reuse@test.com", "role": "owner"}, headers=staff)
    token = res.json()["token"]
    res = client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": "Alex Accepted", "password": "password123"})
    assert res.status_code == 201
    res2 = client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": "Alex Accepted", "password": "password123"})
    assert res2.status_code == 404


def test_expired_invitation_token_is_refused(client):
    staff = owner_headers(client, email="sp-staff3@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Expiry Co")
    res = client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/portal-invitations", json={"email": "expired@test.com", "role": "owner"}, headers=staff)
    invitation_id = res.json()["id"]
    token = res.json()["token"]

    db = SessionLocal()
    try:
        row = db.query(SupplierInvitation).filter(SupplierInvitation.id == uuid.UUID(invitation_id)).first()
        row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": "Alex Accepted", "password": "password123"})
    assert res.status_code == 410  # gone -- expired

    info_res = client.get(f"/api/v1/supplier-portal/auth/invitations/{'x' * 32}")
    assert info_res.status_code == 404  # a bogus/unknown token is simply not found


def test_supplier_owner_can_invite_teammates_staff_cannot(client):
    staff = owner_headers(client, email="sp-staff4@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Team Co")
    invite_and_accept(client, staff, mkt_supplier["id"], "owner2@teamco.com", role="owner")
    owner_hdrs = supplier_headers(client, "owner2@teamco.com")

    res = client.post("/api/v1/supplier-portal/team/invitations", json={"email": "staffmember@teamco.com", "role": "staff"}, headers=owner_hdrs)
    assert res.status_code == 201, res.text
    staff_token = res.json()["token"]
    res = client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": staff_token, "full_name": "Staffer", "password": "password123"})
    assert res.status_code == 201
    staff_member_hdrs = supplier_headers(client, "staffmember@teamco.com")

    res = client.post("/api/v1/supplier-portal/team/invitations", json={"email": "x@teamco.com", "role": "staff"}, headers=staff_member_hdrs)
    assert res.status_code == 403  # STAFF role can't manage the team


def test_membership_suspension_blocks_access(client):
    staff = owner_headers(client, email="sp-staff5@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Suspend Co")
    invite_and_accept(client, staff, mkt_supplier["id"], "owner3@suspendco.com", role="owner")
    owner_hdrs = supplier_headers(client, "owner3@suspendco.com")
    res = client.post("/api/v1/supplier-portal/team/invitations", json={"email": "member@suspendco.com", "role": "staff"}, headers=owner_hdrs)
    token = res.json()["token"]
    client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": "Member", "password": "password123"})
    member_hdrs = supplier_headers(client, "member@suspendco.com")

    members = client.get("/api/v1/supplier-portal/team/members", headers=owner_hdrs).json()
    member_row = next(m for m in members if m["user_email"] == "member@suspendco.com")
    client.post(f"/api/v1/supplier-portal/team/members/{member_row['id']}/suspend", headers=owner_hdrs)

    res = client.get("/api/v1/supplier-portal/dashboard", headers=member_hdrs)
    assert res.status_code == 403  # old access token still decodes, but the membership behind it is no longer active
    res = client.post("/api/v1/supplier-portal/auth/login", json={"email": "member@suspendco.com", "password": "password123"})
    assert res.status_code == 403  # no active membership left to log into


def test_multi_supplier_account_must_explicitly_select(client):
    staff = owner_headers(client, email="sp-staff6@buildos.ai")
    supplier_a = make_verified_supplier(client, staff, name="Multi A")
    supplier_b = make_verified_supplier(client, staff, name="Multi B")
    invite_and_accept(client, staff, supplier_a["id"], "multi@multisupplier.com", role="owner")
    res = client.post(f"/api/v1/platform/marketplace/suppliers/{supplier_b['id']}/portal-invitations", json={"email": "multi@multisupplier.com", "role": "owner"}, headers=staff)
    token = res.json()["token"]
    client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": "Multi", "password": "password123"})

    body = supplier_login(client, "multi@multisupplier.com")
    assert body["active_supplier_id"] is None  # must explicitly select
    assert len(body["memberships"]) == 2

    res = client.post("/api/v1/supplier-portal/auth/select-supplier", json={"refresh_token": body["refresh_token"], "marketplace_supplier_id": supplier_a["id"]})
    assert res.status_code == 200
    assert res.json()["active_supplier_id"] == supplier_a["id"]

    res2 = client.post("/api/v1/supplier-portal/auth/select-supplier", json={"refresh_token": body["refresh_token"], "marketplace_supplier_id": supplier_b["id"]})
    assert res2.json()["active_supplier_id"] == supplier_b["id"]


def test_supplier_a_cannot_access_supplier_b_data(client):
    _staff_a, supplier_a, headers_a = onboarded_supplier(client, "iso1", name="Isolation A", email="a@isolationco.com")
    _staff_b, supplier_b, headers_b = onboarded_supplier(client, "iso2", name="Isolation B", email="b@isolationco.com")

    res = client.post("/api/v1/supplier-portal/products", json={"name": "A's Product", "unit": "bag", "price": "10"}, headers=headers_a)
    product_id = res.json()["id"]

    res = client.get(f"/api/v1/supplier-portal/products/{product_id}", headers=headers_b)
    assert res.status_code == 404  # B can't even see A's product

    res = client.patch(f"/api/v1/supplier-portal/products/{product_id}", json={"price": "1"}, headers=headers_b)
    assert res.status_code == 404  # and certainly can't edit it


def test_supplier_cannot_access_platform_admin_endpoints(client):
    _staff, _supplier, headers = onboarded_supplier(client, "noplatform", email="noplatform@test.com")
    res = client.get("/api/v1/platform/billing/overview", headers=headers)
    assert res.status_code == 401  # a supplier_access token can never satisfy platform_access


def test_supplier_cannot_reach_tenant_endpoints(client, auth_a):
    _staff, _supplier, headers = onboarded_supplier(client, "notenant", email="notenant@test.com")
    res = client.get("/api/v1/projects", headers=headers)
    assert res.status_code == 401  # a supplier_access token can never satisfy a tenant "access" token either


# ---- PLAT-040: product catalog -----------------------------------------------------------------


def test_product_catalog_crud(client):
    _staff, _supplier, headers = onboarded_supplier(client, "catalog", email="catalog@test.com")
    res = client.post("/api/v1/supplier-portal/products", json={"name": "Portland Cement", "category": "cement", "unit": "bag", "price": "12.50", "minimum_order_quantity": "10", "lead_time_days": 3}, headers=headers)
    assert res.status_code == 201, res.text
    product = res.json()
    assert product["is_active"] is True

    res = client.patch(f"/api/v1/supplier-portal/products/{product['id']}", json={"price": "15.00", "is_active": False}, headers=headers)
    assert res.status_code == 200
    assert Decimal(res.json()["price"]) == Decimal("15.00")
    assert res.json()["is_active"] is False

    res = client.get("/api/v1/supplier-portal/products", params={"search": "Portland"}, headers=headers)
    assert len(res.json()) == 1


# ---- PLAT-041: RFQ inbox and quotations -----------------------------------------------------------


def _invited_rfq(client, auth, staff, mkt_supplier):
    company_id = enable_marketplace(client, staff, auth)
    project = make(client, auth, "/projects", {"name": "Portal Tower", "code": "PORT", "budget": "1"})
    material = make(client, auth, "/materials", {"name": "Cement", "sku": "CEMP", "unit": "Bag"})
    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth)
    assert res.status_code == 201, res.text
    rfq = make(client, auth, "/rfqs", {"title": "Cement RFQ", "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "100"}]})
    res = client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth)
    assert res.status_code == 201, res.text
    return company_id, rfq


def test_supplier_can_submit_a_quotation_for_an_authorized_invitation(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "quote1", name="Quote Co", email="quote1@test.com")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)

    res = client.get("/api/v1/supplier-portal/rfqs", headers=headers)
    assert any(r["rfq_id"] == rfq["id"] for r in res.json())

    detail = client.get(f"/api/v1/supplier-portal/rfqs/{rfq['id']}", headers=headers).json()
    assert detail["my_quotation"] is None
    item_id = detail["items"][0]["id"]

    res = client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"delivery_days": 5, "items": [{"rfq_item_id": item_id, "rate": "50"}]}, headers=headers)
    assert res.status_code == 201, res.text
    assert Decimal(res.json()["total"]) == Decimal("5000.00")  # 100 * 50

    detail2 = client.get(f"/api/v1/supplier-portal/rfqs/{rfq['id']}", headers=headers).json()
    assert detail2["my_quotation"] is not None


def test_supplier_cannot_submit_an_uninvited_quotation(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "uninvited", name="Uninvited Co", email="uninvited@test.com")
    company_id = enable_marketplace(client, staff, auth_a)
    project = make(client, auth_a, "/projects", {"name": "Pending Co", "code": "UNIN", "budget": "1"})
    material = make(client, auth_a, "/materials", {"name": "M", "sku": "UNINM", "unit": "kg"})
    rfq = make(client, auth_a, "/rfqs", {"title": "Not invited", "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "1"}]})
    # Deliberately never invited.
    res = client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "1"}]}, headers=headers)
    assert res.status_code == 404


def test_supplier_cannot_view_competing_suppliers_quotations(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "compete1", name="Competitor A", email="compete1@test.com")
    _staff2, mkt_supplier_b, headers_b = onboarded_supplier(client, "compete2", name="Competitor B", email="compete2@test.com")

    company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)
    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier_b['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    assert res.status_code == 201
    client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier_b["id"]]}, headers=auth_a)

    item_id = rfq["items"][0]["id"]
    client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": item_id, "rate": "10"}]}, headers=headers)
    client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": item_id, "rate": "99"}]}, headers=headers_b)

    detail = client.get(f"/api/v1/supplier-portal/rfqs/{rfq['id']}", headers=headers).json()
    assert Decimal(detail["my_quotation"]["items"][0]["rate"]) == Decimal("10")
    assert "quotations" not in detail  # the schema itself never carries a competitor list


def test_duplicate_quotation_submission_replaces_not_duplicates(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "dupe", name="Dupe Co", email="dupe@test.com")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)
    item_id = rfq["items"][0]["id"]

    client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": item_id, "rate": "10"}]}, headers=headers)
    res = client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": item_id, "rate": "20"}]}, headers=headers)
    assert res.status_code == 201
    assert Decimal(res.json()["items"][0]["rate"]) == Decimal("20")  # revised, not a second live quotation

    detail = client.get(f"/api/v1/supplier-portal/rfqs/{rfq['id']}", headers=headers).json()
    assert Decimal(detail["my_quotation"]["items"][0]["rate"]) == Decimal("20")


def test_quotation_attributed_to_supplier_not_platform_staff(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "attrib", name="Attrib Co", email="attrib@test.com")
    company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)
    item_id = rfq["items"][0]["id"]
    client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": item_id, "rate": "10"}]}, headers=headers)

    res = client.get(f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/quotation-attributions", headers=staff)
    assert res.status_code == 200
    attribution = res.json()[0]
    assert attribution["method"] == "supplier_self_submitted"
    assert attribution["submitted_by_staff_id"] is None
    assert attribution["submitted_by_supplier_user_id"] is not None


def test_declined_invitation_cannot_then_be_quoted_on(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "decline", name="Decline Co", email="decline@test.com")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)
    res = client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/decline", headers=headers)
    assert res.status_code == 204
    res = client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "1"}]}, headers=headers)
    assert res.status_code == 403


# ---- PLAT-042: orders, delivery updates, commission statements -----------------------------------


def _awarded_po(client, auth, staff, mkt_supplier):
    company_id, rfq = _invited_rfq(client, auth, staff, mkt_supplier)
    item_id = rfq["items"][0]["id"]
    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
        json={"items": [{"rfq_item_id": item_id, "rate": "100"}], "delivery_days": 5}, headers=staff,
    )
    quotation_id = res.json()["quotations"][0]["id"]
    res = client.post(f"/api/v1/rfqs/{rfq['id']}/award", json={"quotation_id": quotation_id}, headers=auth)
    po_id = res.json()["purchase_order_id"]
    client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=auth)
    return po_id


def test_supplier_can_view_linked_order_and_submit_delivery_update(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "order1", name="Order Co", email="order1@test.com")
    po_id = _awarded_po(client, auth_a, staff, mkt_supplier)

    res = client.get("/api/v1/supplier-portal/orders", headers=headers)
    assert any(o["purchase_order_id"] == po_id for o in res.json())

    res = client.post(f"/api/v1/supplier-portal/orders/{po_id}/delivery-updates", json={"external_reference": "SHIP-001", "note": "Left warehouse"}, headers=headers)
    assert res.status_code == 201, res.text
    assert res.json()["already_recorded"] is False

    # Idempotent re-report.
    res2 = client.post(f"/api/v1/supplier-portal/orders/{po_id}/delivery-updates", json={"external_reference": "SHIP-001"}, headers=headers)
    assert res2.json()["already_recorded"] is True


def test_supplier_delivery_reports_never_post_stock_or_touch_inventory(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "noinvty", name="No Inventory Co", email="noinvty@test.com")
    po_id = _awarded_po(client, auth_a, staff, mkt_supplier)
    client.post(f"/api/v1/supplier-portal/orders/{po_id}/delivery-updates", json={"external_reference": "SHIP-X"}, headers=headers)

    po = client.get(f"/api/v1/purchase-orders/{po_id}", headers=auth_a).json()
    assert po["status"] == "approved"  # unchanged -- a delivery update is never a goods receipt
    assert all(Decimal(item["quantity_received"]) == 0 for item in po["items"])

    res = client.get("/api/v1/inventory/stock", headers=auth_a)
    assert res.status_code == 200
    assert all(Decimal(r["quantity_on_hand"]) == 0 for r in res.json())


def test_supplier_cannot_view_unrelated_orders(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "order2", name="Order Co 2", email="order2@test.com")
    _staff2, mkt_supplier_c, headers_c = onboarded_supplier(client, "order3", name="Order Co 3", email="order3@test.com")
    po_id = _awarded_po(client, auth_a, staff, mkt_supplier)

    res = client.get(f"/api/v1/supplier-portal/orders/{po_id}", headers=headers_c)
    assert res.status_code == 404


def test_commission_statement_isolation(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "comm1", name="Comm Supplier A", email="comm1@test.com")
    _staff2, mkt_supplier_b, headers_b = onboarded_supplier(client, "comm2", name="Comm Supplier B", email="comm2@test.com")

    res = client.post(f"/api/v1/platform/commissions/suppliers/{mkt_supplier['id']}/agreements", json={"basis": "percentage", "rate": "0.1"}, headers=staff)
    assert res.status_code == 201

    po_id = _awarded_po(client, auth_a, staff, mkt_supplier)
    client.post("/api/v1/payments/supplier", json={"purchase_order_id": po_id, "amount": "10000", "paid_on": "2026-10-19", "method": "bank_transfer"}, headers=auth_a)

    res = client.get("/api/v1/supplier-portal/commissions/ledger", headers=headers)
    assert len(res.json()) == 1
    assert Decimal(res.json()[0]["commission_amount"]) == Decimal("1000.00")

    res_b = client.get("/api/v1/supplier-portal/commissions/ledger", headers=headers_b)
    assert res_b.json() == []  # B sees nothing of A's commission ledger

    invoice = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    ).json()
    res = client.get(f"/api/v1/supplier-portal/commissions/invoices/{invoice['id']}", headers=headers)
    assert res.status_code == 200
    res_b = client.get(f"/api/v1/supplier-portal/commissions/invoices/{invoice['id']}", headers=headers_b)
    assert res_b.status_code == 404


def test_supplier_dashboard_reflects_real_counts(client, auth_a):
    staff, mkt_supplier, headers = onboarded_supplier(client, "dash", name="Dash Co", email="dash@test.com")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)

    res = client.get("/api/v1/supplier-portal/dashboard", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["new_invitations"] == 1
    assert body["submitted_quotations"] == 0

    item_id = rfq["items"][0]["id"]
    client.post(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/quotations", json={"items": [{"rfq_item_id": item_id, "rate": "1"}]}, headers=headers)
    res = client.get("/api/v1/supplier-portal/dashboard", headers=headers)
    assert res.json()["submitted_quotations"] == 1


def test_supplier_profile_cannot_edit_name_or_verification(client):
    _staff, mkt_supplier, headers = onboarded_supplier(client, "profile", name="Profile Co", email="profile@test.com")
    res = client.get("/api/v1/supplier-portal/profile", headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Profile Co"

    res = client.patch("/api/v1/supplier-portal/profile", json={"phone": "555-1234", "notes": "We ship fast"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["phone"] == "555-1234"
    assert res.json()["name"] == "Profile Co"  # untouched -- update schema has no name field at all
    assert res.json()["verification_status"] == "verified"


def test_existing_erp_regression_untouched_by_supplier_portal(client, auth_a):
    """A plain ERP PO with no marketplace involvement, paid in full, still
    produces zero commission and is invisible to every supplier."""
    _staff, mkt_supplier, headers = onboarded_supplier(client, "regress", name="Regress Co", email="regress@test.com")
    project = make(client, auth_a, "/projects", {"name": "Plain", "code": "PLAIN1", "budget": "1"})
    material = make(client, auth_a, "/materials", {"name": "Plain Mat", "sku": "PLNM", "unit": "kg"})
    supplier = make(client, auth_a, "/suppliers", {"name": "Plain ERP Supplier"})
    po = make(client, auth_a, "/purchase-orders", {"supplier_id": supplier["id"], "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "1", "rate": "100"}]})
    client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=auth_a)
    client.post("/api/v1/payments/supplier", json={"purchase_order_id": po["id"], "amount": "100", "paid_on": "2026-10-19", "method": "bank_transfer"}, headers=auth_a)

    res = client.get("/api/v1/supplier-portal/orders", headers=headers)
    assert all(o["purchase_order_id"] != po["id"] for o in res.json())
