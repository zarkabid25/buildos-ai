"""BUILD-126: important changes leave an append-only trail that admins can read."""

from tests.conftest import make_user_in_company


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


def log(client, headers, **params):
    res = client.get("/api/v1/audit-log", headers=headers, params=params)
    assert res.status_code == 200, res.text
    return res.json()


def actions(client, headers):
    return [e["action"] for e in log(client, headers)]


def test_purchase_order_lifecycle_is_audited(client, auth_a):
    supplier = make(client, auth_a, "/suppliers", {"name": "Acme"})
    wh = make(client, auth_a, "/warehouses", {"name": "Main"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    po = make(client, auth_a, "/purchase-orders", {
        "supplier_id": supplier["id"], "items": [{"material_id": cement["id"], "quantity": "10", "rate": "100"}],
    })
    po = make(client, auth_a, f"/purchase-orders/{po['id']}/approve", {})
    make(client, auth_a, f"/purchase-orders/{po['id']}/goods-receipts", {
        "warehouse_id": wh["id"], "items": [{"purchase_order_item_id": po["items"][0]["id"], "quantity_received": "4"}],
    })

    entries = log(client, auth_a)
    assert [e["action"] for e in entries] == ["goods_receipt.created", "purchase_order.approved", "purchase_order.created"]
    approved = entries[1]
    assert approved["entity_id"] == po["id"]
    assert approved["actor_name"] == "Test Admin"
    assert approved["details"]["total"] == "1000.00"
    assert po["po_number"] in approved["summary"]


def test_failed_action_leaves_no_entry(client, auth_a):
    supplier = make(client, auth_a, "/suppliers", {"name": "Acme"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    po = make(client, auth_a, "/purchase-orders", {
        "supplier_id": supplier["id"], "items": [{"material_id": cement["id"], "quantity": "1", "rate": "1"}],
    })
    make(client, auth_a, f"/purchase-orders/{po['id']}/approve", {})
    # Approving twice is refused, and must not be logged as if it happened.
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=auth_a).status_code == 400
    assert actions(client, auth_a).count("purchase_order.approved") == 1


def test_user_and_settings_changes_are_audited(client, auth_a, viewer_a):
    viewer_id = client.get("/api/v1/auth/me", headers=viewer_a).json()["id"]
    client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"role": "site_engineer"})
    client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"is_active": False})
    client.patch("/api/v1/companies/me", headers=auth_a, json={"currency": "USD", "name": "Company AAA"})

    entries = log(client, auth_a)
    assert [e["action"] for e in entries] == ["company.settings_updated", "user.deactivated", "user.role_changed"]
    assert entries[2]["details"] == {"from": "viewer", "to": "site_engineer"}
    # Only fields that actually changed are recorded (the name was already "Company AAA").
    assert entries[0]["details"] == {"currency": {"from": "PKR", "to": "USD"}}


def test_no_op_changes_are_not_logged(client, auth_a, viewer_a):
    viewer_id = client.get("/api/v1/auth/me", headers=viewer_a).json()["id"]
    client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"role": "viewer"})
    client.patch("/api/v1/companies/me", headers=auth_a, json={"currency": "PKR"})
    assert log(client, auth_a) == []


def test_deletions_and_expenses_are_audited(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    item = make(client, auth_a, f"/projects/{project['id']}/boq",
                {"item_code": "001", "description": "Cement", "unit": "Bag", "quantity": "2", "rate": "5"})
    assert client.delete(f"/api/v1/projects/{project['id']}/boq/{item['id']}", headers=auth_a).status_code == 204
    make(client, auth_a, "/expenses", {"project_id": project["id"], "amount": "250", "expense_date": "2026-05-01"})

    entries = log(client, auth_a)
    assert [e["action"] for e in entries] == ["expense.created", "boq_item.deleted"]
    assert "Cement" in entries[1]["summary"] and "10.00" in entries[1]["summary"]
    assert log(client, auth_a, entity_type="boq_item")[0]["entity_id"] == item["id"]


def test_only_admins_can_read_and_only_their_company(client, auth_a, auth_b, viewer_a):
    make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    make(client, auth_a, "/expenses", {
        "project_id": client.get("/api/v1/projects", headers=auth_a).json()[0]["id"],
        "amount": "1", "expense_date": "2026-05-01",
    })
    assert client.get("/api/v1/audit-log", headers=viewer_a).status_code == 403
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    assert client.get("/api/v1/audit-log", headers=pm).status_code == 403
    assert log(client, auth_b) == []
    assert len(log(client, auth_a)) == 1


def test_log_cannot_be_edited_or_deleted_through_the_api(client):
    paths = client.get("/openapi.json").json()["paths"]
    audit_ops = {m.upper() for p, ops in paths.items() if p.startswith("/api/v1/audit-log") for m in ops}
    assert audit_ops == {"GET"}
