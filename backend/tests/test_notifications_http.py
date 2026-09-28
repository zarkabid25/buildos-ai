from tests.conftest import make_user_in_company


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def notifications(client, headers, unread_only=False):
    q = "?unread_only=true" if unread_only else ""
    res = client.get(f"/api/v1/notifications{q}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def unread_count(client, headers):
    return client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread_count"]


# ---- task assignment ----------------------------------------------------------


def test_assigning_a_task_notifies_the_assignee(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]

    task = make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Pour foundation", "assignee_id": pm_id})

    notes = notifications(client, pm)
    assert len(notes) == 1
    assert notes[0]["notification_type"] == "task_assigned"
    assert "Pour foundation" in notes[0]["title"]
    assert notes[0]["link"] == f"/projects/{project['id']}"
    assert unread_count(client, pm) == 1
    assert notifications(client, auth_a) == []  # the assigner isn't notified of their own action


def test_self_assignment_does_not_self_notify(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    me = client.get("/api/v1/auth/me", headers=auth_a).json()["id"]
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "My own task", "assignee_id": me})
    assert notifications(client, auth_a) == []


def test_self_assigning_via_update_does_not_self_notify(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    me = client.get("/api/v1/auth/me", headers=auth_a).json()["id"]
    task = make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Task"})
    client.patch(f"/api/v1/projects/{project['id']}/tasks/{task['id']}", headers=auth_a, json={"assignee_id": me})
    assert notifications(client, auth_a) == []


def test_reassigning_a_task_notifies_the_new_assignee_only(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm1 = make_user_in_company(client, auth_a, "pm1@example.com", "project_manager")
    pm2 = make_user_in_company(client, auth_a, "pm2@example.com", "project_manager")
    pm1_id = client.get("/api/v1/auth/me", headers=pm1).json()["id"]
    pm2_id = client.get("/api/v1/auth/me", headers=pm2).json()["id"]

    task = make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Task"})
    client.patch(f"/api/v1/projects/{project['id']}/tasks/{task['id']}", headers=auth_a, json={"assignee_id": pm1_id})
    assert len(notifications(client, pm1)) == 1

    client.patch(f"/api/v1/projects/{project['id']}/tasks/{task['id']}", headers=auth_a, json={"assignee_id": pm2_id})
    assert len(notifications(client, pm2)) == 1
    assert len(notifications(client, pm1)) == 1  # unchanged, no duplicate on reassignment


def test_updating_unrelated_fields_does_not_renotify(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]
    task = make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Task", "assignee_id": pm_id})
    assert len(notifications(client, pm)) == 1

    client.patch(f"/api/v1/projects/{project['id']}/tasks/{task['id']}", headers=auth_a, json={"status": "in_progress"})
    assert len(notifications(client, pm)) == 1  # still just the original


# ---- procurement ---------------------------------------------------------------


def test_material_request_notifies_approvers_not_the_requester(client, auth_a):
    admin_id = client.get("/api/v1/auth/me", headers=auth_a).json()["id"]
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    storekeeper = make_user_in_company(client, auth_a, "store@example.com", "storekeeper")

    project = make(client, pm, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    material = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    make(client, pm, "/material-requests", {"project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "10"}]})

    assert len(notifications(client, auth_a)) == 1  # company admin can approve
    assert notifications(client, pm) == []  # the requester, excluded
    assert notifications(client, storekeeper) == []  # storekeeper isn't an approver


def test_purchase_order_notifies_approvers_not_the_creator(client, auth_a):
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    material = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    supplier = make(client, auth_a, "/suppliers", {"name": "ABC"})

    make(client, pm, "/purchase-orders", {
        "supplier_id": supplier["id"], "items": [{"material_id": material["id"], "quantity": "10", "rate": "100"}],
    })

    admin_notes = notifications(client, auth_a)
    assert len(admin_notes) == 1
    assert "needs approval" in admin_notes[0]["title"]
    assert notifications(client, pm) == []


# ---- notification management ---------------------------------------------------


def test_mark_read_and_unread_count(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "A", "assignee_id": pm_id})
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "B", "assignee_id": pm_id})

    assert unread_count(client, pm) == 2
    note_id = notifications(client, pm)[0]["id"]

    res = client.post(f"/api/v1/notifications/{note_id}/read", headers=pm)
    assert res.status_code == 200 and res.json()["is_read"] is True
    assert unread_count(client, pm) == 1
    assert len(notifications(client, pm, unread_only=True)) == 1


def test_mark_all_read(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]
    for i in range(3):
        make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": f"T{i}", "assignee_id": pm_id})

    assert unread_count(client, pm) == 3
    res = client.post("/api/v1/notifications/read-all", headers=pm)
    assert res.status_code == 200 and res.json()["unread_count"] == 0
    assert unread_count(client, pm) == 0
    assert notifications(client, pm, unread_only=True) == []


def test_cannot_mark_someone_elses_notification_read(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "A", "assignee_id": pm_id})
    note_id = notifications(client, pm)[0]["id"]

    res = client.post(f"/api/v1/notifications/{note_id}/read", headers=auth_a)
    assert res.status_code == 404
    assert unread_count(client, pm) == 1  # untouched


def test_another_company_sees_nothing(client, auth_a, auth_b):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "A", "assignee_id": pm_id})

    assert notifications(client, auth_b) == []
    assert unread_count(client, auth_b) == 0


def test_notifications_require_login(client):
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.get("/api/v1/notifications/unread-count").status_code == 401
