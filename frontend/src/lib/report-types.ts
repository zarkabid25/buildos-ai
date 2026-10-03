export type ReportKind = "projects" | "inventory" | "procurement" | "expenses";

export interface Period {
  date_from?: string;
  date_to?: string;
}

export interface ProjectReportRow {
  project_id: string;
  name: string;
  code: string;
  status: string;
  progress_percent: number;
  budget: string;
  committed: string;
  actual: string;
  forecast: string;
  expected_variance: string;
  schedule_variance_days: number | null;
  health_score: number | null;
  open_tasks: number;
  overdue_tasks: number;
}

export interface ProjectReport {
  as_of: string;
  rows: ProjectReportRow[];
  total_budget: string;
  total_actual: string;
  total_committed: string;
}

export interface InventoryReportRow {
  material_id: string;
  name: string;
  sku: string;
  unit: string;
  on_hand: string;
  reorder_point: number;
  stock_status: "ok" | "low" | "out";
  received: string;
  issued: string;
}

export interface InventoryReport {
  rows: InventoryReportRow[];
  low_stock_count: number;
  out_of_stock_count: number;
}

export interface SupplierSpendRow {
  supplier_id: string;
  supplier_name: string;
  po_count: number;
  ordered_amount: string;
  received_amount: string;
}

export interface ProcurementReport {
  po_count_by_status: Record<string, number>;
  po_value_by_status: Record<string, string>;
  material_requests_by_status: Record<string, number>;
  rows: SupplierSpendRow[];
}

export interface ExpenseReportRow {
  project_id: string;
  project_name: string;
  category: string;
  expense_count: number;
  amount: string;
}

export interface ExpenseReport {
  rows: ExpenseReportRow[];
  total_amount: string;
  by_category: Record<string, string>;
}
