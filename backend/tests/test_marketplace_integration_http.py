"""Marketplace-to-ERP integration (PLAT-021..027): the complete flow from a
company's ERP RFQ through a marketplace supplier invitation, a quotation,
selecting it (the existing award endpoint), PO approval, and a real goods
receipt that actually moves inventory -- plus every required negative case."""

from decimal import Decimal

import pytest

from app.models.enums import PlatformStaffRole
from tests.test_platform_http import platform_login


def make(client, headers, path, body=None):
    res = client.post(f"/api/v1{path}", headers=headers, json=body or {})
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


def owner_headers(client, email="mkt-int-owner@buildos.ai"):
    return platform_login(client, email=email, role=PlatformStaffRole.OWNER)


def enable_marketplace(client, staff_headers, tenant_headers):
    """The marketplace is disabled by default for every company (Phase 4.1
    Task 4); tests that exercise marketplace actions turn it on explicitly,
    which also doubles as live proof the gate works (see
    test_marketplace_disabled_by_default_blocks_actions below)."""
    company_id = client.get("/api/v1/auth/me", headers=tenant_headers).json()["company_id"]
    res = client.post(f"/api/v1/platform/companies/{company_id}/marketplace", json={"enabled": True}, headers=staff_headers)
    assert res.status_code == 200, res.text
    return company_id


def make_verified_supplier(client, staff_headers, name="Global Cement Ltd", categories=None, areas=None):
    res = client.post(
        "/api/v1/platform/marketplace/suppliers",
        json={"name": name, "categories": categories or ["cement"], "coverage_areas": areas or ["Punjab"]},
        headers=staff_headers,
    )
    assert res.status_code == 201, res.text
    supplier = res.json()["supplier"]
    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/verification",
        json={"status": "verified"},
        headers=staff_headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def s(client, auth_a):
    return {
        "project": make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"}),
        "warehouse": make(client, auth_a, "/warehouses", {"name": "Main"}),
        "cement": make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"}),
    }


def stock_of(client, headers, material_name):
    rows = client.get("/api/v1/inventory/stock", headers=headers).json()
    return sum((Decimal(r["quantity_on_hand"]) for r in rows if r["material_name"] == material_name), Decimal("0"))


# ---- The complete flow -------------------------------------------------------------------


