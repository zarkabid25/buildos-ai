import csv
import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


def report(client, headers, kind, **params):
    res = client.get(f"/api/v1/reports/{kind}", headers=headers, params=params)
    assert res.status_code == 200, res.text
    return res.json()


def backdate(model_name, row_id, when: datetime):
    import uuid

    from app.db.session import SessionLocal
    from app.models import inventory_transaction, procurement

    model = {
        "tx": inventory_transaction.InventoryTransaction,
        "po": procurement.PurchaseOrder,
    }[model_name]
    with SessionLocal() as db:
        row = db.get(model, uuid.UUID(row_id))
        row.created_at = when
        db.commit()


# ---- Project report (BUILD-108) ---------------------------------------------


def test_project_report_matches_cost_summary(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    client.patch(f"/api/v1/projects/{project['id']}", headers=auth_a, json={"progress_percent": 50})
    make(client, auth_a, "/expenses", {"project_id": project["id"], "amount": "600", "expense_date": date.today().isoformat()})
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Late", "due_date": (date.today() - timedelta(days=1)).isoformat()})
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Open"})

    data = report(client, auth_a, "projects")
    [row] = data["rows"]
    cost = client.get(f"/api/v1/projects/{project['id']}/cost-summary", headers=auth_a).json()
    for field in ("committed", "actual", "forecast", "expected_variance"):
        assert Decimal(row[field]) == Decimal(cost[field]), field
    assert Decimal(row["forecast"]) == 1200
    assert row["health_score"] == 60  # cost score only
    assert (row["open_tasks"], row["overdue_tasks"]) == (2, 1)
    assert Decimal(data["total_budget"]) == 1000 and Decimal(data["total_actual"]) == 600


# ---- Inventory report (BUILD-109) -------------------------------------------


def test_inventory_report_balances_and_movements(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    main = make(client, auth_a, "/warehouses", {"name": "Main"})
    site = make(client, auth_a, "/warehouses", {"name": "Site"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag", "reorder_point": 50})
    sand = make(client, auth_a, "/materials", {"name": "Sand", "sku": "SND", "unit": "m3"})

    make(client, auth_a, "/inventory/stock-in", {"material_id": cement["id"], "warehouse_id": main["id"], "quantity": "100"})
    make(client, auth_a, "/inventory/transfer", {"material_id": cement["id"], "from_warehouse_id": main["id"], "to_warehouse_id": site["id"], "quantity": "30"})
    make(client, auth_a, "/inventory/stock-out", {"material_id": cement["id"], "warehouse_id": site["id"], "project_id": project["id"], "quantity": "20"})
    make(client, auth_a, "/inventory/stock-out", {"material_id": cement["id"], "warehouse_id": main["id"], "quantity": "40"})

    data = report(client, auth_a, "inventory")
    rows = {r["name"]: r for r in data["rows"]}
    assert Decimal(rows["Cement"]["on_hand"]) == 40
    assert Decimal(rows["Cement"]["received"]) == 100  # the transfer isn't counted as received
    assert Decimal(rows["Cement"]["issued"]) == 60  # 20 allocated + 40 stocked out
    assert rows["Cement"]["stock_status"] == "low"  # 40 <= reorder point 50
    assert rows["Sand"]["stock_status"] == "out"
    assert (data["low_stock_count"], data["out_of_stock_count"]) == (1, 1)


def test_inventory_report_period_filters_movements_not_balance(client, auth_a):
    wh = make(client, auth_a, "/warehouses", {"name": "Main"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    old = make(client, auth_a, "/inventory/stock-in", {"material_id": cement["id"], "warehouse_id": wh["id"], "quantity": "70"})
    make(client, auth_a, "/inventory/stock-in", {"material_id": cement["id"], "warehouse_id": wh["id"], "quantity": "5"})
    backdate("tx", old["id"], datetime(2026, 1, 15, 23, 30, tzinfo=timezone.utc))

    jan = report(client, auth_a, "inventory", date_from="2026-01-15", date_to="2026-01-15")["rows"][0]
    assert Decimal(jan["received"]) == 70  # 23:30 UTC on the last day is still inside
    assert Decimal(jan["on_hand"]) == 75  # the balance is always current

    feb = report(client, auth_a, "inventory", date_from="2026-01-16", date_to="2026-02-28")["rows"][0]
    assert Decimal(feb["received"]) == 0


# ---- Procurement report (BUILD-110) -----------------------------------------


def test_procurement_report(client, auth_a):
    acme = make(client, auth_a, "/suppliers", {"name": "Acme"})
    beta = make(client, auth_a, "/suppliers", {"name": "Beta"})
    wh = make(client, auth_a, "/warehouses", {"name": "Main"})
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    item = lambda qty, rate: [{"material_id": cement["id"], "quantity": qty, "rate": rate}]

    po1 = make(client, auth_a, "/purchase-orders", {"supplier_id": acme["id"], "items": item("100", "10")})
    po1 = make(client, auth_a, f"/purchase-orders/{po1['id']}/approve", {})
    make(client, auth_a, f"/purchase-orders/{po1['id']}/goods-receipts", {
        "warehouse_id": wh["id"], "items": [{"purchase_order_item_id": po1["items"][0]["id"], "quantity_received": "40"}],
    })
    make(client, auth_a, "/purchase-orders", {"supplier_id": beta["id"], "items": item("10", "5")})
    make(client, auth_a, "/material-requests", {"project_id": project["id"], "items": [{"material_id": cement["id"], "quantity": "5"}]})

    data = report(client, auth_a, "procurement")
    assert data["po_count_by_status"] == {"partially_received": 1, "pending_approval": 1}
    assert Decimal(data["po_value_by_status"]["partially_received"]) == 1000
    assert data["material_requests_by_status"] == {"pending": 1}
    assert [(r["supplier_name"], Decimal(r["ordered_amount"]), Decimal(r["received_amount"])) for r in data["rows"]] == [
        ("Acme", 1000, 400), ("Beta", 50, 0),
    ]


def test_procurement_report_period(client, auth_a):
    acme = make(client, auth_a, "/suppliers", {"name": "Acme"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    po = make(client, auth_a, "/purchase-orders", {"supplier_id": acme["id"], "items": [{"material_id": cement["id"], "quantity": "1", "rate": "1"}]})
    backdate("po", po["id"], datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc))
    assert report(client, auth_a, "procurement", date_from="2026-03-01", date_to="2026-03-01")["rows"] != []
    assert report(client, auth_a, "procurement", date_to="2026-02-28")["rows"] == []


# ---- Expense report (BUILD-111) ---------------------------------------------


def test_expense_report_groups_and_filters_by_expense_date(client, auth_a):
    tower = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    villa = make(client, auth_a, "/projects", {"name": "Villa", "code": "VIL", "budget": "1"})
    fuel = make(client, auth_a, "/expense-categories", {"name": "Fuel"})
    add = lambda p, amt, day, cat=None: make(client, auth_a, "/expenses", {
        "project_id": p["id"], "amount": amt, "expense_date": day, **({"category_id": cat["id"]} if cat else {}),
    })
    add(tower, "100", "2026-05-01", fuel)
    add(tower, "50", "2026-05-20", fuel)
    add(tower, "30", "2026-05-20")
    add(villa, "200", "2026-06-01", fuel)

    data = report(client, auth_a, "expenses", date_from="2026-05-01", date_to="2026-05-31")
    assert [(r["project_name"], r["category"], r["expense_count"], Decimal(r["amount"])) for r in data["rows"]] == [
        ("Tower", "Fuel", 2, 150), ("Tower", "Uncategorized", 1, 30),
    ]
    assert Decimal(data["total_amount"]) == 180
    assert {k: Decimal(v) for k, v in data["by_category"].items()} == {"Fuel": 150, "Uncategorized": 30}
    assert Decimal(report(client, auth_a, "expenses")["total_amount"]) == 380


def test_bad_period_rejected(client, auth_a):
    for kind in ("inventory", "procurement", "expenses"):
        res = client.get(f"/api/v1/reports/{kind}", headers=auth_a, params={"date_from": "2026-02-01", "date_to": "2026-01-01"})
        assert res.status_code == 400


# ---- CSV and isolation --------------------------------------------------------


def test_csv_export(client, auth_a):
    tower = make(client, auth_a, "/projects", {"name": "Tower, Phase 1", "code": "TWR", "budget": "1"})
    make(client, auth_a, "/expenses", {"project_id": tower["id"], "amount": "12.50", "expense_date": "2026-05-01"})
    res = client.get("/api/v1/reports/expenses", headers=auth_a, params={"format": "csv"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(res.text)))
    assert rows[0]["project_name"] == "Tower, Phase 1"  # the comma is quoted, not split
    assert Decimal(rows[0]["amount"]) == Decimal("12.50")
    assert client.get("/api/v1/reports/expenses", headers=auth_a, params={"format": "xml"}).status_code == 422


def test_reports_are_tenant_isolated(client, auth_a, auth_b):
    project = make(client, auth_a, "/projects", {"name": "Secret", "code": "SEC", "budget": "999"})
    make(client, auth_a, "/expenses", {"project_id": project["id"], "amount": "5", "expense_date": "2026-05-01"})
    make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    supplier = make(client, auth_a, "/suppliers", {"name": "Acme"})
    cement = client.get("/api/v1/materials", headers=auth_a).json()[0]
    make(client, auth_a, "/purchase-orders", {"supplier_id": supplier["id"], "items": [{"material_id": cement["id"], "quantity": "1", "rate": "1"}]})

    assert report(client, auth_b, "projects")["rows"] == []
    assert report(client, auth_b, "inventory")["rows"] == []
    assert report(client, auth_b, "procurement")["rows"] == []
    assert report(client, auth_b, "expenses")["rows"] == []
