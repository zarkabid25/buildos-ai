export type PlatformStaffRole = "owner" | "admin" | "support";

export interface PlatformAdmin {
  id: string;
  email: string;
  full_name: string;
  role: PlatformStaffRole;
  is_active: boolean;
}

export interface PlatformAuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  admin: PlatformAdmin;
}

export type CompanyOnboardingStatus = "pending" | "approved";

export interface PlatformCompany {
  id: string;
  name: string;
  code: string;
  currency: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  suspended_at: string | null;
  onboarding_status: CompanyOnboardingStatus;
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
  pending_approval_companies: number;
  total_users: number;
  companies_created_last_30_days: number;
  monthly_recurring_revenue: number | null;
  new_leads: number | null;
  pending_supplier_verifications: number | null;
}

export interface PlatformInvitation {
  id: string;
  email: string;
  full_name: string | null;
  role: PlatformStaffRole;
  invited_by_name: string | null;
  created_at: string;
  expires_at: string;
  expired: boolean;
}

export interface PlatformInvitationCreated extends PlatformInvitation {
  token: string;
}

export interface PlatformInvitationInfo {
  email: string;
  full_name: string | null;
  role: PlatformStaffRole;
}

export interface PlatformAuditEntry {
  id: string;
  created_at: string;
  actor_id: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  summary: string;
  details: Record<string, unknown> | null;
}
