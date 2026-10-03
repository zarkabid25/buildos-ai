import type { UserRole } from "@/lib/auth-types";

export interface Company {
  id: string;
  name: string;
  code: string;
  currency: string;
  unit_system: "metric" | "imperial";
  address: string | null;
  phone: string | null;
  email: string | null;
  logo_url: string | null;
}

export interface CompanyUpdate {
  name?: string;
  currency?: string;
  unit_system?: "metric" | "imperial";
  address?: string | null;
  phone?: string | null;
  email?: string | null;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  super_admin: "Super admin",
  company_admin: "Company admin",
  project_manager: "Project manager",
  site_engineer: "Site engineer",
  storekeeper: "Storekeeper",
  accountant: "Accountant",
  viewer: "Viewer",
};
