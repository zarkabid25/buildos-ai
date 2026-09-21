export interface Employee {
  id: string;
  full_name: string;
  designation: string | null;
  phone: string | null;
  email: string | null;
  daily_wage: string;
  hire_date: string | null;
  is_active: boolean;
}

export type AttendanceStatus = "present" | "absent" | "half_day" | "leave";

export interface Attendance {
  id: string;
  employee_id: string;
  project_id: string;
  attendance_date: string;
  status: AttendanceStatus;
}

export interface ProjectLaborCost {
  project_id: string;
  total_labor_cost: string;
  present_days: number;
  half_days: number;
  employee_count: number;
}

export type EquipmentStatus = "available" | "in_use" | "maintenance" | "retired";

export interface Equipment {
  id: string;
  name: string;
  equipment_type: string | null;
  status: EquipmentStatus;
  current_project_id: string | null;
  notes: string | null;
}

export interface MaintenanceReminder {
  equipment_id: string;
  equipment_name: string;
  next_due_date: string;
  days_until_due: number;
  is_overdue: boolean;
}
