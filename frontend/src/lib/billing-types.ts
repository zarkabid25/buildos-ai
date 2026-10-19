export type BillingPeriod = "monthly" | "annual";
export type SubscriptionStatus = "trialing" | "active" | "pending_payment" | "grace_period" | "cancelled" | "expired";
export type InvoiceStatus = "draft" | "pending" | "paid" | "rejected" | "void";
export type PaymentSubmissionStatus = "pending" | "verified" | "rejected";

export interface PlanPrice {
  id: string;
  currency: string;
  billing_period: BillingPeriod;
  amount: string;
  effective_from: string;
  is_current: boolean;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  description: string | null;
  trial_days: number;
  max_projects: number | null;
  max_team_members: number | null;
  ai_monthly_messages: number | null;
  storage_gb: number | null;
  marketplace_included: boolean;
  features: Record<string, unknown> | null;
  is_active: boolean;
  prices: PlanPrice[];
  created_at: string;
}

export interface Subscription {
  id: string;
  company_id: string;
  plan_id: string;
  plan_name: string;
  status: SubscriptionStatus;
  billing_period: BillingPeriod;
  trial_ends_at: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  grace_period_ends_at: string | null;
  cancelled_at: string | null;
  created_at: string;
}

export interface SubscriptionEvent {
  id: string;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  summary: string;
  actor_staff_name: string | null;
  actor_user_name: string | null;
  created_at: string;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: string;
  amount: string;
}

export interface PaymentSubmission {
  id: string;
  invoice_id: string;
  company_id: string;
  submitted_by_user_id: string;
  amount: string;
  method: string;
  reference: string | null;
  proof_filename: string;
  status: PaymentSubmissionStatus;
  verified_by_staff_id: string | null;
  verified_by_staff_name: string | null;
  verified_at: string | null;
  rejection_reason: string | null;
  created_at: string;
}

export interface Invoice {
  id: string;
  company_id: string;
  subscription_id: string;
  invoice_number: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: string;
  discount_amount: string;
  tax_amount: string;
  total_amount: string;
  billing_period_start: string;
  billing_period_end: string;
  due_date: string;
  paid_at: string | null;
  items: InvoiceLineItem[];
  payments: PaymentSubmission[];
  created_at: string;
}

export interface Entitlements {
  source: "subscription" | "legacy" | "none";
  plan_name: string | null;
  max_projects: number | null;
  max_team_members: number | null;
  ai_monthly_messages: number | null;
  storage_gb: number | null;
  marketplace_included: boolean;
  current_projects: number;
  current_team_members: number;
  billing_status: SubscriptionStatus | null;
  current_period_end: string | null;
  grace_period_ends_at: string | null;
}

export interface LegacyEntitlement {
  id: string;
  company_id: string;
  company_name: string | null;
  reason: string;
  granted_by_staff_id: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface BillingOverview {
  active_subscriptions: number;
  trialing_subscriptions: number;
  in_grace_period: number;
  pending_payments: number;
  total_revenue_collected: string;
}
