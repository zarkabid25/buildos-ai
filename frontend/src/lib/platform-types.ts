export interface PlatformAdmin {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface PlatformAuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  admin: PlatformAdmin;
}

export interface PlatformCompany {
  id: string;
  name: string;
  code: string;
  currency: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  suspended_at: string | null;
  created_at: string;
  user_count: number;
}

export interface PlatformCompanyList {
  total: number;
  companies: PlatformCompany[];
}

export interface PlatformDashboardStats {
  active_companies: number;
  suspended_companies: number;
  total_users: number;
  companies_created_last_30_days: number;
  monthly_recurring_revenue: number | null;
  new_leads: number | null;
  pending_supplier_verifications: number | null;
}
