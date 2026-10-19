"""Supplier-side commission statement (PLAT-042) -- entirely read-only, thin
wrappers around the existing Phase 6 commission services, always scoped to
the authenticated supplier's own marketplace_supplier_id (never
client-supplied), so one supplier can never see another's agreements,
ledger entries, invoices or disputes."""

import uuid

from sqlalchemy.orm import Session

from app.schemas.commission import CommissionAgreementRead, CommissionDisputeRead, CommissionInvoiceRead, CommissionLedgerEntryRead
from app.services import commission_agreement_service, commission_dispute_service, commission_invoice_service, commission_service


def list_my_agreements(db: Session, marketplace_supplier_id: uuid.UUID) -> list[CommissionAgreementRead]:
    return commission_agreement_service.list_agreements(db, marketplace_supplier_id)


def list_my_ledger(db: Session, marketplace_supplier_id: uuid.UUID) -> list[CommissionLedgerEntryRead]:
    return commission_service.list_ledger(db, marketplace_supplier_id=marketplace_supplier_id)


def list_my_invoices(db: Session, marketplace_supplier_id: uuid.UUID) -> list[CommissionInvoiceRead]:
    return commission_invoice_service.list_invoices(db, marketplace_supplier_id=marketplace_supplier_id)


def get_my_invoice(db: Session, marketplace_supplier_id: uuid.UUID, invoice_id: uuid.UUID) -> CommissionInvoiceRead:
    invoice = commission_invoice_service.get_invoice(db, invoice_id)
    if invoice.marketplace_supplier_id != marketplace_supplier_id:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return invoice


def list_my_disputes(db: Session, marketplace_supplier_id: uuid.UUID) -> list[CommissionDisputeRead]:
    return commission_dispute_service.list_disputes(db, marketplace_supplier_id=marketplace_supplier_id)
