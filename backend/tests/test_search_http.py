import io


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def search(client, headers, q):
    res = client.get(f"/api/v1/search?q={q}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_finds_a_project_by_name_or_code(client, auth_a):
    make(client, auth_a, "/projects", {"name": "Riverside Tower", "code": "RIV-01", "budget": "1"})
    assert [p["title"] for p in search(client, auth_a, "riverside")["projects"]] == ["Riverside Tower"]
    assert [p["title"] for p in search(client, auth_a, "RIV-01")["projects"]] == ["Riverside Tower"]


def test_search_is_case_insensitive(client, auth_a):
    make(client, auth_a, "/projects", {"name": "Riverside Tower", "code": "RIV-01", "budget": "1"})
    assert len(search(client, auth_a, "RIVERSIDE")["projects"]) == 1
    assert len(search(client, auth_a, "riverSIDE")["projects"]) == 1


def test_finds_a_task_and_links_to_its_project(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    make(client, auth_a, f"/projects/{project['id']}/tasks", {"title": "Pour concrete slab"})
    results = search(client, auth_a, "concrete")
    assert len(results["tasks"]) == 1
    assert results["tasks"][0]["link"] == f"/projects/{project['id']}"


def test_finds_a_material_by_name_or_sku(client, auth_a):
    make(client, auth_a, "/materials", {"name": "Portland Cement", "sku": "PC-500", "unit": "Bag"})
    assert len(search(client, auth_a, "portland")["materials"]) == 1
    assert len(search(client, auth_a, "PC-500")["materials"]) == 1


def test_finds_a_supplier(client, auth_a):
    make(client, auth_a, "/suppliers", {"name": "ABC Construction Supplies"})
    assert len(search(client, auth_a, "ABC")["suppliers"]) == 1


def test_finds_a_purchase_order_by_number(client, auth_a):
    material = make(client, auth_a, "/materials", {"name": "Steel", "sku": "STL", "unit": "Ton"})
    supplier = make(client, auth_a, "/suppliers", {"name": "Supplier"})
    po = make(client, auth_a, "/purchase-orders", {
        "supplier_id": supplier["id"], "items": [{"material_id": material["id"], "quantity": "1", "rate": "1"}],
    })
    results = search(client, auth_a, po["po_number"])
    assert [r["title"] for r in results["purchase_orders"]] == [po["po_number"]]


def test_finds_a_document_by_title_or_filename(client, auth_a):
    client.post(
        "/api/v1/documents", headers=auth_a,
        data={"title": "Main Contract", "category": "contract"},
        files={"file": ("agreement.pdf", io.BytesIO(b"%PDF-1.4\n" + b"x" * 20), "application/pdf")},
    )
    assert len(search(client, auth_a, "Main Contract")["documents"]) == 1
    assert len(search(client, auth_a, "agreement")["documents"]) == 1


def test_finds_an_employee_by_name_or_designation(client, auth_a):
    make(client, auth_a, "/employees", {"full_name": "Ali Khan", "designation": "Site Engineer", "daily_wage": "2000"})
    assert len(search(client, auth_a, "Ali Khan")["employees"]) == 1
    assert len(search(client, auth_a, "Site Engineer")["employees"]) == 1


def test_one_query_finds_matches_across_multiple_types(client, auth_a):
    make(client, auth_a, "/projects", {"name": "Riverside Tower", "code": "RIV", "budget": "1"})
    make(client, auth_a, "/materials", {"name": "Riverside Sand", "sku": "RS", "unit": "m3"})
    results = search(client, auth_a, "riverside")
    assert len(results["projects"]) == 1 and len(results["materials"]) == 1
    assert results["total"] == 2


def test_query_below_minimum_length_returns_nothing(client, auth_a):
    make(client, auth_a, "/projects", {"name": "Riverside Tower", "code": "RIV", "budget": "1"})
    results = search(client, auth_a, "r")
    assert results["total"] == 0 and results["projects"] == []


def test_no_matches_is_a_clean_empty_result_not_an_error(client, auth_a):
    results = search(client, auth_a, "nonexistent-xyz")
    assert results["total"] == 0
    assert all(results[k] == [] for k in ["projects", "tasks", "materials", "suppliers", "purchase_orders", "documents", "employees"])


def test_another_company_never_appears_in_results(client, auth_a, auth_b):
    make(client, auth_a, "/projects", {"name": "Company A Secret Tower", "code": "SECRET", "budget": "1"})
    make(client, auth_b, "/materials", {"name": "Company B Secret Material", "sku": "SEC", "unit": "Bag"})

    a_results = search(client, auth_a, "secret")
    assert len(a_results["projects"]) == 1 and a_results["materials"] == []

    b_results = search(client, auth_b, "secret")
    assert a_results["projects"][0]["title"] not in [p["title"] for p in b_results["projects"]]
    assert len(b_results["materials"]) == 1


def test_search_requires_login(client):
    assert client.get("/api/v1/search?q=test").status_code == 401
