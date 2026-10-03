"""BUILD-122: an ID sent in a request body must belong to the caller's company.
Each of these was accepted before (Day 21 audit)."""

from tests.conftest import make_user_in_company


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def me(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()


def notifications(client, headers):
    return client.get("/api/v1/notifications", headers=headers).json()


def test_cannot_assign_task_to_another_companys_user(client, auth_a, auth_b):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    foreigner = me(client, auth_b)["id"]

    res = client.post(f"/api/v1/projects/{project['id']}/tasks", headers=auth_a,
                      json={"title": "Secret task", "assignee_id": foreigner})
    assert res.status_code == 404
    task = make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Secret task"})
    res = client.patch(f"/api/v1/projects/{project['id']}/tasks/{task['id']}", headers=auth_a,
                       json={"assignee_id": foreigner})
    assert res.status_code == 404
    # And nothing about the task reached the other company.
    assert notifications(client, auth_b) == []


def test_can_still_assign_task_to_a_colleague(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    task = make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Pour", "assignee_id": me(client, pm)["id"]})
    assert task["assignee_id"] == me(client, pm)["id"]


def test_expense_category_must_be_own(client, auth_a, auth_b):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    foreign = make(client, auth_b, "/expense-categories", {"name": "B-only category"})
    res = client.post("/api/v1/expenses", headers=auth_a, json={
        "project_id": project["id"], "category_id": foreign["id"], "amount": "5", "expense_date": "2026-05-01",
    })
    assert res.status_code == 404
    own = make(client, auth_a, "/expense-categories", {"name": "Fuel"})
    make(client, auth_a, "/expenses", {
        "project_id": project["id"], "category_id": own["id"], "amount": "5", "expense_date": "2026-05-01",
    })


def test_material_category_must_be_own(client, auth_a, auth_b):
    foreign = make(client, auth_b, "/material-categories", {"name": "B-only"})
    res = client.post("/api/v1/materials", headers=auth_a,
                      json={"name": "Cement", "sku": "CEM", "unit": "Bag", "category_id": foreign["id"]})
    assert res.status_code == 404
    material = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    res = client.patch(f"/api/v1/materials/{material['id']}", headers=auth_a, json={"category_id": foreign["id"]})
    assert res.status_code == 404


def test_equipment_project_must_be_own(client, auth_a, auth_b):
    foreign = make(client, auth_b, "/projects", {"name": "B Tower", "code": "BT", "budget": "1"})
    eq = make(client, auth_a, "/equipment", {"name": "Excavator"})
    res = client.patch(f"/api/v1/equipment/{eq['id']}", headers=auth_a, json={"current_project_id": foreign["id"]})
    assert res.status_code == 404
