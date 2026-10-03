"""BUILD-041..043: RFQ -> supplier quotations -> comparison -> award (a drafted PO)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from tests.conftest import make_user_in_company


def make(client, headers, path, body=None):
    res = client.post(f"/api/v1{path}", headers=headers, json=body or {})
    assert res.status_code in (200, 201), (path, res.text)
    return res.json()


@pytest.fixture
def s(client, auth_a):
    return {
        "project": make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"}),
        "acme": make(client, auth_a, "/suppliers", {"name": "Acme"}),
        "beta": make(client, auth_a, "/suppliers", {"name": "Beta"}),
        "gamma": make(client, auth_a, "/suppliers", {"name": "Gamma"}),
        "cement": make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"}),
        "steel": make(client, auth_a, "/materials", {"name": "Steel", "sku": "STL", "unit": "Ton"}),
    }


def new_rfq(client, headers, s, **extra):
    body = {
        "title": "Level 3 slab materials",
        "project_id": s["project"]["id"],
        "items": [
            {"material_id": s["cement"]["id"], "quantity": "100"},
            {"material_id": s["steel"]["id"], "quantity": "2"},
        ],
        "supplier_ids": [s["acme"]["id"], s["beta"]["id"]],
        **extra,
    }
    return make(client, headers, "/rfqs", body)


def quote(client, headers, rfq, supplier, cement_rate, steel_rate, **extra):
    items = {i["material_name"]: i["id"] for i in rfq["items"]}
    return make(client, headers, f"/rfqs/{rfq['id']}/quotations", {
        "supplier_id": supplier["id"],
        "items": [{"rfq_item_id": items["Cement"], "rate": cement_rate}, {"rfq_item_id": items["Steel"], "rate": steel_rate}],
        **extra,
    })


def test_create_rfq(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s, response_due="2026-12-01")
    assert rfq["rfq_number"] == "RFQ-1001" and rfq["status"] == "open"
    assert rfq["project_name"] == "Tower"
    assert [(i["material_name"], i["unit"], Decimal(i["quantity"])) for i in rfq["items"]] == [("Cement", "Bag", 100), ("Steel", "Ton", 2)]
    assert [(v["supplier_name"], v["has_quoted"]) for v in rfq["invited"]] == [("Acme", False), ("Beta", False)]
    assert new_rfq(client, auth_a, s)["rfq_number"] == "RFQ-1002"


def test_comparison_hand_checked(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s)
    quote(client, auth_a, rfq, s["acme"], "1400", "280000", delivery_days=5)   # 140000 + 560000 = 700000
    quote(client, auth_a, rfq, s["beta"], "1350", "290000", delivery_days=9)   # 135000 + 580000 = 715000
    rfq = quote(client, auth_a, rfq, s["gamma"], "1500", "275000")             # 150000 + 550000 = 700000 (uninvited)

    by_supplier = {q["supplier_name"]: q for q in rfq["quotations"]}
    assert {k: Decimal(v["total"]) for k, v in by_supplier.items()} == {"Acme": 700000, "Beta": 715000, "Gamma": 700000}
    # Tie for cheapest overall: both flagged, list ordered cheapest first then by name.
    assert [q["supplier_name"] for q in rfq["quotations"]] == ["Acme", "Gamma", "Beta"]
    assert [k for k, v in by_supplier.items() if v["is_lowest_total"]] == ["Acme", "Gamma"]
    # Cheapest per item: Beta for cement, Gamma for steel.
    item_ids = {i["material_name"]: i["id"] for i in rfq["items"]}
    lowest = {
        name: sorted(q["supplier_name"] for q in rfq["quotations"] for qi in q["items"] if qi["rfq_item_id"] == iid and qi["is_lowest"])
        for name, iid in item_ids.items()
    }
    assert lowest == {"Cement": ["Beta"], "Steel": ["Gamma"]}
    # Quoting without an invitation adds the supplier to the list.
    assert {v["supplier_name"]: v["has_quoted"] for v in rfq["invited"]} == {"Acme": True, "Beta": True, "Gamma": True}


def test_requoting_replaces_the_quote(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s)
    quote(client, auth_a, rfq, s["acme"], "1400", "280000")
    rfq = quote(client, auth_a, rfq, s["acme"], "1300", "280000", notes="revised")
    assert len(rfq["quotations"]) == 1
    assert Decimal(rfq["quotations"][0]["total"]) == 690000 and rfq["quotations"][0]["notes"] == "revised"


def test_quotation_must_price_every_item_once(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s)
    cement = next(i["id"] for i in rfq["items"] if i["material_name"] == "Cement")
    url = f"/api/v1/rfqs/{rfq['id']}/quotations"
    partial = {"supplier_id": s["acme"]["id"], "items": [{"rfq_item_id": cement, "rate": "1"}]}
    assert client.post(url, headers=auth_a, json=partial).status_code == 400
    dup = {"supplier_id": s["acme"]["id"], "items": [{"rfq_item_id": cement, "rate": "1"}] * 2}
    assert client.post(url, headers=auth_a, json=dup).status_code == 400
    negative = {"supplier_id": s["acme"]["id"], "items": [{"rfq_item_id": cement, "rate": "-1"}]}
    assert client.post(url, headers=auth_a, json=negative).status_code == 422


def test_award_drafts_a_po_at_quoted_rates_for_approval(client, auth_a, s):
    mr = make(client, auth_a, "/material-requests", {
        "project_id": s["project"]["id"], "items": [{"material_id": s["cement"]["id"], "quantity": "100"}],
    })
    rfq = make(client, auth_a, "/rfqs", {
        "title": "From request", "material_request_id": mr["id"], "supplier_ids": [s["acme"]["id"]],
    })
    # Items and project came from the material request.
    assert [(i["material_name"], Decimal(i["quantity"])) for i in rfq["items"]] == [("Cement", 100)]
    assert rfq["project_id"] == s["project"]["id"]
    cement_item = rfq["items"][0]["id"]
    rfq = make(client, auth_a, f"/rfqs/{rfq['id']}/quotations", {
        "supplier_id": s["acme"]["id"], "items": [{"rfq_item_id": cement_item, "rate": "1375.50"}],
    })

    awarded = make(client, auth_a, f"/rfqs/{rfq['id']}/award", {"quotation_id": rfq["quotations"][0]["id"]})
    assert awarded["status"] == "awarded" and awarded["po_number"] == "PO-1001"
    po = client.get(f"/api/v1/purchase-orders/{awarded['purchase_order_id']}", headers=auth_a).json()
    assert po["status"] == "pending_approval"  # still needs a human approval
    assert po["supplier_id"] == s["acme"]["id"] and po["project_id"] == s["project"]["id"]
    assert [(Decimal(i["quantity"]), Decimal(i["rate"])) for i in po["items"]] == [(100, Decimal("1375.50"))]
    assert client.get(f"/api/v1/material-requests/{mr['id']}", headers=auth_a).json()["status"] == "converted"
    assert "rfq.awarded" in [e["action"] for e in client.get("/api/v1/audit-log", headers=auth_a).json()]

    # Closed now: no second award, no more quotes, no cancel.
    q_id = rfq["quotations"][0]["id"]
    assert client.post(f"/api/v1/rfqs/{rfq['id']}/award", headers=auth_a, json={"quotation_id": q_id}).status_code == 409
    assert client.post(f"/api/v1/rfqs/{rfq['id']}/cancel", headers=auth_a).status_code == 409
    assert len(client.get("/api/v1/purchase-orders", headers=auth_a).json()) == 1


def test_expired_quotation_cannot_be_awarded(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s)
    rfq = quote(client, auth_a, rfq, s["acme"], "1", "1", valid_until=str(date.today() - timedelta(days=1)))
    assert rfq["quotations"][0]["expired"] is True
    res = client.post(f"/api/v1/rfqs/{rfq['id']}/award", headers=auth_a, json={"quotation_id": rfq["quotations"][0]["id"]})
    assert res.status_code == 409 and "expired" in res.json()["detail"]
    assert client.get(f"/api/v1/rfqs/{rfq['id']}", headers=auth_a).json()["status"] == "open"
    assert client.get("/api/v1/purchase-orders", headers=auth_a).json() == []


def test_failed_award_leaves_rfq_open(client, auth_a, s):
    # The material request is rejected after the RFQ was raised, so the PO can't be drafted.
    mr = make(client, auth_a, "/material-requests", {
        "project_id": s["project"]["id"], "items": [{"material_id": s["cement"]["id"], "quantity": "1"}],
    })
    rfq = make(client, auth_a, "/rfqs", {"title": "x", "material_request_id": mr["id"], "supplier_ids": [s["acme"]["id"]]})
    rfq = make(client, auth_a, f"/rfqs/{rfq['id']}/quotations", {
        "supplier_id": s["acme"]["id"], "items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": "1"}],
    })
    client.patch(f"/api/v1/material-requests/{mr['id']}/status", headers=auth_a, json={"status": "rejected"})
    res = client.post(f"/api/v1/rfqs/{rfq['id']}/award", headers=auth_a, json={"quotation_id": rfq["quotations"][0]["id"]})
    assert res.status_code == 409
    after = client.get(f"/api/v1/rfqs/{rfq['id']}", headers=auth_a).json()
    assert after["status"] == "open" and after["purchase_order_id"] is None
    assert "rfq.awarded" not in [e["action"] for e in client.get("/api/v1/audit-log", headers=auth_a).json()]


def test_cancel(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s)
    assert make(client, auth_a, f"/rfqs/{rfq['id']}/cancel")["status"] == "cancelled"
    assert client.post(f"/api/v1/rfqs/{rfq['id']}/quotations", headers=auth_a, json={
        "supplier_id": s["acme"]["id"], "items": [{"rfq_item_id": i["id"], "rate": "1"} for i in rfq["items"]],
    }).status_code == 409


def test_validation(client, auth_a, s):
    base = {"title": "x", "project_id": s["project"]["id"]}
    assert client.post("/api/v1/rfqs", headers=auth_a, json={**base, "items": []}).status_code == 422
    twice = [{"material_id": s["cement"]["id"], "quantity": "1"}] * 2
    assert client.post("/api/v1/rfqs", headers=auth_a, json={**base, "items": twice}).status_code == 400
    zero = [{"material_id": s["cement"]["id"], "quantity": "0"}]
    assert client.post("/api/v1/rfqs", headers=auth_a, json={**base, "items": zero}).status_code == 422


def test_list(client, auth_a, s):
    rfq = new_rfq(client, auth_a, s)
    quote(client, auth_a, rfq, s["acme"], "1400", "280000")
    quote(client, auth_a, rfq, s["beta"], "1350", "290000")
    [row] = client.get("/api/v1/rfqs", headers=auth_a).json()
    assert (row["item_count"], row["invited_count"], row["quotation_count"]) == (2, 2, 2)
    assert Decimal(row["lowest_total"]) == 700000


def test_roles(client, auth_a, s, viewer_a):
    assert client.post("/api/v1/rfqs", headers=viewer_a, json={"title": "x", "items": []}).status_code == 403
    keeper = make_user_in_company(client, auth_a, "store@example.com", "storekeeper")
    rfq = new_rfq(client, keeper, s)
    rfq = quote(client, keeper, rfq, s["acme"], "1", "1")
    # A storekeeper can collect quotes but not choose the winner.
    res = client.post(f"/api/v1/rfqs/{rfq['id']}/award", headers=keeper, json={"quotation_id": rfq["quotations"][0]["id"]})
    assert res.status_code == 403
    assert client.get(f"/api/v1/rfqs/{rfq['id']}", headers=viewer_a).status_code == 200


def test_tenant_isolation(client, auth_a, auth_b, s):
    rfq = new_rfq(client, auth_a, s)
    assert client.get(f"/api/v1/rfqs/{rfq['id']}", headers=auth_b).status_code == 404
    assert client.get("/api/v1/rfqs", headers=auth_b).json() == []
    b_supplier = make(client, auth_b, "/suppliers", {"name": "B Supplier"})
    b_material = make(client, auth_b, "/materials", {"name": "B Cement", "sku": "BC", "unit": "Bag"})
    # A's RFQ can't name B's supplier or material, and B can't quote on A's RFQ.
    assert client.post("/api/v1/rfqs", headers=auth_a, json={
        "title": "x", "items": [{"material_id": s["cement"]["id"], "quantity": "1"}], "supplier_ids": [b_supplier["id"]],
    }).status_code == 404
    assert client.post("/api/v1/rfqs", headers=auth_a, json={
        "title": "x", "items": [{"material_id": b_material["id"], "quantity": "1"}],
    }).status_code == 404
    assert client.post(f"/api/v1/rfqs/{rfq['id']}/quotations", headers=auth_b, json={
        "supplier_id": b_supplier["id"], "items": [{"rfq_item_id": i["id"], "rate": "1"} for i in rfq["items"]],
    }).status_code == 404
    assert client.post(f"/api/v1/rfqs/{rfq['id']}/quotations", headers=auth_a, json={
        "supplier_id": b_supplier["id"], "items": [{"rfq_item_id": i["id"], "rate": "1"} for i in rfq["items"]],
    }).status_code == 404
