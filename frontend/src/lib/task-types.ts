export type TaskStatus = "todo" | "in_progress" | "blocked" | "done";
export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  assignee_id: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface Milestone {
  id: string;
  project_id: string;
  name: string;
  due_date: string | null;
  is_completed: boolean;
  completed_date: string | null;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  user: { id: string; full_name: string; email: string; role: string };
}

export interface ProjectHealth {
  overall_score: number | null;
  schedule_score: number | null;
  cost_score: number | null;
  inventory_score: number | null;
  quality_score: number | null;
  safety_score: number | null;
  labor_score: number | null;
  procurement_score: number | null;
  is_at_risk: boolean;
}
