from datetime import date, timedelta


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def make_project(client, headers, **overrides):
    body = {"name": "Tower", "code": "TWR" + str(id(overrides))[-4:], "budget": "1000"}
    body.update(overrides)
    return make(client, headers, "/projects", body)


def make_task(client, headers, project_id, title="Task", **overrides):
    body = {"title": title, **overrides}
    return make(client, headers, f"/projects/{project_id}/tasks", body)


def test_task_has_start_and_due_date(client, auth_a):
    project = make_project(client, auth_a)
    task = make_task(client, auth_a, project["id"], start_date="2026-01-01", due_date="2026-01-10")
    assert task["start_date"] == "2026-01-01" and task["due_date"] == "2026-01-10"
    assert task["depends_on"] == []


def test_add_and_remove_dependency(client, auth_a):
    project = make_project(client, auth_a)
    foundation = make_task(client, auth_a, project["id"], "Foundation")
    framing = make_task(client, auth_a, project["id"], "Framing")

    res = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{framing['id']}/dependencies",
        headers=auth_a, json={"depends_on_task_id": foundation["id"]},
    )
    assert res.status_code == 201, res.text
    assert res.json()["depends_on"] == [foundation["id"]]

    tasks = client.get(f"/api/v1/projects/{project['id']}/tasks", headers=auth_a).json()
    framing_now = next(t for t in tasks if t["id"] == framing["id"])
    assert framing_now["depends_on"] == [foundation["id"]]

    res = client.delete(
        f"/api/v1/projects/{project['id']}/tasks/{framing['id']}/dependencies/{foundation['id']}",
        headers=auth_a,
    )
    assert res.status_code == 204
    tasks = client.get(f"/api/v1/projects/{project['id']}/tasks", headers=auth_a).json()
    assert next(t for t in tasks if t["id"] == framing["id"])["depends_on"] == []


def test_a_task_cannot_depend_on_itself(client, auth_a):
    project = make_project(client, auth_a)
    task = make_task(client, auth_a, project["id"])
    res = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/dependencies",
        headers=auth_a, json={"depends_on_task_id": task["id"]},
    )
    assert res.status_code == 400


def test_duplicate_dependency_is_rejected(client, auth_a):
    project = make_project(client, auth_a)
    a = make_task(client, auth_a, project["id"], "A")
    b = make_task(client, auth_a, project["id"], "B")
    client.post(f"/api/v1/projects/{project['id']}/tasks/{a['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": b["id"]})
    res = client.post(f"/api/v1/projects/{project['id']}/tasks/{a['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": b["id"]})
    assert res.status_code == 409


def test_direct_cycle_is_rejected(client, auth_a):
    project = make_project(client, auth_a)
    a = make_task(client, auth_a, project["id"], "A")
    b = make_task(client, auth_a, project["id"], "B")
    # a depends on b
    assert client.post(f"/api/v1/projects/{project['id']}/tasks/{a['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": b["id"]}).status_code == 201
    # b depends on a would close a 2-node cycle
    res = client.post(f"/api/v1/projects/{project['id']}/tasks/{b['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": a["id"]})
    assert res.status_code == 400


def test_indirect_three_node_cycle_is_rejected(client, auth_a):
    project = make_project(client, auth_a)
    a = make_task(client, auth_a, project["id"], "A")
    b = make_task(client, auth_a, project["id"], "B")
    c = make_task(client, auth_a, project["id"], "C")
    # a -> b -> c  (a depends on b, b depends on c)
    assert client.post(f"/api/v1/projects/{project['id']}/tasks/{a['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": b["id"]}).status_code == 201
    assert client.post(f"/api/v1/projects/{project['id']}/tasks/{b['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": c["id"]}).status_code == 201
    # closing it: c depends on a
    res = client.post(f"/api/v1/projects/{project['id']}/tasks/{c['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": a["id"]})
    assert res.status_code == 400


def test_cannot_depend_on_a_task_from_another_project(client, auth_a):
    p1 = make_project(client, auth_a)
    p2 = make_project(client, auth_a)
    t1 = make_task(client, auth_a, p1["id"])
    t2 = make_task(client, auth_a, p2["id"])
    res = client.post(f"/api/v1/projects/{p1['id']}/tasks/{t1['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": t2["id"]})
    assert res.status_code == 404


def test_cannot_depend_on_another_companys_task(client, auth_a, auth_b):
    p1 = make_project(client, auth_a)
    t1 = make_task(client, auth_a, p1["id"])
    p2 = make_project(client, auth_b)
    t2 = make_task(client, auth_b, p2["id"])
    res = client.post(f"/api/v1/projects/{p1['id']}/tasks/{t1['id']}/dependencies", headers=auth_a, json={"depends_on_task_id": t2["id"]})
    assert res.status_code == 404


# ---- schedule endpoint --------------------------------------------------------


def test_schedule_with_no_dates_has_no_variance(client, auth_a):
    project = make_project(client, auth_a)
    make_task(client, auth_a, project["id"], "A")
    res = client.get(f"/api/v1/projects/{project['id']}/schedule", headers=auth_a)
    assert res.status_code == 200
    body = res.json()
    assert body["schedule_variance_percent"] is None and body["schedule_variance_days"] is None
    assert len(body["tasks"]) == 1
    assert "start and end date" in body["variance_note"]


def test_schedule_variance_behind(client, auth_a):
    today = date.today()
    project = make_project(
        client, auth_a,
        start_date=str(today - timedelta(days=50)), end_date=str(today + timedelta(days=50)),
    )
    client.patch(f"/api/v1/projects/{project['id']}", headers=auth_a, json={"progress_percent": 20})
    res = client.get(f"/api/v1/projects/{project['id']}/schedule", headers=auth_a)
    body = res.json()
    # 100-day span, day 50 -> 50% elapsed vs 20% progress -> 30 points behind -> 30 days
    assert body["schedule_variance_percent"] == 30
    assert body["schedule_variance_days"] == 30
    assert "behind schedule" in body["variance_note"]


def test_schedule_includes_milestones(client, auth_a):
    project = make_project(client, auth_a)
    make(client, auth_a, f"/projects/{project['id']}/milestones", {"name": "Foundation done", "due_date": "2026-02-01"})
    res = client.get(f"/api/v1/projects/{project['id']}/schedule", headers=auth_a)
    assert [m["name"] for m in res.json()["milestones"]] == ["Foundation done"]


def test_schedule_requires_login_and_respects_tenant(client, auth_a, auth_b):
    project = make_project(client, auth_a)
    assert client.get(f"/api/v1/projects/{project['id']}/schedule").status_code == 401
    assert client.get(f"/api/v1/projects/{project['id']}/schedule", headers=auth_b).status_code == 404
