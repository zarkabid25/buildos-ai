"""BUILD-130: the inventory ledger. Stock on hand is derived from transactions,
so these pin down the arithmetic and the guards around it."""

from decimal import Decimal

import pytest

from tests.conftest import make_user_in_company


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


@pytest.fixture
def stockyard(client, auth_a):
    """Two warehouses and one material, nothing in stock yet."""
    return {
        "main": make(client, auth_a, "/warehouses", {"name": "Main"}),
        "site": make(client, auth_a, "/warehouses", {"name": "Site"}),
        "cement": make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag", "reorder_point": 20}),
    }


def stock(client, headers):
    """{(material, warehouse): quantity} for every non-zero balance."""
    rows = client.get("/api/v1/inventory/stock", headers=headers).json()
    return {(r["material_name"], r["warehouse_name"]): Decimal(r["quantity_on_hand"]) for r in rows}


def move(client, headers, kind, body):
    return client.post(f"/api/v1/inventory/{kind}", headers=headers, json=body)


def test_balance_is_the_sum_of_movements(client, auth_a, stockyard):
    c, main, site = stockyard["cement"]["id"], stockyard["main"]["id"], stockyard["site"]["id"]
    assert move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "100"}).status_code == 201
    assert move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "0.5"}).status_code == 201
    assert move(client, auth_a, "transfer", {
        "material_id": c, "from_warehouse_id": main, "to_warehouse_id": site, "quantity": "30",
    }).status_code == 201
    assert move(client, auth_a, "stock-out", {"material_id": c, "warehouse_id": site, "quantity": "12.25"}).status_code == 201

    assert stock(client, auth_a) == {("Cement", "Main"): Decimal("70.5"), ("Cement", "Site"): Decimal("17.75")}


def test_cannot_take_out_more_than_is_there(client, auth_a, stockyard):
    c, main, site = stockyard["cement"]["id"], stockyard["main"]["id"], stockyard["site"]["id"]
    move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "10"})

    res = move(client, auth_a, "stock-out", {"material_id": c, "warehouse_id": main, "quantity": "10.001"})
    assert res.status_code == 400 and "Insufficient stock" in res.json()["detail"]
    # Stock in another warehouse doesn't count towards this one.
    res = move(client, auth_a, "stock-out", {"material_id": c, "warehouse_id": site, "quantity": "1"})
    assert res.status_code == 400
    res = move(client, auth_a, "transfer", {"material_id": c, "from_warehouse_id": main, "to_warehouse_id": site, "quantity": "11"})
    assert res.status_code == 400
    # Taking out exactly what's there is fine, and leaves zero.
    assert move(client, auth_a, "stock-out", {"material_id": c, "warehouse_id": main, "quantity": "10"}).status_code == 201
    assert stock(client, auth_a) == {}


def test_transfer_is_two_linked_rows_and_conserves_stock(client, auth_a, stockyard):
    c, main, site = stockyard["cement"]["id"], stockyard["main"]["id"], stockyard["site"]["id"]
    move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "40"})
    rows = move(client, auth_a, "transfer", {"material_id": c, "from_warehouse_id": main, "to_warehouse_id": site, "quantity": "15"}).json()
    assert sorted(r["transaction_type"] for r in rows) == ["transfer_in", "transfer_out"]
    assert sum(stock(client, auth_a).values()) == 40

    res = move(client, auth_a, "transfer", {"material_id": c, "from_warehouse_id": main, "to_warehouse_id": main, "quantity": "1"})
    assert res.status_code == 400


@pytest.mark.parametrize("quantity", ["0", "-5"])
def test_quantities_must_be_positive(client, auth_a, stockyard, quantity):
    c, main = stockyard["cement"]["id"], stockyard["main"]["id"]
    res = move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": quantity})
    assert res.status_code == 422


def test_project_allocation_is_recorded_as_allocation(client, auth_a, stockyard):
    c, main = stockyard["cement"]["id"], stockyard["main"]["id"]
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "10"})
    tx = move(client, auth_a, "stock-out", {"material_id": c, "warehouse_id": main, "quantity": "4", "project_id": project["id"]}).json()
    assert tx["transaction_type"] == "allocation" and tx["project_id"] == project["id"]
    assert stock(client, auth_a) == {("Cement", "Main"): Decimal("6")}


def test_dashboard_counts_low_and_out_of_stock(client, auth_a, stockyard):
    main = stockyard["main"]["id"]
    sand = make(client, auth_a, "/materials", {"name": "Sand", "sku": "SND", "unit": "m3", "reorder_point": 5})
    make(client, auth_a, "/materials", {"name": "Lime", "sku": "LIM", "unit": "Bag"})  # never stocked
    move(client, auth_a, "stock-in", {"material_id": stockyard["cement"]["id"], "warehouse_id": main, "quantity": "20"})  # == reorder point
    move(client, auth_a, "stock-in", {"material_id": sand["id"], "warehouse_id": main, "quantity": "50"})

    dash = client.get("/api/v1/inventory/dashboard", headers=auth_a).json()
    assert dash == {"total_materials": 3, "low_stock_count": 1, "out_of_stock_count": 1, "warehouse_count": 2}


def test_transaction_history_newest_first_with_author(client, auth_a, stockyard):
    c, main = stockyard["cement"]["id"], stockyard["main"]["id"]
    move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "10", "reference": "GRN-1"})
    move(client, auth_a, "stock-out", {"material_id": c, "warehouse_id": main, "quantity": "3"})
    history = client.get("/api/v1/inventory/transactions", headers=auth_a).json()
    assert [h["transaction_type"] for h in history] == ["stock_out", "stock_in"]
    me = client.get("/api/v1/auth/me", headers=auth_a).json()["id"]
    assert {h["created_by_id"] for h in history} == {me}


def test_only_stock_roles_can_move_stock(client, auth_a, stockyard, viewer_a):
    c, main = stockyard["cement"]["id"], stockyard["main"]["id"]
    body = {"material_id": c, "warehouse_id": main, "quantity": "1"}
    assert move(client, viewer_a, "stock-in", body).status_code == 403
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    assert move(client, pm, "stock-in", body).status_code == 403
    keeper = make_user_in_company(client, auth_a, "store@example.com", "storekeeper")
    assert move(client, keeper, "stock-in", body).status_code == 201
    # Anyone in the company can look.
    assert client.get("/api/v1/inventory/stock", headers=viewer_a).status_code == 200


def test_cannot_touch_another_companys_stock(client, auth_a, auth_b, stockyard):
    c, main = stockyard["cement"]["id"], stockyard["main"]["id"]
    move(client, auth_a, "stock-in", {"material_id": c, "warehouse_id": main, "quantity": "10"})
    b_wh = make(client, auth_b, "/warehouses", {"name": "B Main"})
    # B can't take A's material out of anywhere, or put it into B's warehouse.
    assert move(client, auth_b, "stock-out", {"material_id": c, "warehouse_id": main, "quantity": "1"}).status_code == 404
    assert move(client, auth_b, "stock-in", {"material_id": c, "warehouse_id": b_wh["id"], "quantity": "1"}).status_code == 404
    assert stock(client, auth_b) == {}
    assert client.get("/api/v1/inventory/transactions", headers=auth_b).json() == []
    assert stock(client, auth_a) == {("Cement", "Main"): Decimal("10")}
