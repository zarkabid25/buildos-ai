"""BUILD-054: supplier payments against POs, client receipts, and the cash summary."""

from decimal import Decimal

import pytest

from tests.conftest import make_user_in_company


def make(client, headers, path, body=None):
    res = client.post(f"/api/v1{path}", headers=headers, json=body or {})
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


@pytest.fixture
def s(client, auth_a):
    supplier = make(client, auth_a, "/suppliers", {"name": "Acme"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    return {"supplier": supplier, "cement": cement, "project": project}


def po(client, headers, s, quantity="100", rate="10", approve=True, **extra):
    order = make(client, headers, "/purchase-orders", {
        "supplier_id": s["supplier"]["id"], "items": [{"material_id": s["cement"]["id"], "quantity": quantity, "rate": rate}], **extra,
    })
    return make(client, headers, f"/purchase-orders/{order['id']}/approve") if approve else order


def pay(client, headers, order, amount, method="bank_transfer"):
    return client.post("/api/v1/payments/supplier", headers=headers, json={
        "purchase_order_id": order["id"], "amount": amount, "paid_on": "2026-10-01", "method": method,
    })


def get_po(client, headers, order):
    return client.get(f"/api/v1/purchase-orders/{order['id']}", headers=headers).json()


def test_payment_status_follows_payments(client, auth_a, s):
    order = po(client, auth_a, s)  # 1000
    assert get_po(client, auth_a, order)["payment_status"] == "unpaid"
    assert pay(client, auth_a, order, "400").status_code == 201
    after = get_po(client, auth_a, order)
    assert (after["payment_status"], Decimal(after["amount_paid"])) == ("partially_paid", 400)
    assert pay(client, auth_a, order, "600.00").status_code == 201
    assert get_po(client, auth_a, order)["payment_status"] == "paid"


def test_cannot_overpay(client, auth_a, s):
    order = po(client, auth_a, s, quantity="3", rate="33.33")  # 99.99
    assert pay(client, auth_a, order, "50").status_code == 201
    res = pay(client, auth_a, order, "50")
    assert res.status_code == 400 and "49.99" in res.json()["detail"]
    assert pay(client, auth_a, order, "49.99").status_code == 201
    assert pay(client, auth_a, order, "0.01").status_code == 400


def test_only_approved_pos_can_be_paid(client, auth_a, s):
    pending = po(client, auth_a, s, approve=False)
    res = pay(client, auth_a, pending, "1")
    assert res.status_code == 400 and "pending approval" in res.json()["detail"]


@pytest.mark.parametrize("amount", ["0", "-5", "1.001"])
def test_amount_validation(client, auth_a, s, amount):
    assert pay(client, auth_a, po(client, auth_a, s), amount).status_code == 422


def test_cash_summary_hand_checked(client, auth_a, s):
    villa = make(client, auth_a, "/projects", {"name": "Villa", "code": "VIL", "budget": "1"})
    tower_po = po(client, auth_a, s, quantity="100", rate="10", project_id=s["project"]["id"])  # 1000
    villa_po = po(client, auth_a, s, quantity="50", rate="10", project_id=villa["id"])  # 500
    po(client, auth_a, s, quantity="999", rate="1", approve=False)  # pending: not owed yet
    pay(client, auth_a, tower_po, "600")
    pay(client, auth_a, villa_po, "500")
    make(client, auth_a, "/payments/client", {
        "project_id": s["project"]["id"], "amount": "2500", "received_on": "2026-10-02", "method": "cheque",
    })

    summary = client.get("/api/v1/payments/summary", headers=auth_a).json()
    assert Decimal(summary["total_received"]) == 2500
    assert Decimal(summary["total_paid_out"]) == 1100
    assert Decimal(summary["net"]) == 1400
    assert Decimal(summary["total_outstanding"]) == 400
    projects = {p["project_name"]: (Decimal(p["received"]), Decimal(p["paid_out"]), Decimal(p["net"])) for p in summary["projects"]}
    assert projects == {"Tower": (2500, 600, 1900), "Villa": (0, 500, -500)}
    [payable] = summary["payables"]
    assert (Decimal(payable["committed"]), Decimal(payable["paid"]), Decimal(payable["outstanding"])) == (1500, 1100, 400)


def test_lists_and_audit(client, auth_a, s):
    order = po(client, auth_a, s)
    pay(client, auth_a, order, "250", method="cash")
    make(client, auth_a, "/payments/client", {
        "project_id": s["project"]["id"], "amount": "99", "received_on": "2026-10-02", "method": "bank_transfer", "reference": "INV-7",
    })
    [p] = client.get("/api/v1/payments/supplier", headers=auth_a).json()
    assert (p["po_number"], p["supplier_name"], Decimal(p["amount"]), p["method"]) == ("PO-1001", "Acme", 250, "cash")
    [r] = client.get(f"/api/v1/payments/client?project_id={s['project']['id']}", headers=auth_a).json()
    assert (r["project_name"], r["reference"]) == ("Tower", "INV-7")
    actions = [e["action"] for e in client.get("/api/v1/audit-log", headers=auth_a).json()]
    assert "payment.supplier" in actions and "payment.client_receipt" in actions


def test_only_finance_roles_record(client, auth_a, s, viewer_a):
    order = po(client, auth_a, s)
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    assert pay(client, pm, order, "1").status_code == 403
    assert pay(client, viewer_a, order, "1").status_code == 403
    accountant = make_user_in_company(client, auth_a, "acc@example.com", "accountant")
    assert pay(client, accountant, order, "1").status_code == 201
    assert client.get("/api/v1/payments/summary", headers=viewer_a).status_code == 200


def test_tenant_isolation(client, auth_a, auth_b, s):
    order = po(client, auth_a, s)
    pay(client, auth_a, order, "10")
    assert pay(client, auth_b, order, "1").status_code == 404
    assert client.post("/api/v1/payments/client", headers=auth_b, json={
        "project_id": s["project"]["id"], "amount": "1", "received_on": "2026-10-02", "method": "cash",
    }).status_code == 404
    assert client.get("/api/v1/payments/supplier", headers=auth_b).json() == []
    summary = client.get("/api/v1/payments/summary", headers=auth_b).json()
    assert summary["projects"] == [] and summary["payables"] == []


def test_paid_po_project_cannot_be_deleted(client, auth_a, s):
    make(client, auth_a, "/payments/client", {
        "project_id": s["project"]["id"], "amount": "1", "received_on": "2026-10-02", "method": "cash",
    })
    res = client.delete(f"/api/v1/projects/{s['project']['id']}", headers=auth_a)
    assert res.status_code == 409 and "client receipts" in res.json()["detail"]
