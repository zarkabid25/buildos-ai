export interface Supplier {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  notes: string | null;
}

export interface SupplierContact {
  id: string;
  supplier_id: string;
  name: string;
  role: string | null;
  phone: string | null;
  email: string | null;
}

export interface SupplierTransaction {
  purchase_order_id: string;
  po_number: string;
  project_id: string | null;
  project_name: string | null;
  status: string;
  created_at: string;
  ordered_amount: string;
  received_amount: string;
  receipt_count: number;
  last_received_at: string | null;
}

export interface SupplierPerformance {
  po_count: number;
  committed_po_count: number;
  fully_received_count: number;
  cancelled_count: number;
  committed_amount: string;
  received_amount: string;
  fulfilment_percent: string | null;
  average_lead_time_days: string | null;
  note: string;
}