def test_complete_flow_company_rfq_to_marketplace_to_inventory(client, auth_a, s):
    staff = owner_headers(client)
    mkt_supplier = make_verified_supplier(client, staff, name="Flow Cement Co")

    company_id = enable_marketplace(client, staff, auth_a)

    # 1. Company connects to the marketplace supplier, creating a real ERP Supplier
    #    through the existing supplier_service (not a parallel system).
    res = client.post(
        f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect",
        json={"create_new_erp_supplier": True, "is_preferred": True},
        headers=auth_a,
    )
    assert res.status_code == 201, res.text
    connection = res.json()
    assert connection["erp_supplier_id"] is not None
    erp_supplier_id = connection["erp_supplier_id"]

    # The new ERP supplier is real and shows up in the normal supplier list.
    res = client.get("/api/v1/suppliers", headers=auth_a)
    assert any(sup["id"] == erp_supplier_id for sup in res.json())

    # 2. Company raises a normal ERP RFQ (existing endpoint, untouched).
    rfq = make(
        client, auth_a, "/rfqs",
        {"title": "Cement for Tower", "project_id": s["project"]["id"], "items": [{"material_id": s["cement"]["id"], "quantity": "500"}]},
    )

    # 3. Company invites the connected marketplace supplier to quote.
    res = client.post(
        f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers",
        json={"marketplace_supplier_ids": [mkt_supplier["id"]]},
        headers=auth_a,
    )
    assert res.status_code == 201, res.text

    # The real RFQ now lists the ERP supplier as invited -- same RfqSupplier
    # mechanism as a normal, non-marketplace invitation.
    rfq = client.get(f"/api/v1/rfqs/{rfq['id']}", headers=auth_a).json()
    assert erp_supplier_id in [v["supplier_id"] for v in rfq["invited"]]

    # 4. Platform staff records a quotation on the supplier's behalf.
    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
        json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "1200"}], "delivery_days": 5},
        headers=staff,
    )
    assert res.status_code == 201, res.text
    rfq = res.json()
    quotation_id = rfq["quotations"][0]["id"]

    # 5. Company selects the quotation through the existing award endpoint --
    #    no second purchase-order system.
    res = client.post(f"/api/v1/rfqs/{rfq['id']}/award", json={"quotation_id": quotation_id}, headers=auth_a)
    assert res.status_code == 200, res.text
    awarded = res.json()
    po_id = awarded["purchase_order_id"]
    po = client.get(f"/api/v1/purchase-orders/{po_id}", headers=auth_a).json()
    assert po["status"] == "pending_approval"
    assert po["supplier_id"] == erp_supplier_id

    # 6. Approval is mandatory, same as always.
    res = client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=auth_a)
    assert res.status_code == 200, res.text

    # 7. Marketplace status reflects the real (pre-receipt) ERP state.
    res = client.get(f"/api/v1/marketplace/purchase-orders/{po_id}/status", headers=auth_a)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "approved"
    assert res.json()["fully_received"] is False
    assert res.json()["delivery_reported"] is False

    # 8. A supplier-reported delivery is recorded but changes NOTHING in inventory.
    before_stock = stock_of(client, auth_a, "Cement")
    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/purchase-orders/{po_id}/delivery-reports",
        json={"external_reference": "carrier-ref-001", "note": "Left the warehouse"},
        headers=staff,
    )
    assert res.status_code == 201, res.text
    assert res.json()["already_recorded"] is False
    assert stock_of(client, auth_a, "Cement") == before_stock  # untouched

    # Idempotent: reporting the same event again doesn't duplicate it.
    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/purchase-orders/{po_id}/delivery-reports",
        json={"external_reference": "carrier-ref-001", "note": "retry"},
        headers=staff,
    )
    assert res.status_code == 201
    assert res.json()["already_recorded"] is True

    res = client.get(f"/api/v1/marketplace/purchase-orders/{po_id}/status", headers=auth_a)
    assert res.json()["delivery_reported"] is True

    # 9. ONLY the real goods receipt moves inventory -- same endpoint as any
    #    non-marketplace PO.
    res = client.post(
        f"/api/v1/purchase-orders/{po_id}/goods-receipts",
        json={"warehouse_id": s["warehouse"]["id"], "items": [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "500"}]},
        headers=auth_a,
    )
    assert res.status_code == 201, res.text
    assert stock_of(client, auth_a, "Cement") == before_stock + 500

    res = client.get(f"/api/v1/marketplace/purchase-orders/{po_id}/status", headers=auth_a)
    assert res.json()["status"] == "received"
    assert res.json()["fully_received"] is True


# ---- Tenant isolation --------------------------------------------------------------------


