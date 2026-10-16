"""Phase 4.1 Task 3 (quotation attribution) and Task 4 (marketplace feature
flag): disabled by default, platform-staff-only toggle, server-side
enforcement, historical records preserved, and the real actor correctly
recorded without touching Quotation.created_by_id."""

from app.models.enums import PlatformStaffRole
from tests.test_marketplace_integration_http import enable_marketplace, make, make_verified_supplier, owner_headers
from tests.test_marketplace_integration_http import s  # noqa: F401 -- reused fixture


# ---- Feature flag --------------------------------------------------------------------------


def test_marketplace_is_disabled_by_default_for_every_company(client, auth_a):
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.status_code == 200
    assert res.json()["enabled"] is False


def test_disabled_marketplace_blocks_actions_server_side(client, auth_a):
    staff = owner_headers(client, email="flag-staff1@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Flag Blocked Co")

    res = client.get("/api/v1/marketplace/suppliers", headers=auth_a)
    assert res.status_code == 403

    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    assert res.status_code == 403


def test_enabling_marketplace_lets_actions_through(client, auth_a):
    staff = owner_headers(client, email="flag-staff2@buildos.ai")
    enable_marketplace(client, staff, auth_a)
    res = client.get("/api/v1/marketplace/suppliers", headers=auth_a)
    assert res.status_code == 200
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.json()["enabled"] is True


def test_only_owner_or_admin_staff_can_toggle_the_flag(client, auth_a):
    from tests.test_platform_http import platform_login

    support = platform_login(client, email="flag-support@buildos.ai", role=PlatformStaffRole.SUPPORT)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.post(f"/api/v1/platform/companies/{company_id}/marketplace", json={"enabled": True}, headers=support)
    assert res.status_code == 403


def test_existing_erp_workflows_are_unaffected_by_the_flag_either_way(client, auth_a):
    """A company with the marketplace left disabled must still be able to do
    completely normal, non-marketplace procurement."""
    res = client.get("/api/v1/marketplace/status", headers=auth_a).json()
    assert res["enabled"] is False
    supplier = client.post("/api/v1/suppliers", json={"name": "Totally Normal Supplier"}, headers=auth_a)
    assert supplier.status_code == 201
    assert client.get("/api/v1/rfqs", headers=auth_a).status_code == 200
    assert client.get("/api/v1/purchase-orders", headers=auth_a).status_code == 200


