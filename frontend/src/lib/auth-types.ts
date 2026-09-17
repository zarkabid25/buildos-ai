export type UserRole =
  | "super_admin"
  | "company_admin"
  | "project_manager"
  | "site_engineer"
  | "storekeeper"
  | "accountant"
  | "viewer";

export interface User {
  id: string;
  company_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}