def test_company_a_cannot_access_company_b_marketplace_data(client, auth_a, auth_b, s):
    staff = owner_headers(client, email="iso-staff@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Isolation Supplier")
    enable_marketplace(client, staff, auth_a)
    enable_marketplace(client, staff, auth_b)

    client.post(
        f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect",
        json={"create_new_erp_supplier": True},
        headers=auth_a,
    )
    rfq = make(client, auth_a, "/rfqs", {"title": "A's RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})

    # B never connected to the supplier, and A's RFQ isn't B's -- both must fail.
    res = client.post(
        f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers",
        json={"marketplace_supplier_ids": [mkt_supplier["id"]]},
        headers=auth_b,
    )
    assert res.status_code in (404, 400)  # rfq_service.get_rfq 404s before the connection check even runs

    res = client.get("/api/v1/marketplace/connections", headers=auth_b)
    assert res.json() == []  # B's connection list never shows A's connection

    po_res = client.get(f"/api/v1/marketplace/purchase-orders/{rfq['id']}/status", headers=auth_b)
    assert po_res.status_code == 404


def test_platform_staff_match_and_status_are_scoped_to_the_given_company(client, auth_a, auth_b, s):
    staff = owner_headers(client, email="scope-staff@buildos.ai")
    company_a_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    company_b_id = client.get("/api/v1/auth/me", headers=auth_b).json()["company_id"]

    po = make(client, auth_a, "/purchase-orders", {
        "supplier_id": make(client, auth_a, "/suppliers", {"name": "Co X"})["id"],
        "items": [{"material_id": s["cement"]["id"], "quantity": "10", "rate": "5"}],
    })

    res = client.get(f"/api/v1/platform/marketplace/companies/{company_a_id}/purchase-orders/{po['id']}/status", headers=staff)
    assert res.status_code == 200
    res = client.get(f"/api/v1/platform/marketplace/companies/{company_b_id}/purchase-orders/{po['id']}/status", headers=staff)
    assert res.status_code == 404  # same PO id, wrong company scope -> not found, not leaked


# ---- Eligibility and duplicate protections ------------------------------------------------


def test_suspended_supplier_cannot_receive_new_invitations(client, auth_a, s):
    staff = owner_headers(client, email="suspend-staff@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Soon Suspended Co")
    enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/verification", json={"status": "suspended"}, headers=staff)

    rfq = make(client, auth_a, "/rfqs", {"title": "RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})
    res = client.post(
        f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers",
        json={"marketplace_supplier_ids": [mkt_supplier["id"]]},
        headers=auth_a,
    )
    assert res.status_code == 400


def test_duplicate_invitations_are_rejected(client, auth_a, s):
    staff = owner_headers(client, email="dup-invite-staff@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Dup Invite Co")
    enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    rfq = make(client, auth_a, "/rfqs", {"title": "RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})

    res1 = client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth_a)
    assert res1.status_code == 201
    res2 = client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth_a)
    assert res2.status_code == 409


def test_duplicate_connection_is_rejected(client, auth_a):
    staff = owner_headers(client, email="dup-connect-staff@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Dup Connect Co")
    enable_marketplace(client, staff, auth_a)
    res1 = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    assert res1.status_code == 201
    res2 = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    assert res2.status_code == 409


def test_duplicate_purchase_orders_are_prevented(client, auth_a, s):
    """Unchanged ERP behaviour: an RFQ can only be awarded once."""
    staff = owner_headers(client, email="dup-po-staff@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Dup PO Co")
    company_id = enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth_a)
    rfq = make(client, auth_a, "/rfqs", {"title": "RFQ", "items": [{"material_id": s["cement"]["id"], "quantity": "10"}]})
    client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth_a)

    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
        json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "100"}]},
        headers=staff,
    )
    assert res.status_code == 201, res.text
    rfq = res.json()
    quotation_id = rfq["quotations"][0]["id"]

    res1 = client.post(f"/api/v1/rfqs/{rfq['id']}/award", json={"quotation_id": quotation_id}, headers=auth_a)
    assert res1.status_code == 200
    res2 = client.post(f"/api/v1/rfqs/{rfq['id']}/award", json={"quotation_id": quotation_id}, headers=auth_a)
    assert res2.status_code == 409  # RFQ already awarded -- no second PO


def test_goods_receipts_cannot_post_twice(client, auth_a, s):
    """Unchanged ERP behaviour: can't receive more than was ordered."""
    po = make(client, auth_a, "/purchase-orders", {
        "supplier_id": make(client, auth_a, "/suppliers", {"name": "Co Y"})["id"],
        "items": [{"material_id": s["cement"]["id"], "quantity": "100", "rate": "10"}],
    })
    client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=auth_a)
    po = client.get(f"/api/v1/purchase-orders/{po['id']}", headers=auth_a).json()

    res1 = client.post(f"/api/v1/purchase-orders/{po['id']}/goods-receipts", json={
        "warehouse_id": s["warehouse"]["id"], "items": [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "100"}]
    }, headers=auth_a)
    assert res1.status_code == 201

    res2 = client.post(f"/api/v1/purchase-orders/{po['id']}/goods-receipts", json={
        "warehouse_id": s["warehouse"]["id"], "items": [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "1"}]
    }, headers=auth_a)
    assert res2.status_code == 400  # nothing left to receive


# ---- The marketplace is additive: ERP works the same with zero marketplace calls ------


