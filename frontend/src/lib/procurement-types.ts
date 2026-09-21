export type MaterialRequestStatus = "pending" | "approved" | "rejected" | "converted";
export type PurchaseOrderStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "partially_received"
  | "received"
  | "cancelled";

export interface MaterialRequestItem {
  id: string;
  material_id: string;
  quantity: string;
}

export interface MaterialRequest {
  id: string;
  project_id: string;
  requested_by_id: string;
  status: MaterialRequestStatus;
  notes: string | null;
  created_at: string;
  items: MaterialRequestItem[];
}

export interface PurchaseOrderItem {
  id: string;
  material_id: string;
  quantity: string;
  rate: string;
  quantity_received: string;
  amount: string;
}

export interface PurchaseOrder {
  id: string;
  supplier_id: string;
  project_id: string | null;
  material_request_id: string | null;
  created_by_id: string;
  approved_by_id: string | null;
  status: PurchaseOrderStatus;
  po_number: string;
  created_at: string;
  items: PurchaseOrderItem[];
  total_amount: string;
}
