export type ProjectStatus = "planning" | "active" | "on_hold" | "completed" | "cancelled";

export interface Project {
  id: string;
  company_id: string;
  name: string;
  code: string;
  client_name: string | null;
  location: string | null;
  project_type: string | null;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: string;
  status: ProjectStatus;
  progress_percent: number;
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSummary {
  total_projects: number;
  total_budget: string;
  avg_progress: number;
  at_risk_count: number;
}
