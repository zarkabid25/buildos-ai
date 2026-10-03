from datetime import timedelta
from decimal import Decimal


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


def setup(client, headers):
    supplier = make(client, headers, "/suppliers", {"name": "Acme Cement"})
    material = make(client, headers, "/materials", {"name": "Cement", "sku": "CEM-1", "unit": "Bag"})
    warehouse = make(client, headers, "/warehouses", {"name": "Main"})
    project = make(client, headers, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    return supplier, material, warehouse, project


def po(client, headers, supplier, material, quantity="100", rate="10", project=None, approve=True):
    body = {"supplier_id": supplier["id"], "items": [{"material_id": material["id"], "quantity": quantity, "rate": rate}]}
    if project:
        body["project_id"] = project["id"]
    order = make(client, headers, "/purchase-orders", body)
    if approve:
        order = make(client, headers, f"/purchase-orders/{order['id']}/approve", {})
    return order


def receive(client, headers, order, warehouse, quantity):
    return make(client, headers, f"/purchase-orders/{order['id']}/goods-receipts", {
        "warehouse_id": warehouse["id"],
        "items": [{"purchase_order_item_id": order["items"][0]["id"], "quantity_received": quantity}],
    })


def get(client, headers, supplier, what):
    res = client.get(f"/api/v1/suppliers/{supplier['id']}/{what}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def backdate_po(order_id, days):
    """Receipts happen seconds after the PO in a test; move the PO back to get a real lead time."""
    import uuid

    from app.db.session import SessionLocal
    from app.models.procurement import PurchaseOrder

    with SessionLocal() as db:
        row = db.get(PurchaseOrder, uuid.UUID(order_id))
        row.created_at = row.created_at - timedelta(days=days)
        db.commit()


def test_empty_supplier(client, auth_a):
    supplier, *_ = setup(client, auth_a)
    assert get(client, auth_a, supplier, "transactions") == []
    perf = get(client, auth_a, supplier, "performance")
    assert perf["po_count"] == 0
    assert perf["fulfilment_percent"] is None and perf["average_lead_time_days"] is None


def test_transactions_show_ordered_and_received(client, auth_a):
    supplier, material, warehouse, project = setup(client, auth_a)
    order = po(client, auth_a, supplier, material, project=project)
    receive(client, auth_a, order, warehouse, "30")
    receive(client, auth_a, order, warehouse, "20")

    [tx] = get(client, auth_a, supplier, "transactions")
    assert tx["po_number"] == order["po_number"]
    assert tx["project_name"] == "Tower"
    assert tx["status"] == "partially_received"
    assert Decimal(tx["ordered_amount"]) == 1000
    assert Decimal(tx["received_amount"]) == 500
    assert tx["receipt_count"] == 2 and tx["last_received_at"] is not None


def test_only_this_suppliers_pos(client, auth_a):
    supplier, material, *_ = setup(client, auth_a)
    other = make(client, auth_a, "/suppliers", {"name": "Other Supplier"})
    po(client, auth_a, other, material)
    assert get(client, auth_a, supplier, "transactions") == []
    assert get(client, auth_a, supplier, "performance")["po_count"] == 0


def test_performance_hand_checked(client, auth_a):
    supplier, material, warehouse, _ = setup(client, auth_a)
    full = po(client, auth_a, supplier, material, quantity="100", rate="10")  # 1000
    backdate_po(full["id"], 4)
    receive(client, auth_a, full, warehouse, "100")

    partial = po(client, auth_a, supplier, material, quantity="50", rate="20")  # 1000
    backdate_po(partial["id"], 2)
    receive(client, auth_a, partial, warehouse, "25")  # 500 received

    po(client, auth_a, supplier, material, quantity="10", rate="100")  # approved, 1000, nothing yet
    po(client, auth_a, supplier, material, quantity="999", rate="999", approve=False)  # pending: not committed

    perf = get(client, auth_a, supplier, "performance")
    assert perf["po_count"] == 4
    assert perf["committed_po_count"] == 3
    assert perf["fully_received_count"] == 1
    assert Decimal(perf["committed_amount"]) == 3000
    assert Decimal(perf["received_amount"]) == 1500
    assert Decimal(perf["fulfilment_percent"]) == Decimal("50.0")
    assert Decimal(perf["average_lead_time_days"]) == Decimal("3.0")  # (4 + 2) / 2


def test_other_company_cannot_see_supplier_history(client, auth_a, auth_b):
    supplier, material, *_ = setup(client, auth_a)
    po(client, auth_a, supplier, material)
    for what in ("transactions", "performance"):
        res = client.get(f"/api/v1/suppliers/{supplier['id']}/{what}", headers=auth_b)
        assert res.status_code == 404
