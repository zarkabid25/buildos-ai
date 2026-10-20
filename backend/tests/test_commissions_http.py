"""Marketplace commissions (Phase 6, PLAT-033..037): supplier commission
agreements, the commission ledger (accrual only on real, verified-payment
events against a marketplace-attributed PO), disputes/adjustments, commission
invoices and manual settlement, and the revenue dashboard -- plus the
required compatibility checks proving ordinary ERP purchase orders are never
touched by any of this."""

from decimal import Decimal

from app.models.enums import PlatformStaffRole
from tests.test_marketplace_integration_http import enable_marketplace, make, make_verified_supplier, owner_headers


def _setup_project(client, auth):
    project = make(client, auth, "/projects", {"name": "Commission Tower", "code": "COMM", "budget": "1"})
    material = make(client, auth, "/materials", {"name": "Steel Rebar", "sku": "REB", "unit": "Ton"})
    return project, material


def commission_eligible_po(client, auth, staff, rate="1000", quantity="10"):
    """Builds a real marketplace-sourced, awarded, approved PO -- the exact
    flow test_marketplace_integration_http.py's complete-flow test already
    proves end to end. Returns (po_id, company_id, marketplace_supplier)."""
    mkt_supplier = make_verified_supplier(client, staff, name=f"Commission Supplier {rate}")
    company_id = enable_marketplace(client, staff, auth)
    project, material = _setup_project(client, auth)

    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth)
    assert res.status_code == 201, res.text

    rfq = make(client, auth, "/rfqs", {"title": "Rebar", "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": quantity}]})
    res = client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth)
    assert res.status_code == 201, res.text

    res = client.post(
        f"/api/v1/platform/marketplace/companies/{company_id}/rfqs/{rfq['id']}/suppliers/{mkt_supplier['id']}/quotations",
        json={"items": [{"rfq_item_id": rfq["items"][0]["id"], "rate": rate}], "delivery_days": 5},
        headers=staff,
    )
    assert res.status_code == 201, res.text
    rfq_after = res.json()
    quotation_id = rfq_after["quotations"][0]["id"]

    res = client.post(f"/api/v1/rfqs/{rfq['id']}/award", json={"quotation_id": quotation_id}, headers=auth)
    assert res.status_code == 200, res.text
    po_id = res.json()["purchase_order_id"]

    res = client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=auth)
    assert res.status_code == 200, res.text
    return po_id, company_id, mkt_supplier


def ordinary_po(client, auth):
    """A plain ERP PO with no marketplace involvement at all -- the control
    case every commission test needs to prove doesn't accrue anything."""
    project, material = _setup_project(client, auth)
    supplier = make(client, auth, "/suppliers", {"name": "Plain Steel Co"})
    po = make(
        client, auth, "/purchase-orders",
        {"supplier_id": supplier["id"], "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "5", "rate": "500"}]},
    )
    res = client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=auth)
    assert res.status_code == 200, res.text
    return po["id"]


def pay(client, auth, po_id, amount, method="bank_transfer"):
    from datetime import date

    res = client.post("/api/v1/payments/supplier", json={"purchase_order_id": po_id, "amount": amount, "paid_on": str(date.today()), "method": method}, headers=auth)
    assert res.status_code == 201, res.text
    return res.json()


def percentage_agreement(client, staff, supplier_id, rate="0.1000"):
    res = client.post(f"/api/v1/platform/commissions/suppliers/{supplier_id}/agreements", json={"basis": "percentage", "rate": rate}, headers=staff)
    assert res.status_code == 201, res.text
    return res.json()


def fixed_fee_agreement(client, staff, supplier_id, fee="50"):
    res = client.post(f"/api/v1/platform/commissions/suppliers/{supplier_id}/agreements", json={"basis": "fixed_fee", "fixed_fee_amount": fee}, headers=staff)
    assert res.status_code == 201, res.text
    return res.json()


# ---- PLAT-033: supplier commission agreements -----------------------------------------------


def test_percentage_commission_agreement(client):
    staff = owner_headers(client, email="comm-staff1@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Pct Supplier")
    agreement = percentage_agreement(client, staff, mkt_supplier["id"], rate="0.0500")
    assert agreement["basis"] == "percentage"
    assert Decimal(agreement["rate"]) == Decimal("0.0500")
    assert agreement["version"] == 1