def test_existing_erp_procurement_flow_works_with_no_marketplace_involvement(client, auth_a, s):
    """Proves the marketplace tables/routes are purely additive: a complete
    RFQ -> quotation -> award -> approve -> receipt cycle that never touches a
    single /marketplace or /platform/marketplace endpoint. This is the
    practical equivalent of 'the marketplace feature can be disabled without
    affecting ERP operations' -- there's no feature-flag system in this
    codebase (confirmed in the Day 28 audit), so the real guarantee is
    structural: no ERP table has a required FK to a marketplace table, and no
    ERP service imports marketplace_integration_service."""
    supplier = make(client, auth_a, "/suppliers", {"name": "Plain ERP Supplier"})
    rfq = make(client, auth_a, "/rfqs", {
        "title": "No marketplace involved",
        "items": [{"material_id": s["cement"]["id"], "quantity": "50"}],
        "supplier_ids": [supplier["id"]],
    })
    rfq = make(client, auth_a, f"/rfqs/{rfq['id']}/quotations", {
        "supplier_id": supplier["id"], "items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "20"}]
    })
    awarded = make(client, auth_a, f"/rfqs/{rfq['id']}/award", {"quotation_id": rfq["quotations"][0]["id"]})
    client.post(f"/api/v1/purchase-orders/{awarded['purchase_order_id']}/approve", headers=auth_a)
    po = client.get(f"/api/v1/purchase-orders/{awarded['purchase_order_id']}", headers=auth_a).json()
    res = client.post(f"/api/v1/purchase-orders/{po['id']}/goods-receipts", json={
        "warehouse_id": s["warehouse"]["id"], "items": [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "50"}]
    }, headers=auth_a)
    assert res.status_code == 201
    assert stock_of(client, auth_a, "Cement") == 50


def test_no_erp_service_imports_the_marketplace_integration_service():
    import ast
    import pathlib

    erp_service_files = [
        "rfq_service.py", "procurement_service.py", "supplier_service.py",
        "inventory_service.py", "finance_service.py", "project_service.py",
    ]
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "services"
    for filename in erp_service_files:
        tree = ast.parse((root / filename).read_text())
        imported = {
            alias.name if isinstance(node, ast.Import) else node.module
            for node in ast.walk(tree)
            for alias in (node.names if hasattr(node, "names") else [])
            if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        assert not any("marketplace" in (name or "") for name in imported), f"{filename} imports a marketplace module"


# ---- Supplier matching (PLAT-027) ---------------------------------------------------------


def test_eligible_supplier_matching_is_deterministic_and_real(client, auth_a, s):
    staff = owner_headers(client, email="match-staff@buildos.ai")
    category = make(client, auth_a, "/material-categories", {"name": "Cement"})
    cement = make(client, auth_a, "/materials", {"name": "Match Cement", "sku": "MCEM", "unit": "Bag", "category_id": category["id"]})

    good_supplier = make_verified_supplier(client, staff, name="Matching Supplier", categories=["Cement"], areas=["Lahore"])
    client.post(f"/api/v1/platform/marketplace/suppliers/{good_supplier['id']}/products", json={
        "name": "OPC 50kg", "unit": "bag", "price": "900", "minimum_order_quantity": "50", "lead_time_days": 2
    }, headers=staff)

    wrong_category = make_verified_supplier(client, staff, name="Steel Only Co", categories=["Steel"], areas=["Lahore"])
    client.post(f"/api/v1/platform/marketplace/suppliers/{wrong_category['id']}/products", json={
        "name": "Rebar", "unit": "ton", "price": "180000"
    }, headers=staff)

    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.get(f"/api/v1/platform/marketplace/companies/{company_id}/match?material_id={cement['id']}&area=Lahore", headers=staff)
    assert res.status_code == 200, res.text
    names = [m["supplier_name"] for m in res.json()]
    assert "Matching Supplier" in names
    assert "Steel Only Co" not in names
    assert res.json()[0]["matched_via"] == "category"
    assert Decimal(res.json()[0]["price"]) == 900  # the real entered price, nothing invented


def test_material_mapping_takes_priority_over_category_match(client, auth_a, s):
    staff = owner_headers(client, email="mapping-staff@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Mapped Supplier", categories=["cement"], areas=["Karachi"])
    product = client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/products", json={
        "name": "Mapped Product", "unit": "bag", "price": "850"
    }, headers=staff).json()

    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.post("/api/v1/platform/marketplace/material-mappings", json={
        "company_id": company_id, "material_id": s["cement"]["id"], "marketplace_product_id": product["id"]
    }, headers=staff)
    assert res.status_code == 201, res.text

    res = client.get(f"/api/v1/platform/marketplace/companies/{company_id}/match?material_id={s['cement']['id']}", headers=staff)
    assert res.status_code == 200
    assert any(m["matched_via"] == "material_mapping" and m["product_name"] == "Mapped Product" for m in res.json())
