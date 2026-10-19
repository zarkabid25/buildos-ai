export type CommissionBasis = "percentage" | "fixed_fee";
export type CommissionAgreementStatus = "active" | "superseded" | "cancelled";
export type CommissionLedgerEntryKind = "accrual" | "reversal" | "adjustment";
export type CommissionInvoiceStatus = "draft" | "pending" | "partially_paid" | "paid" | "void";
export type CommissionDisputeStatus = "open" | "approved" | "rejected";

export interface CommissionAgreement {
  id: string;
  marketplace_supplier_id: string;
  version: number;
  basis: CommissionBasis;
  rate: string | null;
  fixed_fee_amount: string | null;
  earning_trigger: "on_payment";
  status: CommissionAgreementStatus;
  effective_from: string;
  effective_to: string | null;
  notes: string | null;
  created_at: string;
}

export interface CommissionLedgerEntry {
  id: string;
  company_id: string;
  purchase_order_id: string;
  marketplace_supplier_id: string;
  marketplace_supplier_name: string | null;
  supplier_payment_id: string | null;
  kind: CommissionLedgerEntryKind;
  agreement_id: string | null;
  basis_snapshot: CommissionBasis | null;
  rate_snapshot: string | null;
  fixed_fee_snapshot: string | null;
  base_amount: string;
  commission_amount: string;
  related_entry_id: string | null;
  invoiced: boolean;
  note: string | null;
  created_at: string;
}

export interface CommissionDispute {
  id: string;
  ledger_entry_id: string;
  marketplace_supplier_id: string;
  reason: string;
  status: CommissionDisputeStatus;
  raised_by_staff_id: string;
  raised_by_staff_name: string | null;
  reviewed_by_staff_id: string | null;
  reviewed_by_staff_name: string | null;
  resolution_notes: string | null;
  resulting_entry_id: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface CommissionInvoiceLineItem {
  id: string;
  ledger_entry_id: string;
  description: string;
  amount: string;
}

export interface CommissionPayment {
  id: string;
  invoice_id: string;
  amount: string;
  paid_on: string;
  method: string;
  receipt_reference: string | null;
  notes: string | null;
  recorded_by_staff_id: string;
  recorded_by_staff_name: string | null;
  created_at: string;
}

export interface CommissionInvoice {
  id: string;
  marketplace_supplier_id: string;
  marketplace_supplier_name: string | null;
  invoice_number: string;
  status: CommissionInvoiceStatus;
  currency: string;
  subtotal: string;
  total_amount: string;
  amount_paid: string;
  outstanding: string;
  period_start: string;
  period_end: string;
  due_date: string;
  items: CommissionInvoiceLineItem[];
  payments: CommissionPayment[];
  created_at: string;
}

export interface CommissionMonthlyTrendPoint {
  month: string;
  amount: string;
}

export interface SupplierRevenueContribution {
  marketplace_supplier_id: string;
  marketplace_supplier_name: string;
  commission_earned: string;
}

export interface CommissionRevenueDashboard {
  commission_earned: string;
  commission_invoiced: string;
  commission_collected: string;
  outstanding_commission: string;
  active_agreements: number;
  marketplace_attributed_order_count: number;
  marketplace_attributed_order_value: string;
  disputed_amount: string;
  monthly_trend: CommissionMonthlyTrendPoint[];
  supplier_contributions: SupplierRevenueContribution[];
}
