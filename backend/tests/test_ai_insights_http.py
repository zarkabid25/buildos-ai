from datetime import date, timedelta


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def insights(client, headers):
    res = client.get("/api/v1/ai/insights", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_empty_company_has_nothing_to_report(client, auth_a):
    report = insights(client, auth_a)
    assert report["insights"] == []
    assert report["summary"] == "Nothing needs attention right now."
    assert report["counts"]["total"] == 0


def test_insights_are_labelled_as_rules_not_ai(client, auth_a):
    assert insights(client, auth_a)["generated_by"] == "rules"


def test_flags_late_over_budget_project_low_stock_and_pending_approvals(client, auth_a):
    today = date.today()
    project = make(client, auth_a, "/projects", {
        "name": "Alpha Tower", "code": "ALPHA", "budget": "1000000",
        "start_date": str(today - timedelta(days=100)), "end_date": str(today + timedelta(days=100)),
    })
    # 50% of the schedule has elapsed but only 20% of the work is reported done
    client.patch(f"/api/v1/projects/{project['id']}", headers=auth_a, json={"status": "active", "progress_percent": 20})
    # 300k spent at 20% progress projects to 1.5M against a 1M budget
    make(client, auth_a, "/expenses", {"project_id": project["id"], "amount": "300000", "expense_date": str(today)})

    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag", "reorder_point": 50})
    wh = make(client, auth_a, "/warehouses", {"name": "Main"})
    make(client, auth_a, "/inventory/stock-in", {"material_id": cement["id"], "warehouse_id": wh["id"], "quantity": "100"})
    make(client, auth_a, "/inventory/stock-out", {"material_id": cement["id"], "warehouse_id": wh["id"], "quantity": "98"})

    supplier = make(client, auth_a, "/suppliers", {"name": "ABC"})
    make(client, auth_a, "/purchase-orders", {
        "supplier_id": supplier["id"],
        "items": [{"material_id": cement["id"], "quantity": "10", "rate": "100"}],
    })
    make(client, auth_a, "/material-requests", {
        "project_id": project["id"], "items": [{"material_id": cement["id"], "quantity": "5"}],
    })

    report = insights(client, auth_a)
    titles = [i["title"] for i in report["insights"]]

    assert any("Alpha Tower is behind schedule" in t for t in titles)
    assert any("Alpha Tower is forecast to overrun" in t for t in titles)
    assert any(t.startswith("Cement may run out") for t in titles)
    assert any("purchase order(s) awaiting approval" in t for t in titles)
    assert any("material request(s) not yet actioned" in t for t in titles)

    overrun = next(i for i in report["insights"] if "overrun" in i["title"])
    assert overrun["severity"] == "high"  # +50% is over the 10% threshold
    assert overrun["data"]["budget"] == "1000000.00"

    severities = [i["severity"] for i in report["insights"]]
    assert severities == sorted(severities, key=["high", "medium", "low"].index), "must be sorted most urgent first"
    assert report["counts"]["total"] == len(report["insights"])
    assert f"{report['counts']['total']} item(s) need attention" in report["summary"]


def test_cost_overrun_is_not_claimed_without_recorded_progress(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "New Job", "code": "NEW", "budget": "1000"})
    make(client, auth_a, "/expenses", {"project_id": project["id"], "amount": "5000", "expense_date": str(date.today())})
    # progress is 0%, so the "forecast" is just spend-so-far, not a projection
    assert not any("overrun" in i["title"] for i in insights(client, auth_a)["insights"])


def test_no_insight_for_a_healthy_project(client, auth_a):
    today = date.today()
    project = make(client, auth_a, "/projects", {
        "name": "Healthy", "code": "OK", "budget": "1000000",
        "start_date": str(today - timedelta(days=50)), "end_date": str(today + timedelta(days=50)),
    })
    client.patch(f"/api/v1/projects/{project['id']}", headers=auth_a, json={"status": "active", "progress_percent": 55})
    make(client, auth_a, "/expenses", {"project_id": project["id"], "amount": "400000", "expense_date": str(today)})
    assert insights(client, auth_a)["insights"] == []


def test_another_company_sees_none_of_it(client, auth_a, auth_b):
    make(client, auth_a, "/materials", {"name": "Steel", "sku": "STL", "unit": "Ton", "reorder_point": 10})
    assert len(insights(client, auth_a)["insights"]) == 1
    assert insights(client, auth_b)["insights"] == []


def test_insights_require_login(client):
    assert client.get("/api/v1/ai/insights").status_code == 401
