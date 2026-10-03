"""BUILD-131: material request -> purchase order -> approval -> goods receipt,
and the inventory that receipt creates."""

from decimal import Decimal

import pytest

from tests.conftest import make_user_in_company


def make(client, headers, path, body=None):
    res = client.post(f"/api/v1{path}", headers=headers, json=body or {})
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


@pytest.fixture
def setup(client, auth_a):
    return {
        "project": make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"}),
        "supplier": make(client, auth_a, "/suppliers", {"name": "Acme"}),
        "warehouse": make(client, auth_a, "/warehouses", {"name": "Main"}),
        "cement": make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"}),
        "steel": make(client, auth_a, "/materials", {"name": "Steel", "sku": "STL", "unit": "Ton"}),
    }


def new_po(client, headers, s, items=None, **extra):
    items = items or [{"material_id": s["cement"]["id"], "quantity": "100", "rate": "10"}]
    return make(client, headers, "/purchase-orders", {"supplier_id": s["supplier"]["id"], "items": items, **extra})


def receive(client, headers, po, warehouse, lines):
    return client.post(f"/api/v1/purchase-orders/{po['id']}/goods-receipts", headers=headers,
                       json={"warehouse_id": warehouse["id"], "items": lines})


def stock_of(client, headers, material_name):
    rows = client.get("/api/v1/inventory/stock", headers=headers).json()
    return sum((Decimal(r["quantity_on_hand"]) for r in rows if r["material_name"] == material_name), Decimal("0"))


# ---- Material requests ---------------------------------------------------------


def test_request_can_be_approved_or_rejected_once(client, auth_a, setup):
    mr = make(client, auth_a, "/material-requests", {
        "project_id": setup["project"]["id"], "items": [{"material_id": setup["cement"]["id"], "quantity": "5"}],
    })
    assert mr["status"] == "pending"
    res = client.patch(f"/api/v1/material-requests/{mr['id']}/status", headers=auth_a, json={"status": "approved"})
    assert res.status_code == 200 and res.json()["status"] == "approved"
    res = client.patch(f"/api/v1/material-requests/{mr['id']}/status", headers=auth_a, json={"status": "rejected"})
    assert res.status_code == 400


@pytest.mark.parametrize("status", ["converted", "pending"])
def test_request_status_endpoint_only_decides(client, auth_a, setup, status):
    # "converted" is set by raising a PO, never by hand.
    mr = make(client, auth_a, "/material-requests", {
        "project_id": setup["project"]["id"], "items": [{"material_id": setup["cement"]["id"], "quantity": "5"}],
    })
    res = client.patch(f"/api/v1/material-requests/{mr['id']}/status", headers=auth_a, json={"status": status})
    assert res.status_code == 400


@pytest.mark.parametrize("decided", [None, "approved"])
def test_raising_a_po_converts_the_request(client, auth_a, setup, decided):
    mr = make(client, auth_a, "/material-requests", {
        "project_id": setup["project"]["id"], "items": [{"material_id": setup["cement"]["id"], "quantity": "5"}],
    })
    if decided:
        client.patch(f"/api/v1/material-requests/{mr['id']}/status", headers=auth_a, json={"status": decided})
    new_po(client, auth_a, setup, material_request_id=mr["id"])
    assert client.get(f"/api/v1/material-requests/{mr['id']}", headers=auth_a).json()["status"] == "converted"


@pytest.mark.parametrize("state", ["rejected", "converted"])
def test_cannot_raise_a_po_from_a_closed_request(client, auth_a, setup, state):
    mr = make(client, auth_a, "/material-requests", {
        "project_id": setup["project"]["id"], "items": [{"material_id": setup["cement"]["id"], "quantity": "5"}],
    })
    if state == "rejected":
        client.patch(f"/api/v1/material-requests/{mr['id']}/status", headers=auth_a, json={"status": "rejected"})
    else:
        new_po(client, auth_a, setup, material_request_id=mr["id"])
    res = client.post("/api/v1/purchase-orders", headers=auth_a, json={
        "supplier_id": setup["supplier"]["id"], "material_request_id": mr["id"],
        "items": [{"material_id": setup["cement"]["id"], "quantity": "5", "rate": "1"}],
    })
    assert res.status_code == 409
    assert len(client.get("/api/v1/purchase-orders", headers=auth_a).json()) == (0 if state == "rejected" else 1)


# ---- Purchase orders -----------------------------------------------------------