def test_fixed_fee_commission_agreement(client):
    staff = owner_headers(client, email="comm-staff2@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Fixed Supplier")
    agreement = fixed_fee_agreement(client, staff, mkt_supplier["id"], fee="25")
    assert agreement["basis"] == "fixed_fee"
    assert Decimal(agreement["fixed_fee_amount"]) == 25


def test_agreement_requires_matching_fields(client):
    staff = owner_headers(client, email="comm-staff3@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Bad Agreement Supplier")
    res = client.post(f"/api/v1/platform/commissions/suppliers/{mkt_supplier['id']}/agreements", json={"basis": "percentage"}, headers=staff)
    assert res.status_code == 422  # no rate given for a percentage agreement


def test_agreement_versioning_supersedes_not_edits(client):
    staff = owner_headers(client, email="comm-staff4@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Versioned Supplier")
    v1 = percentage_agreement(client, staff, mkt_supplier["id"], rate="0.0500")
    v2 = percentage_agreement(client, staff, mkt_supplier["id"], rate="0.0800")
    assert v2["version"] == 2

    res = client.get(f"/api/v1/platform/commissions/suppliers/{mkt_supplier['id']}/agreements", headers=staff)
    rows = {r["id"]: r for r in res.json()}
    assert rows[v1["id"]]["status"] == "superseded"
    assert rows[v1["id"]]["effective_to"] is not None  # old row kept, not deleted
    assert rows[v2["id"]]["status"] == "active"


