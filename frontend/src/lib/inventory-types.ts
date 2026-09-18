export interface MaterialCategory {
  id: string;
  name: string;
  description: string | null;
}

export interface Material {
  id: string;
  name: string;
  sku: string;
  unit: string;
  category_id: string | null;
  reorder_point: number;
}

export interface Warehouse {
  id: string;
  name: string;
  location: string | null;
}

export type InventoryTransactionType =
  | "stock_in"
  | "stock_out"
  | "transfer_in"
  | "transfer_out"
  | "allocation";

export interface InventoryTransaction {
  id: string;
  material_id: string;
  warehouse_id: string;
  project_id: string | null;
  transaction_type: InventoryTransactionType;
  quantity: string;
  reference: string | null;
  notes: string | null;
  created_at: string;
}

export interface MaterialStockLevel {
  material_id: string;
  material_name: string;
  unit: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity_on_hand: string;
}

export interface InventoryDashboard {
  total_materials: number;
  low_stock_count: number;
  out_of_stock_count: number;
  warehouse_count: number;
}