def test_po_numbers_are_sequential_per_company(client, auth_a, auth_b, setup):
    assert [new_po(client, auth_a, setup)["po_number"] for _ in range(3)] == ["PO-1001", "PO-1002", "PO-1003"]
    b_setup = {
        "supplier": make(client, auth_b, "/suppliers", {"name": "B Supplier"}),
        "cement": make(client, auth_b, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"}),
    }
    assert new_po(client, auth_b, b_setup)["po_number"] == "PO-1001"


def test_po_totals(client, auth_a, setup):
    po = new_po(client, auth_a, setup, items=[
        {"material_id": setup["cement"]["id"], "quantity": "12.5", "rate": "1400"},
        {"material_id": setup["steel"]["id"], "quantity": "0.75", "rate": "280000"},
    ])
    assert po["status"] == "pending_approval"
    assert sorted(Decimal(i["amount"]) for i in po["items"]) == [Decimal("17500"), Decimal("210000")]


def test_po_needs_items_and_own_references(client, auth_a, auth_b, setup):
    assert client.post("/api/v1/purchase-orders", headers=auth_a,
                       json={"supplier_id": setup["supplier"]["id"], "items": []}).status_code == 422
    foreign_supplier = make(client, auth_b, "/suppliers", {"name": "B Supplier"})
    res = client.post("/api/v1/purchase-orders", headers=auth_a, json={
        "supplier_id": foreign_supplier["id"], "items": [{"material_id": setup["cement"]["id"], "quantity": "1", "rate": "1"}],
    })
    assert res.status_code == 404
    assert client.get("/api/v1/purchase-orders", headers=auth_a).json() == []


def test_approval_flow_and_roles(client, auth_a, setup, viewer_a):
    po = new_po(client, auth_a, setup)
    keeper = make_user_in_company(client, auth_a, "store@example.com", "storekeeper")
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=keeper).status_code == 403
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=viewer_a).status_code == 403
    approved = make(client, auth_a, f"/purchase-orders/{po['id']}/approve")
    assert approved["status"] == "approved"
    assert approved["approved_by_id"] == client.get("/api/v1/auth/me", headers=auth_a).json()["id"]
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=auth_a).status_code == 400


# ---- Goods receipt -------------------------------------------------------------


def test_cannot_receive_before_approval(client, auth_a, setup):
    po = new_po(client, auth_a, setup)
    res = receive(client, auth_a, po, setup["warehouse"], [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "1"}])
    assert res.status_code == 400
    assert stock_of(client, auth_a, "Cement") == 0


def test_partial_then_full_receipt_updates_stock_and_status(client, auth_a, setup):
    po = make(client, auth_a, f"/purchase-orders/{new_po(client, auth_a, setup)['id']}/approve")
    line = po["items"][0]["id"]

    assert receive(client, auth_a, po, setup["warehouse"], [{"purchase_order_item_id": line, "quantity_received": "40"}]).status_code == 201
    po_now = client.get(f"/api/v1/purchase-orders/{po['id']}", headers=auth_a).json()
    assert po_now["status"] == "partially_received" and Decimal(po_now["items"][0]["quantity_received"]) == 40
    assert stock_of(client, auth_a, "Cement") == 40

    # Over-receiving the remainder is refused and changes nothing.
    res = receive(client, auth_a, po, setup["warehouse"], [{"purchase_order_item_id": line, "quantity_received": "60.001"}])
    assert res.status_code == 400
    assert stock_of(client, auth_a, "Cement") == 40

    assert receive(client, auth_a, po, setup["warehouse"], [{"purchase_order_item_id": line, "quantity_received": "60"}]).status_code == 201
    assert client.get(f"/api/v1/purchase-orders/{po['id']}", headers=auth_a).json()["status"] == "received"
    assert stock_of(client, auth_a, "Cement") == 100
    # Received in full: nothing more can come in.
    assert receive(client, auth_a, po, setup["warehouse"], [{"purchase_order_item_id": line, "quantity_received": "1"}]).status_code == 400

    ledger = client.get("/api/v1/inventory/transactions", headers=auth_a).json()
    assert [(t["transaction_type"], t["reference"]) for t in ledger] == [("stock_in", po["po_number"])] * 2


def test_receipt_line_must_belong_to_the_po(client, auth_a, setup):
    po1 = make(client, auth_a, f"/purchase-orders/{new_po(client, auth_a, setup)['id']}/approve")
    po2 = make(client, auth_a, f"/purchase-orders/{new_po(client, auth_a, setup)['id']}/approve")
    res = receive(client, auth_a, po1, setup["warehouse"], [{"purchase_order_item_id": po2["items"][0]["id"], "quantity_received": "1"}])
    assert res.status_code == 400
    assert stock_of(client, auth_a, "Cement") == 0


def test_only_receiving_roles_receive(client, auth_a, setup):
    po = make(client, auth_a, f"/purchase-orders/{new_po(client, auth_a, setup)['id']}/approve")
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    line = [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "1"}]
    assert receive(client, pm, po, setup["warehouse"], line).status_code == 403
    keeper = make_user_in_company(client, auth_a, "store@example.com", "storekeeper")
    assert receive(client, keeper, po, setup["warehouse"], line).status_code == 201


def test_another_company_cannot_see_or_act_on_pos(client, auth_a, auth_b, setup):
    po = new_po(client, auth_a, setup)
    assert client.get(f"/api/v1/purchase-orders/{po['id']}", headers=auth_b).status_code == 404
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=auth_b).status_code == 404
    assert client.get("/api/v1/purchase-orders", headers=auth_b).json() == []
    assert client.get("/api/v1/material-requests", headers=auth_b).json() == []