def test_overlapping_active_agreements_refused_at_the_db_level(client):
    """Belt-and-suspenders: even if the service-layer supersede logic were
    ever skipped, the partial unique index itself refuses a second active
    row for the same supplier."""
    import uuid as _uuid

    from app.db.session import SessionLocal
    from app.models.commission import SupplierCommissionAgreement
    from app.models.enums import CommissionAgreementStatus, CommissionBasis
    from datetime import datetime, timezone
    from sqlalchemy.exc import IntegrityError

    staff = owner_headers(client, email="comm-staff5@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="DB Guard Supplier")
    percentage_agreement(client, staff, mkt_supplier["id"])

    staff_id = client.get("/api/v1/platform/auth/me", headers=staff).json()["id"]

    db = SessionLocal()
    try:
        dupe = SupplierCommissionAgreement(
            marketplace_supplier_id=_uuid.UUID(mkt_supplier["id"]), version=99, basis=CommissionBasis.PERCENTAGE, rate=Decimal("0.01"),
            status=CommissionAgreementStatus.ACTIVE, effective_from=datetime.now(timezone.utc),
            created_by_staff_id=_uuid.UUID(staff_id),
        )
        db.add(dupe)
        raised = False
        try:
            db.flush()
        except IntegrityError:
            raised = True
            db.rollback()
        assert raised
    finally:
        db.close()


def test_agreement_expiration_stops_accrual(client, auth_a):
    """An agreement with a past effective_to must not apply, even while its
    status column still says ACTIVE (staff ended it without superseding)."""
    import uuid as _uuid

    from app.db.session import SessionLocal
    from app.models.commission import SupplierCommissionAgreement
    from datetime import datetime, timedelta, timezone

    staff = owner_headers(client, email="comm-staff6@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    agreement = percentage_agreement(client, staff, mkt_supplier["id"])

    db = SessionLocal()
    try:
        row = db.query(SupplierCommissionAgreement).filter(SupplierCommissionAgreement.id == _uuid.UUID(agreement["id"])).first()
        row.effective_to = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    pay(client, auth_a, po_id, "1000")
    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    assert res.json() == []  # expired agreement -> no accrual


def test_missing_agreement_means_no_accrual(client, auth_a):
    staff = owner_headers(client, email="comm-staff7@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    # No agreement created at all.
    pay(client, auth_a, po_id, "1000")
    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    assert res.json() == []


# ---- PLAT-034: commission ledger / accrual ----------------------------------------------------


def test_ordinary_erp_po_is_never_charged_commission(client, auth_a):
    """The critical compatibility guarantee this phase's own inspection was
    about: a plain PO with zero marketplace involvement, paid in full,
    never produces a single commission ledger entry -- even with a global
    agreement existing for some other, unrelated supplier."""
    staff = owner_headers(client, email="comm-staff8@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Unrelated Supplier")
    percentage_agreement(client, staff, mkt_supplier["id"])

    po_id = ordinary_po(client, auth_a)
    pay(client, auth_a, po_id, "2500")

    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    assert res.json() == []


def test_marketplace_po_payment_accrues_percentage_commission(client, auth_a):
    staff = owner_headers(client, email="comm-staff9@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")

    pay(client, auth_a, po_id, "4000")  # partial payment against a 10,000 PO
    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    entries = res.json()
    assert len(entries) == 1
    assert entries[0]["kind"] == "accrual"
    assert Decimal(entries[0]["commission_amount"]) == Decimal("400.00")  # 10% of 4000
    assert Decimal(entries[0]["base_amount"]) == Decimal("4000")


def test_partial_payments_each_accrue_their_own_proportional_commission(client, auth_a):
    staff = owner_headers(client, email="comm-staff10@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")

    pay(client, auth_a, po_id, "4000")
    pay(client, auth_a, po_id, "6000")
    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    entries = res.json()
    assert len(entries) == 2
    total_commission = sum(Decimal(e["commission_amount"]) for e in entries)
    assert total_commission == Decimal("1000.00")  # 10% of 10,000 total, across two payments


def test_fixed_fee_commission_charges_once_not_per_payment(client, auth_a):
    staff = owner_headers(client, email="comm-staff11@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    fixed_fee_agreement(client, staff, mkt_supplier["id"], fee="75")

    pay(client, auth_a, po_id, "4000")
    pay(client, auth_a, po_id, "6000")
    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    entries = [e for e in res.json() if e["kind"] == "accrual"]
    assert len(entries) == 1
    assert Decimal(entries[0]["commission_amount"]) == Decimal("75")


def test_duplicate_payment_event_never_double_accrues(client, auth_a):
    """Directly exercises the idempotency guard: calling the accrual
    function twice for the exact same SupplierPayment must never produce two
    ledger entries -- the DB partial-unique index on supplier_payment_id is
    what actually prevents it."""
    import uuid as _uuid

    from app.db.session import SessionLocal
    from app.models.payment import SupplierPayment
    from app.services import commission_service

    staff = owner_headers(client, email="comm-staff12@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"])
    payment = pay(client, auth_a, po_id, "4000")

    db = SessionLocal()
    try:
        row = db.query(SupplierPayment).filter(SupplierPayment.id == _uuid.UUID(payment["id"])).first()
        second_attempt = commission_service.accrue_on_supplier_payment(db, row.company_id, row)
        assert second_attempt is None  # refused -- an entry already exists for this payment
    finally:
        db.close()

    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    accruals = [e for e in res.json() if e["kind"] == "accrual"]
    assert len(accruals) == 1


def test_adjustment_entry_is_a_new_row_not_an_edit(client, auth_a):
    staff = owner_headers(client, email="comm-staff13@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    percentage_agreement(client, staff, mkt_supplier["id"])
    pay(client, auth_a, po_id, "1000")

    res = client.post(
        "/api/v1/platform/commissions/ledger/adjustments",
        json={"purchase_order_id": po_id, "marketplace_supplier_id": mkt_supplier["id"], "amount": "-10", "note": "Goodwill credit"},
        headers=staff,
    )
    assert res.status_code == 201
    assert res.json()["kind"] == "adjustment"

    res = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff)
    kinds = [e["kind"] for e in res.json()]
    assert "accrual" in kinds and "adjustment" in kinds and len(kinds) == 2  # both rows present, nothing overwritten


# ---- PLAT-036: disputes -----------------------------------------------------------------------


def test_dispute_approval_posts_a_reversal_not_an_edit(client, auth_a):
    staff = owner_headers(client, email="comm-staff14@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")
    pay(client, auth_a, po_id, "10000")

    ledger = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff).json()
    accrual_id = ledger[0]["id"]

    res = client.post("/api/v1/platform/commissions/disputes", json={"ledger_entry_id": accrual_id, "reason": "Supplier disputes this rate"}, headers=staff)
    assert res.status_code == 201
    dispute = res.json()
    assert dispute["status"] == "open"

    res = client.post(f"/api/v1/platform/commissions/disputes/{dispute['id']}/review", json={"approve": True, "resolution_notes": "Confirmed, reversing"}, headers=staff)
    assert res.status_code == 200
    reviewed = res.json()
    assert reviewed["status"] == "approved"
    assert reviewed["resulting_entry_id"] is not None

    ledger_after = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff).json()
    assert len(ledger_after) == 2  # the original accrual AND the new reversal, both visible
    net = sum(Decimal(e["commission_amount"]) for e in ledger_after)
    assert net == Decimal("0")  # fully offset


def test_rejected_dispute_leaves_the_charge_standing(client, auth_a):
    staff = owner_headers(client, email="comm-staff15@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    percentage_agreement(client, staff, mkt_supplier["id"])
    pay(client, auth_a, po_id, "1000")
    ledger = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff).json()

    res = client.post("/api/v1/platform/commissions/disputes", json={"ledger_entry_id": ledger[0]["id"], "reason": "Not justified"}, headers=staff)
    dispute_id = res.json()["id"]
    res = client.post(f"/api/v1/platform/commissions/disputes/{dispute_id}/review", json={"approve": False, "resolution_notes": "Rate was correct"}, headers=staff)
    assert res.json()["status"] == "rejected"

    ledger_after = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff).json()
    assert len(ledger_after) == 1  # nothing reversed


