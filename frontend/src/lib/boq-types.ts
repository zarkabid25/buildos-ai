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
