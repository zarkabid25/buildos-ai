from datetime import date, timedelta


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def health(client, headers, project):
    res = client.get(f"/api/v1/projects/{project['id']}/health", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def set_progress(client, headers, project, percent):
    res = client.patch(f"/api/v1/projects/{project['id']}", headers=headers, json={"progress_percent": percent})
    assert res.status_code == 200, res.text


def spend(client, headers, project, amount):
    make(client, headers, "/expenses", {
        "project_id": project["id"], "amount": amount, "expense_date": date.today().isoformat(),
    })


def test_no_data_means_no_scores(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    data = health(client, auth_a, project)
    assert data["overall_score"] is None
    assert data["cost_score"] is None and data["inventory_score"] is None
    assert data["basis"] == {}


def test_cost_score_hand_checked(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    set_progress(client, auth_a, project, 50)
    spend(client, auth_a, project, "600")  # forecast 600 / 50% = 1200 → 20% over → 100 - 40

    data = health(client, auth_a, project)
    assert data["cost_score"] == 60
    assert data["overall_score"] == 60  # the only scored dimension
    assert "20.0% over" in data["basis"]["cost"]


def test_under_budget_scores_full(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    set_progress(client, auth_a, project, 50)
    spend(client, auth_a, project, "300")
    assert health(client, auth_a, project)["cost_score"] == 100


def test_no_cost_score_before_progress(client, auth_a):
    # With 0% progress the forecast is just spend so far, not a projection.
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    spend(client, auth_a, project, "5000")
    assert health(client, auth_a, project)["cost_score"] is None


def test_inventory_score_from_boq_vs_actual(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    warehouse = make(client, auth_a, "/warehouses", {"name": "Main"})
    materials = [
        make(client, auth_a, "/materials", {"name": name, "sku": name[:3], "unit": "Bag"})
        for name in ("Cement", "Lime", "Grout", "Putty")
    ]
    for i, m in enumerate(materials):
        make(client, auth_a, "/inventory/stock-in", {"material_id": m["id"], "warehouse_id": warehouse["id"], "quantity": "100"})
        make(client, auth_a, f"/projects/{project['id']}/boq", {
            "item_code": str(i), "description": m["name"], "unit": "Bag", "quantity": "10", "material_id": m["id"],
        })
    # One of the four linked lines goes over plan.
    make(client, auth_a, "/inventory/stock-out", {
        "material_id": materials[0]["id"], "warehouse_id": warehouse["id"], "project_id": project["id"], "quantity": "15",
    })
    # Unlinked lines don't count either way.
    make(client, auth_a, f"/projects/{project['id']}/boq", {"item_code": "X", "description": "Misc", "unit": "LS"})

    data = health(client, auth_a, project)
    assert data["inventory_score"] == 75
    assert data["basis"]["inventory"].startswith("1 of 4")


def test_overall_is_average_of_available_scores(client, auth_a):
    today = date.today()
    project = make(client, auth_a, "/projects", {
        "name": "Tower", "code": "TWR", "budget": "1000",
        "start_date": (today - timedelta(days=50)).isoformat(),
        "end_date": (today + timedelta(days=50)).isoformat(),
    })
    set_progress(client, auth_a, project, 40)  # 50% elapsed → 10 behind → schedule 80
    spend(client, auth_a, project, "480")  # forecast 1200 → 20% over → cost 60

    data = health(client, auth_a, project)
    assert data["schedule_score"] == 80
    assert data["cost_score"] == 60
    assert data["overall_score"] == 70
    assert set(data["basis"]) == {"schedule", "cost"}


def test_health_is_tenant_isolated(client, auth_a, auth_b):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1000"})
    res = client.get(f"/api/v1/projects/{project['id']}/health", headers=auth_b)
    assert res.status_code == 404