def test_cannot_open_two_disputes_on_the_same_entry(client, auth_a):
    staff = owner_headers(client, email="comm-staff16@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    percentage_agreement(client, staff, mkt_supplier["id"])
    pay(client, auth_a, po_id, "1000")
    ledger = client.get("/api/v1/platform/commissions/ledger", params={"purchase_order_id": po_id}, headers=staff).json()

    client.post("/api/v1/platform/commissions/disputes", json={"ledger_entry_id": ledger[0]["id"], "reason": "First"}, headers=staff)
    res = client.post("/api/v1/platform/commissions/disputes", json={"ledger_entry_id": ledger[0]["id"], "reason": "Second"}, headers=staff)
    assert res.status_code == 409


# ---- PLAT-035: commission invoices and payments ------------------------------------------------


def test_commission_invoice_generation_and_uniqueness(client, auth_a):
    staff = owner_headers(client, email="comm-staff17@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")
    pay(client, auth_a, po_id, "10000")

    res = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    )
    assert res.status_code == 201, res.text
    invoice = res.json()
    assert Decimal(invoice["total_amount"]) == Decimal("1000.00")
    assert len(invoice["items"]) == 1

    other_invoice_number = client.get(f"/api/v1/platform/commissions/invoices/{invoice['id']}", headers=staff).json()["invoice_number"]
    # A second generation call for the same already-billed period has nothing left to bill.
    res2 = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    )
    assert res2.status_code == 400  # nothing unbilled left -- never double-invoices the same entry


def test_commission_invoices_separate_from_subscription_invoices(client, auth_a):
    staff = owner_headers(client, email="comm-staff18@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    percentage_agreement(client, staff, mkt_supplier["id"])
    pay(client, auth_a, po_id, "1000")
    res = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    )
    commission_invoice_number = res.json()["invoice_number"]
    assert commission_invoice_number.startswith("COMM-")  # never shares SubscriptionInvoice's INV- numbering


def test_partial_commission_settlement_and_outstanding_balance(client, auth_a):
    staff = owner_headers(client, email="comm-staff19@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")
    pay(client, auth_a, po_id, "10000")
    invoice = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    ).json()

    res = client.post(f"/api/v1/platform/commissions/invoices/{invoice['id']}/payments", json={"amount": "600", "paid_on": "2026-11-01", "receipt_reference": "RCPT-1"}, headers=staff)
    assert res.status_code == 201
    partially_paid = res.json()
    assert partially_paid["status"] == "partially_paid"
    assert Decimal(partially_paid["outstanding"]) == Decimal("400.00")

    res = client.post(f"/api/v1/platform/commissions/invoices/{invoice['id']}/payments", json={"amount": "400", "paid_on": "2026-11-15"}, headers=staff)
    fully_paid = res.json()
    assert fully_paid["status"] == "paid"
    assert Decimal(fully_paid["outstanding"]) == Decimal("0.00")


