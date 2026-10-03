from decimal import Decimal


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def setup_stock(client, headers, name="Cement", unit="Bag", quantity="1000"):
    """A project, a warehouse, and a material with stock in it."""
    project = make(client, headers, "/projects", {"name": "Tower", "code": "TWR-" + name[:3].upper(), "budget": "1000"})
    warehouse = make(client, headers, "/warehouses", {"name": f"Main {name}"})
    material = make(client, headers, "/materials", {"name": name, "sku": name[:3].upper() + "-1", "unit": unit})
    make(client, headers, "/inventory/stock-in", {
        "material_id": material["id"], "warehouse_id": warehouse["id"], "quantity": quantity,
    })
    return project, warehouse, material


def allocate(client, headers, project, warehouse, material, quantity):
    return make(client, headers, "/inventory/stock-out", {
        "material_id": material["id"], "warehouse_id": warehouse["id"],
        "project_id": project["id"], "quantity": quantity,
    })


def boq_line(client, headers, project, **overrides):
    body = {"item_code": "001", "description": "Cement", "unit": "Bag", "quantity": "100", "rate": "10"}
    body.update(overrides)
    return make(client, headers, f"/projects/{project['id']}/boq", body)


def vs_actual(client, headers, project):
    res = client.get(f"/api/v1/projects/{project['id']}/boq/vs-actual", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_hand_checked_over_and_within_plan(client, auth_a):
    project, warehouse, cement = setup_stock(client, auth_a)
    sand = make(client, auth_a, "/materials", {"name": "Sand", "sku": "SND-1", "unit": "m3"})
    make(client, auth_a, "/inventory/stock-in", {"material_id": sand["id"], "warehouse_id": warehouse["id"], "quantity": "50"})

    boq_line(client, auth_a, project, material_id=cement["id"])  # plan 100 bags @ 10
    boq_line(client, auth_a, project, item_code="002", description="Sand", unit="m3",
             quantity="40", rate="25", material_id=sand["id"])  # plan 40 m3 @ 25
    allocate(client, auth_a, project, warehouse, cement, "70")
    allocate(client, auth_a, project, warehouse, cement, "50")  # 120 bags total
    allocate(client, auth_a, project, warehouse, sand, "30")

    data = vs_actual(client, auth_a, project)
    cement_line, sand_line = data["lines"]

    assert Decimal(cement_line["actual_quantity"]) == 120
    assert Decimal(cement_line["quantity_variance"]) == 20
    assert Decimal(cement_line["variance_percent"]) == Decimal("20.0")
    assert Decimal(cement_line["actual_amount"]) == 1200
    assert cement_line["status"] == "over_plan"
    assert cement_line["material_name"] == "Cement"

    assert Decimal(sand_line["actual_quantity"]) == 30
    assert Decimal(sand_line["quantity_variance"]) == -10
    assert Decimal(sand_line["variance_percent"]) == Decimal("-25.0")
    assert sand_line["status"] == "within_plan"

    assert Decimal(data["planned_total"]) == 2000  # 1000 + 1000
    assert Decimal(data["tracked_planned_total"]) == 2000
    assert Decimal(data["actual_total"]) == 1950  # 120*10 + 30*25
    assert data["unplanned"] == []


def test_unlinked_line_is_not_tracked_and_not_counted(client, auth_a):
    project, _, _ = setup_stock(client, auth_a)
    boq_line(client, auth_a, project)  # no material link

    data = vs_actual(client, auth_a, project)
    line = data["lines"][0]
    assert line["status"] == "not_tracked"
    assert line["actual_quantity"] is None and line["quantity_variance"] is None
    assert Decimal(data["planned_total"]) == 1000
    assert Decimal(data["tracked_planned_total"]) == 0
    assert Decimal(data["actual_total"]) == 0


def test_linked_line_with_no_consumption_is_not_started(client, auth_a):
    project, _, cement = setup_stock(client, auth_a)
    boq_line(client, auth_a, project, material_id=cement["id"])
    line = vs_actual(client, auth_a, project)["lines"][0]
    assert line["status"] == "not_started"
    assert Decimal(line["actual_quantity"]) == 0


def test_zero_planned_quantity_has_no_percent(client, auth_a):
    project, warehouse, cement = setup_stock(client, auth_a)
    boq_line(client, auth_a, project, quantity="0", material_id=cement["id"])
    allocate(client, auth_a, project, warehouse, cement, "5")
    line = vs_actual(client, auth_a, project)["lines"][0]
    assert line["variance_percent"] is None
    assert line["status"] == "over_plan"


def test_unplanned_consumption_listed(client, auth_a):
    project, warehouse, cement = setup_stock(client, auth_a)
    allocate(client, auth_a, project, warehouse, cement, "15")
    data = vs_actual(client, auth_a, project)
    assert data["lines"] == []
    assert [(u["material_name"], Decimal(u["actual_quantity"])) for u in data["unplanned"]] == [("Cement", 15)]


def test_only_this_projects_allocations_count(client, auth_a):
    project, warehouse, cement = setup_stock(client, auth_a)
    other = make(client, auth_a, "/projects", {"name": "Other", "code": "OTH", "budget": "1"})
    boq_line(client, auth_a, project, material_id=cement["id"])
    allocate(client, auth_a, other, warehouse, cement, "40")
    # A plain stock-out with no project is not project consumption either.
    make(client, auth_a, "/inventory/stock-out", {"material_id": cement["id"], "warehouse_id": warehouse["id"], "quantity": "10"})

    line = vs_actual(client, auth_a, project)["lines"][0]
    assert Decimal(line["actual_quantity"]) == 0


def test_unit_mismatch_rejected(client, auth_a):
    project, _, cement = setup_stock(client, auth_a)
    res = client.post(
        f"/api/v1/projects/{project['id']}/boq", headers=auth_a,
        json={"item_code": "001", "description": "Cement", "unit": "Kg", "quantity": "1", "material_id": cement["id"]},
    )
    assert res.status_code == 400
    assert "Unit mismatch" in res.json()["detail"]
    # Case and surrounding spaces don't count as a mismatch.
    boq_line(client, auth_a, project, unit=" bag ", material_id=cement["id"])


def test_changing_unit_of_linked_line_is_checked(client, auth_a):
    project, _, cement = setup_stock(client, auth_a)
    line = boq_line(client, auth_a, project, material_id=cement["id"])
    res = client.patch(f"/api/v1/projects/{project['id']}/boq/{line['id']}", headers=auth_a, json={"unit": "Kg"})
    assert res.status_code == 400
    # Unlinking is allowed, and then the unit is free to change.
    res = client.patch(f"/api/v1/projects/{project['id']}/boq/{line['id']}", headers=auth_a,
                       json={"material_id": None, "unit": "Kg"})
    assert res.status_code == 200, res.text
    assert res.json()["material_id"] is None


def test_material_linked_to_two_lines_rejected(client, auth_a):
    project, _, cement = setup_stock(client, auth_a)
    boq_line(client, auth_a, project, material_id=cement["id"])
    res = client.post(
        f"/api/v1/projects/{project['id']}/boq", headers=auth_a,
        json={"item_code": "002", "description": "More cement", "unit": "Bag", "material_id": cement["id"]},
    )
    assert res.status_code == 409

    # Same rule inside a single bulk accept.
    other = make(client, auth_a, "/projects", {"name": "Other", "code": "OTH", "budget": "1"})
    res = client.post(
        f"/api/v1/projects/{other['id']}/boq/ai-accept", headers=auth_a,
        json=[
            {"item_code": "1", "description": "a", "unit": "Bag", "material_id": cement["id"]},
            {"item_code": "2", "description": "b", "unit": "Bag", "material_id": cement["id"]},
        ],
    )
    assert res.status_code == 409
    assert client.get(f"/api/v1/projects/{other['id']}/boq", headers=auth_a).json() == []


def test_cannot_link_another_companys_material(client, auth_a, auth_b):
    project, _, _ = setup_stock(client, auth_a)
    _, _, foreign = setup_stock(client, auth_b, name="Steel", unit="Ton")
    res = client.post(
        f"/api/v1/projects/{project['id']}/boq", headers=auth_a,
        json={"item_code": "001", "description": "Steel", "unit": "Ton", "material_id": foreign["id"]},
    )
    assert res.status_code == 404


def test_cannot_allocate_to_another_companys_project(client, auth_a, auth_b):
    _, warehouse, cement = setup_stock(client, auth_a)
    foreign_project, _, _ = setup_stock(client, auth_b, name="Steel", unit="Ton")
    res = client.post("/api/v1/inventory/stock-out", headers=auth_a, json={
        "material_id": cement["id"], "warehouse_id": warehouse["id"],
        "project_id": foreign_project["id"], "quantity": "5",
    })
    assert res.status_code == 404
    assert vs_actual(client, auth_b, foreign_project)["unplanned"] == []


def test_vs_actual_is_tenant_isolated(client, auth_a, auth_b):
    project, _, _ = setup_stock(client, auth_a)
    res = client.get(f"/api/v1/projects/{project['id']}/boq/vs-actual", headers=auth_b)
    assert res.status_code == 404
