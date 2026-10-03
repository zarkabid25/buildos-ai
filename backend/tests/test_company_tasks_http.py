"""The company-wide task list behind the sidebar Tasks page."""

from tests.conftest import make_user_in_company


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def tasks(client, headers, **params):
    res = client.get("/api/v1/tasks", headers=headers, params=params)
    assert res.status_code == 200, res.text
    return res.json()


def test_lists_across_projects_open_and_soonest_first(client, auth_a):
    tower = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    villa = make(client, auth_a, "/projects", {"name": "Villa", "code": "VIL", "budget": "1"})
    done = make(client, auth_a, f"/projects/{tower['id']}/tasks", {"title": "Survey", "due_date": "2026-01-01"})
    client.patch(f"/api/v1/projects/{tower['id']}/tasks/{done['id']}", headers=auth_a, json={"status": "done"})
    make(client, auth_a, f"/projects/{villa['id']}/tasks", {"title": "No date"})
    make(client, auth_a, f"/projects/{villa['id']}/tasks", {"title": "Roof", "due_date": "2026-03-01"})
    make(client, auth_a, f"/projects/{tower['id']}/tasks", {"title": "Pour", "due_date": "2026-02-01"})

    rows = tasks(client, auth_a)
    assert [(t["title"], t["project_code"]) for t in rows] == [
        ("Pour", "TWR"), ("Roof", "VIL"), ("No date", "VIL"), ("Survey", "TWR"),
    ]
    assert rows[0]["project_name"] == "Tower"


def test_filters(client, auth_a):
    tower = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    villa = make(client, auth_a, "/projects", {"name": "Villa", "code": "VIL", "budget": "1"})
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    pm_id = client.get("/api/v1/auth/me", headers=pm).json()["id"]
    make(client, auth_a, f"/projects/{tower['id']}/tasks", {"title": "For PM", "assignee_id": pm_id})
    blocked = make(client, auth_a, f"/projects/{villa['id']}/tasks", {"title": "Blocked one"})
    client.patch(f"/api/v1/projects/{villa['id']}/tasks/{blocked['id']}", headers=auth_a, json={"status": "blocked"})

    mine = tasks(client, pm, mine="true")
    assert [t["title"] for t in mine] == ["For PM"]
    assert mine[0]["assignee_name"] == "project_manager user"
    assert [t["title"] for t in tasks(client, auth_a, status="blocked")] == ["Blocked one"]
    assert [t["title"] for t in tasks(client, auth_a, project_id=tower["id"])] == ["For PM"]
    assert tasks(client, auth_a, mine="true") == []


def test_only_own_company(client, auth_a, auth_b):
    tower = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    make(client, auth_a, f"/projects/{tower['id']}/tasks", {"title": "Secret"})
    assert tasks(client, auth_b) == []
    assert tasks(client, auth_b, project_id=tower["id"]) == []