def test_overpaying_a_commission_invoice_is_refused(client, auth_a):
    staff = owner_headers(client, email="comm-staff20@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff)
    percentage_agreement(client, staff, mkt_supplier["id"])
    pay(client, auth_a, po_id, "1000")
    invoice = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    ).json()
    res = client.post(f"/api/v1/platform/commissions/invoices/{invoice['id']}/payments", json={"amount": "999999", "paid_on": "2026-11-01"}, headers=staff)
    assert res.status_code == 400


# ---- Platform finance permissions / isolation --------------------------------------------------


def test_support_staff_cannot_create_agreements_or_record_payments(client, auth_a):
    from tests.test_platform_http import platform_login

    support = platform_login(client, email="comm-support@buildos.ai", role=PlatformStaffRole.SUPPORT)
    owner = owner_headers(client, email="comm-staff21@buildos.ai")
    mkt_supplier = make_verified_supplier(client, owner, name="Support Gate Supplier")

    res = client.post(f"/api/v1/platform/commissions/suppliers/{mkt_supplier['id']}/agreements", json={"basis": "percentage", "rate": "0.05"}, headers=support)
    assert res.status_code == 403

    # Support CAN still read the ledger/agreements (view-only, same tier as billing).
    res = client.get(f"/api/v1/platform/commissions/suppliers/{mkt_supplier['id']}/agreements", headers=support)
    assert res.status_code == 200


def test_tenant_user_token_cannot_reach_any_commission_endpoint(client, auth_a):
    """There is no tenant-side commission route at all -- commissions are a
    platform/supplier relationship, never a company one."""
    res = client.get("/api/v1/platform/commissions/ledger", headers=auth_a)
    assert res.status_code == 401


# ---- PLAT-037: revenue dashboard ----------------------------------------------------------------


def test_revenue_dashboard_distinguishes_earned_invoiced_collected_outstanding(client, auth_a):
    staff = owner_headers(client, email="comm-staff22@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")
    pay(client, auth_a, po_id, "10000")

    res = client.get("/api/v1/platform/commissions/revenue", headers=staff)
    before_invoice = res.json()
    assert Decimal(before_invoice["commission_earned"]) >= Decimal("1000.00")
    assert Decimal(before_invoice["commission_invoiced"]) == Decimal("0.00")  # not invoiced yet

    invoice = client.post(
        "/api/v1/platform/commissions/invoices",
        json={"marketplace_supplier_id": mkt_supplier["id"], "period_start": "2026-01-01", "period_end": "2026-12-31", "due_date": "2027-01-15"},
        headers=staff,
    ).json()
    client.post(f"/api/v1/platform/commissions/invoices/{invoice['id']}/payments", json={"amount": "600", "paid_on": "2026-11-01"}, headers=staff)

    res = client.get("/api/v1/platform/commissions/revenue", headers=staff)
    after = res.json()
    assert Decimal(after["commission_invoiced"]) >= Decimal("1000.00")
    assert Decimal(after["commission_collected"]) >= Decimal("600.00")
    assert Decimal(after["outstanding_commission"]) >= Decimal("400.00")
    assert after["marketplace_attributed_order_count"] >= 1
    assert any(c["marketplace_supplier_id"] == mkt_supplier["id"] for c in after["supplier_contributions"])


def test_revenue_dashboard_never_counts_marketplace_order_value_as_platform_revenue(client, auth_a):
    """The order's own value (attributed_amount) must never leak into
    commission_earned -- only the real, calculated commission amount does."""
    staff = owner_headers(client, email="comm-staff23@buildos.ai")
    po_id, company_id, mkt_supplier = commission_eligible_po(client, auth_a, staff, rate="1000", quantity="10")
    percentage_agreement(client, staff, mkt_supplier["id"], rate="0.1000")
    pay(client, auth_a, po_id, "10000")  # full PO value paid

    res = client.get("/api/v1/platform/commissions/revenue", headers=staff)
    body = res.json()
    assert Decimal(body["commission_earned"]) == Decimal("1000.00")  # 10% of 10,000, not 10,000 itself
    assert Decimal(body["marketplace_attributed_order_value"]) == Decimal("10000.00")  # the order value, reported separately
