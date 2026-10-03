export type RfqStatus = "open" | "awarded" | "cancelled";

export interface RfqItem {
  id: string;
  material_id: string;
  material_name: string;
  unit: string;
  quantity: string;
}

export interface QuotationItem {
  rfq_item_id: string;
  rate: string;
  amount: string;
  is_lowest: boolean;
}

export interface Quotation {
  id: string;
  supplier_id: string;
  supplier_name: string;
  delivery_days: number | null;
  valid_until: string | null;
  expired: boolean;
  notes: string | null;
  total: string;
  is_lowest_total: boolean;
  created_at: string;
  items: QuotationItem[];
}

export interface Rfq {
  id: string;
  rfq_number: string;
  title: string;
  project_id: string | null;
  project_name: string | null;
  material_request_id: string | null;
  response_due: string | null;
  notes: string | null;
  status: RfqStatus;
  created_at: string;
  items: RfqItem[];
  invited: { supplier_id: string; supplier_name: string; has_quoted: boolean }[];
  quotations: Quotation[];
  awarded_quotation_id: string | null;
  purchase_order_id: string | null;
  po_number: string | null;
}

export interface RfqSummary {
  id: string;
  rfq_number: string;
  title: string;
  project_name: string | null;
  status: RfqStatus;
  response_due: string | null;
  item_count: number;
  invited_count: number;
  quotation_count: number;
  lowest_total: string | null;
  created_at: string;
}

export type PaymentMethod = "bank_transfer" | "cheque" | "cash" | "other";

export interface SupplierPayment {
  id: string;
  purchase_order_id: string;
  po_number: string | null;
  supplier_name: string | null;
  amount: string;
  paid_on: string;
  method: PaymentMethod;
  reference: string | null;
  notes: string | null;
}

export interface ClientReceipt {
  id: string;
  project_id: string;
  project_name: string | null;
  amount: string;
  received_on: string;
  method: PaymentMethod;
  reference: string | null;
  notes: string | null;
}

export interface CashSummary {
  total_received: string;
  total_paid_out: string;
  net: string;
  total_outstanding: string;
  projects: { project_id: string | null; project_name: string; received: string; paid_out: string; net: string }[];
  payables: { supplier_id: string; supplier_name: string; committed: string; paid: string; outstanding: string }[];
}
