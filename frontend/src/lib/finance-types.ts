export interface Expense {
  id: string;
  project_id: string;
  category_id: string | null;
  amount: string;
  description: string | null;
  expense_date: string;
  created_at: string;
}

export interface ProjectCostSummary {
  original_budget: string;
  committed: string;
  actual: string;
  remaining: string;
  forecast: string;
  expected_variance: string;
  forecast_basis: string;
}
