export interface BoqItem {
  id: string;
  project_id: string;
  item_code: string;
  description: string;
  category: string | null;
  unit: string;
  quantity: string;
  rate: string;
  amount: string;
  is_ai_generated: boolean;
  material_id: string | null;
}

export interface BoqCategoryTotal {
  category: string;
  total_amount: string;
  item_count: number;
}

export interface BoqSummary {
  total_amount: string;
  item_count: number;
  by_category: BoqCategoryTotal[];
}

export interface BoqAiGeneratedItem {
  item_code: string;
  description: string;
  category: string;
  unit: string;
  quantity: string;
  rate: string;
}

export interface BoqAiGenerateResponse {
  items: BoqAiGeneratedItem[];
  disclaimer: string;
}

export type BoqLineStatus = "not_tracked" | "not_started" | "within_plan" | "over_plan";

export interface BoqVsActualLine {
  boq_item_id: string;
  item_code: string;
  description: string;
  unit: string;
  material_id: string | null;
  material_name: string | null;
  planned_quantity: string;
  rate: string;
  planned_amount: string;
  actual_quantity: string | null;
  actual_amount: string | null;
  quantity_variance: string | null;
  variance_percent: string | null;
  status: BoqLineStatus;
}

export interface UnplannedConsumption {
  material_id: string;
  material_name: string;
  unit: string;
  actual_quantity: string;
}

export interface BoqVsActual {
  lines: BoqVsActualLine[];
  unplanned: UnplannedConsumption[];
  planned_total: string;
  tracked_planned_total: string;
  actual_total: string;
  valuation_note: string;
}