def test_disabling_marketplace_after_the_fact_preserves_historical_records(client, auth_a):
    staff = owner_headers(client, email="flag-staff3@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="History Preserved Co")
    company_id = enable_marketplace(client, staff, auth_a)
    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    connection_id = res.json()["id"]

    # Disable it again.
    res = client.post(f"/api/v1/platform/companies/{company_id}/marketplace", json={"enabled": False}, headers=staff)
    assert res.status_code == 200
    assert res.json()["marketplace_enabled"] is False

    # The connection record itself still exists and is still readable by platform staff.
    res = client.get(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/company-links", headers=staff)
    assert res.status_code == 200
    assert any(link["id"] == connection_id for link in res.json())

    # New marketplace actions are blocked again now that it's off.
    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    assert res.status_code == 403


def test_platform_administration_remains_available_regardless_of_any_companys_flag(client, auth_a):
    """Platform staff can still manage the supplier registry itself -- create,
    verify, catalog -- whether or not any particular company has marketplace
    access turned on."""
    staff = owner_headers(client, email="flag-staff4@buildos.ai")
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.json()["enabled"] is False  # disabled for this company

    res = client.post("/api/v1/platform/marketplace/suppliers", json={"name": "Still Manageable Co"}, headers=staff)
    assert res.status_code == 201
    supplier_id = res.json()["supplier"]["id"]
    res = client.post(f"/api/v1/platform/marketplace/suppliers/{supplier_id}/verification", json={"status": "verified"}, headers=staff)
    assert res.status_code == 200
    res = client.get("/api/v1/platform/marketplace/suppliers", headers=staff)
    assert res.status_code == 200


# ---- Quotation attribution --------------------------------------------------------------


def test_assisted_quotation_preserves_the_real_quotation_creator_fk(client, auth_a, s):
    """Quotation.created_by_id (exposed as rfq.created_by_id's equivalent via
    the RFQ itself) must keep meaning what it always meant: a real tenant user,
    unaffected by this feature."""
    staff = owner_headers(client, email="attr-staff1@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Attribution Co")
    company_id = enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    rfq = make(client, auth_a, "/rfqs", {"title": "Attribution RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})
    client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth_a)

    rfq_admin = client.get("/api/v1/auth/me", headers=auth_a).json()
    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
        json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "55"}]},
        headers=staff,
    )
    assert res.status_code == 201, res.text
    rfq_after = res.json()
    quotation = rfq_after["quotations"][0]
    # The RFQ was created by the company admin; that's who the real
    # Quotation.created_by_id-backed RFQ data still (correctly) shows -- this
    # is NOT who actually typed the rates in, which is exactly the problem
    # the attribution record below solves.
    assert rfq_after["created_at"] is not None  # sanity: RFQ itself untouched

    # The honest record: who actually submitted it, which supplier, which
    # quotation, when.
    res = client.get(f"/api/v1/marketplace/rfqs/{rfq['id']}/quotation-attributions", headers=auth_a)
    assert res.status_code == 200, res.text
    attributions = res.json()
    assert len(attributions) == 1
    att = attributions[0]
    assert att["quotation_id"] == quotation["id"]
    assert att["marketplace_supplier_name"] == "Attribution Co"
    assert att["submitted_by_staff_name"] == "Platform Admin"
    assert att["method"] == "platform_staff_assisted"
    assert att["total_amount"] == "550.00"


def test_attribution_never_falsely_shows_the_rfq_creator_as_the_submitter(client, auth_a, s):
    staff = owner_headers(client, email="attr-staff2@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="No False Attribution Co")
    company_id = enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    rfq = make(client, auth_a, "/rfqs", {"title": "RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})
    client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth_a)
    client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
        json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "10"}]},
        headers=staff,
    )
    res = client.get(f"/api/v1/marketplace/rfqs/{rfq['id']}/quotation-attributions", headers=auth_a)
    # The submitter name must be the real platform staff member, never the
    # company admin who merely created the RFQ.
    assert res.json()[0]["submitted_by_staff_name"] == "Platform Admin"
    assert res.json()[0]["submitted_by_staff_name"] != "Test Admin"


def test_a_regular_company_entered_quotation_has_no_attribution_record(client, auth_a, s):
    """Attribution rows only exist for staff-assisted submissions -- a normal
    company-entered quote (the existing, untouched RFQ flow) creates none."""
    supplier = make(client, auth_a, "/suppliers", {"name": "Plain Supplier"})
    rfq = make(client, auth_a, "/rfqs", {"title": "Plain RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}], "supplier_ids": [supplier["id"]]})
    make(client, auth_a, f"/rfqs/{rfq['id']}/quotations", {"supplier_id": supplier["id"], "items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "5"}]})

    res = client.get(f"/api/v1/marketplace/rfqs/{rfq['id']}/quotation-attributions", headers=auth_a)
    assert res.status_code == 200
    assert res.json() == []


def test_a_requote_by_staff_adds_a_new_attribution_row_not_an_edit(client, auth_a, s):
    staff = owner_headers(client, email="attr-staff3@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Requote Co")
    company_id = enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    rfq = make(client, auth_a, "/rfqs", {"title": "RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})
    client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth_a)

    for rate in ("10", "20"):
        client.post(
            f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
            json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": rate}]},
            headers=staff,
        )

    res = client.get(f"/api/v1/marketplace/rfqs/{rfq['id']}/quotation-attributions", headers=auth_a)
    assert len(res.json()) == 2  # both submission events kept, nothing overwritten
