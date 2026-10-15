"""Marketplace supplier registry: onboarding, verification, catalog, duplicate
detection, and distinctness from the existing per-company Supplier (PLAT-016..020)."""

import io

from app.models.enums import PlatformStaffRole
from tests.test_platform_http import platform_login


def owner_headers(client, email="mkt-owner@buildos.ai"):
    return platform_login(client, email=email, role=PlatformStaffRole.OWNER)


def make_supplier(client, headers, name="Global Cement Ltd", **extra):
    body = {"name": name, "categories": ["cement"], "coverage_areas": ["Punjab"], **extra}
    res = client.post("/api/v1/platform/marketplace/suppliers", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["supplier"]


# ---- Existing ERP supplier CRUD is untouched -------------------------------------------


def test_existing_tenant_supplier_crud_is_unaffected(client, auth_a):
    res = client.post(
        "/api/v1/suppliers", json={"name": "Local Builders Supply", "email": "info@local-builders.example.com"}, headers=auth_a
    )
    assert res.status_code == 201, res.text
    supplier_id = res.json()["id"]

    res = client.get("/api/v1/suppliers", headers=auth_a)
    assert res.status_code == 200
    assert any(s["id"] == supplier_id for s in res.json())

    res = client.patch(f"/api/v1/suppliers/{supplier_id}", json={"phone": "12345"}, headers=auth_a)
    assert res.status_code == 200
    assert res.json()["phone"] == "12345"


def test_marketplace_suppliers_are_not_erp_suppliers(client, auth_a):
    headers = owner_headers(client)
    mkt = make_supplier(client, headers, name="Not The Same Supplier")

    res = client.get("/api/v1/suppliers", headers=auth_a)
    assert all(s["name"] != mkt["name"] or s["id"] != mkt["id"] for s in res.json())


# ---- Admin-led onboarding, usable before any supplier login exists ----------------------


def test_create_and_view_supplier_with_categories_and_coverage(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)
    assert supplier["verification_status"] == "pending"
    assert supplier["categories"] == ["cement"]
    assert supplier["coverage_areas"] == ["Punjab"]

    res = client.get(f"/api/v1/platform/marketplace/suppliers/{supplier['id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["contacts"] == []
    assert res.json()["products"] == []


def test_support_role_can_view_but_not_create_or_edit(client):
    owner = owner_headers(client)
    supplier = make_supplier(client, owner)
    support = platform_login(client, email="mkt-support@buildos.ai", role=PlatformStaffRole.SUPPORT)

    res = client.get("/api/v1/platform/marketplace/suppliers", headers=support)
    assert res.status_code == 200

    res = client.post(
        "/api/v1/platform/marketplace/suppliers", json={"name": "Blocked Supplier"}, headers=support
    )
    assert res.status_code == 403

    res = client.patch(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}", json={"notes": "x"}, headers=support
    )
    assert res.status_code == 403


# ---- Never auto-merge by name -----------------------------------------------------------


def test_duplicate_names_are_flagged_not_merged(client):
    headers = owner_headers(client)
    first = make_supplier(client, headers, name="Steel Traders Co")
    res = client.post(
        "/api/v1/platform/marketplace/suppliers",
        json={"name": "steel traders co"},  # same name, different case
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    second = body["supplier"]
    assert second["id"] != first["id"]  # two distinct records, never merged
    assert len(body["possible_duplicates"]) == 1
    assert body["possible_duplicates"][0]["id"] == first["id"]

    res = client.get("/api/v1/platform/marketplace/suppliers?search=Steel", headers=headers)
    assert res.json()["total"] == 2


# ---- Verification workflow ---------------------------------------------------------------


def test_verification_transitions(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)

    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/verification",
        json={"status": "verified"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "verified"

    # Can't jump straight to pending-only transitions in reverse without going through the rules.
    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/verification",
        json={"status": "verified"},
        headers=headers,
    )
    assert res.status_code == 400  # no-op transition refused

    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/verification",
        json={"status": "suspended", "reason": "complaint received"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "suspended"


def test_cannot_skip_straight_from_pending_to_suspended(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)
    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/verification",
        json={"status": "suspended"},
        headers=headers,
    )
    assert res.status_code == 400


def test_verification_change_is_audit_logged_and_in_supplier_activity(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)
    client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/verification",
        json={"status": "verified"},
        headers=headers,
    )

    res = client.get(f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/activity", headers=headers)
    actions = [e["action"] for e in res.json()]
    assert "marketplace_supplier.verification_changed" in actions
    assert "marketplace_supplier.onboarded" in actions

    res = client.get("/api/v1/platform/audit-log", headers=headers)
    assert any(e["action"] == "marketplace_supplier.verification_changed" for e in res.json())


# ---- Contacts and documents -------------------------------------------------------------


def test_add_contact(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)
    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/contacts",
        json={"name": "Ali Khan", "role": "Sales Manager", "is_primary": True},
        headers=headers,
    )
    assert res.status_code == 201, res.text


def test_upload_and_download_document(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)

    pdf_bytes = b"%PDF-1.4\n%mock pdf content"
    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/documents",
        data={"title": "Trade License"},
        files={"file": ("license.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    doc_id = res.json()["id"]

    res = client.get(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/documents/{doc_id}/download", headers=headers
    )
    assert res.status_code == 200
    assert res.content == pdf_bytes


# ---- Product catalog: prices, min quantities, lead times --------------------------------


def test_add_and_update_product(client):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)

    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/products",
        json={"name": "OPC Cement 50kg", "unit": "bag", "price": "950.00", "minimum_order_quantity": "100", "lead_time_days": 3},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    product_id = res.json()["id"]
    assert res.json()["price"] == "950.00"

    res = client.patch(
        f"/api/v1/platform/marketplace/products/{product_id}", json={"price": "975.00"}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["price"] == "975.00"

    res = client.get(f"/api/v1/platform/marketplace/suppliers/{supplier['id']}", headers=headers)
    assert len(res.json()["products"]) == 1


# ---- Search and filtering ----------------------------------------------------------------


def test_search_and_filter_by_category_and_area(client):
    headers = owner_headers(client)
    make_supplier(client, headers, name="Cement Co", categories=["cement"], coverage_areas=["Sindh"])
    make_supplier(client, headers, name="Steel Co", categories=["steel"], coverage_areas=["Punjab"])

    res = client.get("/api/v1/platform/marketplace/suppliers?category=steel", headers=headers)
    names = [s["name"] for s in res.json()["suppliers"]]
    assert "Steel Co" in names
    assert "Cement Co" not in names

    res = client.get("/api/v1/platform/marketplace/suppliers?area=Sindh", headers=headers)
    names = [s["name"] for s in res.json()["suppliers"]]
    assert "Cement Co" in names
    assert "Steel Co" not in names

    res = client.get("/api/v1/platform/marketplace/suppliers?search=Steel", headers=headers)
    assert len(res.json()["suppliers"]) == 1


# ---- Future-integration groundwork: company links + material mappings -------------------


def test_link_company_and_prevent_duplicate_link(client, auth_a):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/company-links",
        json={"company_id": company_id, "notes": "intro call done"},
        headers=headers,
    )
    assert res.status_code == 201, res.text

    res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/company-links",
        json={"company_id": company_id},
        headers=headers,
    )
    assert res.status_code == 409

    res = client.get(f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/company-links", headers=headers)
    assert len(res.json()) == 1
    assert res.json()[0]["company_name"] is not None


def test_material_mapping_links_marketplace_product_to_tenant_material(client, auth_a):
    headers = owner_headers(client)
    supplier = make_supplier(client, headers)
    product_res = client.post(
        f"/api/v1/platform/marketplace/suppliers/{supplier['id']}/products",
        json={"name": "Rebar 12mm", "unit": "ton", "price": "180000"},
        headers=headers,
    )
    product_id = product_res.json()["id"]

    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    mat_res = client.post(
        "/api/v1/materials",
        json={"name": "Rebar 12mm", "sku": "REB-12", "unit": "ton", "category_id": None},
        headers=auth_a,
    )
    assert mat_res.status_code == 201, mat_res.text
    material_id = mat_res.json()["id"]

    res = client.post(
        "/api/v1/platform/marketplace/material-mappings",
        json={"company_id": company_id, "material_id": material_id, "marketplace_product_id": product_id},
        headers=headers,
    )
    assert res.status_code == 201, res.text

    res = client.post(
        "/api/v1/platform/marketplace/material-mappings",
        json={"company_id": company_id, "material_id": material_id, "marketplace_product_id": product_id},
        headers=headers,
    )
    assert res.status_code == 409
