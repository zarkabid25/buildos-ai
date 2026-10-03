"""BUILD-132 (projects) and the cost calculations behind them (CLAUDE.md rule 15)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from tests.conftest import make_user_in_company


def make(client, headers, path, body=None):
    res = client.post(f"/api/v1{path}", headers=headers, json=body or {})
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


def project(client, headers, **extra):
    body = {"name": "Tower", "code": "TWR", "budget": "1000", **extra}
    return make(client, headers, "/projects", body)


def cost(client, headers, p):
    res = client.get(f"/api/v1/projects/{p['id']}/cost-summary", headers=headers)
    assert res.status_code == 200, res.text
    return {k: (Decimal(v) if k != "forecast_basis" else v) for k, v in res.json().items()}


# ---- CRUD and validation ---------------------------------------------------------


def test_create_read_update(client, auth_a):
    p = project(client, auth_a, client_name="Acme", start_date="2026-01-01", end_date="2026-12-31")
    assert (p["status"], p["progress_percent"]) == ("planning", 0)
    res = client.patch(f"/api/v1/projects/{p['id']}", headers=auth_a, json={"status": "active", "progress_percent": 40})
    assert res.status_code == 200 and (res.json()["status"], res.json()["progress_percent"]) == ("active", 40)
    assert client.get(f"/api/v1/projects/{p['id']}", headers=auth_a).json()["client_name"] == "Acme"


@pytest.mark.parametrize("body", [
    {"progress_percent": 101},
    {"progress_percent": -1},
    {"budget": "-1"},
    {"status": "finished"},
])
def test_update_validation(client, auth_a, body):
    p = project(client, auth_a)
    assert client.patch(f"/api/v1/projects/{p['id']}", headers=auth_a, json=body).status_code == 422


def test_negative_budget_rejected_on_create(client, auth_a):
    res = client.post("/api/v1/projects", headers=auth_a, json={"name": "T", "code": "T", "budget": "-5"})
    assert res.status_code == 422


def test_end_date_cannot_be_before_start(client, auth_a):
    res = client.post("/api/v1/projects", headers=auth_a, json={
        "name": "T", "code": "T", "budget": "1", "start_date": "2026-06-01", "end_date": "2026-05-01",
    })
    assert res.status_code == 422
    p = project(client, auth_a, start_date="2026-01-01", end_date="2026-12-31")
    res = client.patch(f"/api/v1/projects/{p['id']}", headers=auth_a, json={"end_date": "2025-12-31"})
    assert res.status_code == 422


def test_roles(client, auth_a, viewer_a):
    assert client.post("/api/v1/projects", headers=viewer_a, json={"name": "T", "code": "T", "budget": "1"}).status_code == 403
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    p = project(client, pm)
    # A PM can run projects but deleting one is admin-only.
    assert client.delete(f"/api/v1/projects/{p['id']}", headers=pm).status_code == 403
    assert client.delete(f"/api/v1/projects/{p['id']}", headers=auth_a).status_code == 204


def test_project_with_records_cannot_be_deleted(client, auth_a):
    p = project(client, auth_a)
    make(client, auth_a, "/expenses", {"project_id": p["id"], "amount": "10", "expense_date": "2026-05-01"})
    res = client.delete(f"/api/v1/projects/{p['id']}", headers=auth_a)
    assert res.status_code == 409
    assert "expenses" in res.json()["detail"]
    assert client.get(f"/api/v1/projects/{p['id']}", headers=auth_a).status_code == 200


def test_tenant_isolation(client, auth_a, auth_b):
    p = project(client, auth_a)
    assert client.get(f"/api/v1/projects/{p['id']}", headers=auth_b).status_code == 404
    assert client.patch(f"/api/v1/projects/{p['id']}", headers=auth_b, json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/v1/projects/{p['id']}", headers=auth_b).status_code == 404
    assert client.get(f"/api/v1/projects/{p['id']}/cost-summary", headers=auth_b).status_code == 404
    assert client.get("/api/v1/projects", headers=auth_b).json() == []


# ---- Portfolio summary -------------------------------------------------------------


def test_summary(client, auth_a):
    today = date.today()
    behind = project(client, auth_a, code="A", budget="1000",
                     start_date=str(today - timedelta(days=50)), end_date=str(today + timedelta(days=50)))
    client.patch(f"/api/v1/projects/{behind['id']}", headers=auth_a, json={"status": "active", "progress_percent": 20})
    on_track = project(client, auth_a, code="B", budget="500",
                       start_date=str(today - timedelta(days=50)), end_date=str(today + timedelta(days=50)))
    client.patch(f"/api/v1/projects/{on_track['id']}", headers=auth_a, json={"status": "active", "progress_percent": 45})
    # Behind schedule but not active (on hold): not counted as at risk.
    paused = project(client, auth_a, code="C", budget="0",
                     start_date=str(today - timedelta(days=50)), end_date=str(today + timedelta(days=50)))
    client.patch(f"/api/v1/projects/{paused['id']}", headers=auth_a, json={"status": "on_hold", "progress_percent": 10})

    s = client.get("/api/v1/projects/summary", headers=auth_a).json()
    assert s["total_projects"] == 3
    assert Decimal(s["total_budget"]) == 1500
    assert s["avg_progress"] == 25.0  # (20 + 45 + 10) / 3
    assert s["at_risk_count"] == 1  # 50% elapsed vs 20% done is 30 points behind (> 15); 45% is 5 behind


# ---- Cost calculations ---------------------------------------------------------------


def test_cost_summary_before_any_progress(client, auth_a):
    p = project(client, auth_a, budget="1000")
    make(client, auth_a, "/expenses", {"project_id": p["id"], "amount": "150", "expense_date": "2026-05-01"})
    c = cost(client, auth_a, p)
    assert (c["actual"], c["committed"], c["remaining"]) == (150, 0, 850)
    # No progress: the forecast is just what's spent, not an extrapolation.
    assert c["forecast"] == 150 and c["expected_variance"] == -850
    assert "not a real projection" in c["forecast_basis"]


def test_cost_summary_projection_and_commitments(client, auth_a):
    p = project(client, auth_a, budget="10000")
    client.patch(f"/api/v1/projects/{p['id']}", headers=auth_a, json={"progress_percent": 25})
    for amount in ("1000", "1500.50"):
        make(client, auth_a, "/expenses", {"project_id": p["id"], "amount": amount, "expense_date": "2026-05-01"})
    supplier = make(client, auth_a, "/suppliers", {"name": "Acme"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    make(client, auth_a, "/purchase-orders", {
        "supplier_id": supplier["id"], "project_id": p["id"],
        "items": [{"material_id": cement["id"], "quantity": "10", "rate": "120"}],
    })
    # A PO for no project doesn't count against this one.
    make(client, auth_a, "/purchase-orders", {
        "supplier_id": supplier["id"], "items": [{"material_id": cement["id"], "quantity": "999", "rate": "1"}],
    })

    c = cost(client, auth_a, p)
    assert c["actual"] == Decimal("2500.50")
    assert c["committed"] == 1200
    assert c["remaining"] == Decimal("6299.50")  # 10000 - 1200 - 2500.50
    assert c["forecast"] == Decimal("10002")  # 2500.50 / 25 * 100
    assert c["expected_variance"] == 2  # just over budget


def test_expenses_on_other_projects_dont_leak_in(client, auth_a):
    a = project(client, auth_a, code="A")
    b = project(client, auth_a, code="B")
    make(client, auth_a, "/expenses", {"project_id": b["id"], "amount": "999", "expense_date": "2026-05-01"})
    assert cost(client, auth_a, a)["actual"] == 0


@pytest.mark.parametrize("amount", ["0", "-10"])
def test_expense_amount_must_be_positive(client, auth_a, amount):
    p = project(client, auth_a)
    res = client.post("/api/v1/expenses", headers=auth_a, json={"project_id": p["id"], "amount": amount, "expense_date": "2026-05-01"})
    assert res.status_code == 422
