import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type {
  AdminInvoice,
  BillingOverview,
  CompanyBillingSummary,
  LegacyEntitlement,
  PaymentSubmission,
  RevenueDashboard,
  Subscription,
  SubscriptionEvent,
  SubscriptionPlan,
} from "@/lib/billing-types";

export function usePlatformPlans(includeInactive = false) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-billing-plans", includeInactive],
    queryFn: () => platformApi.get<SubscriptionPlan[]>(`/platform/billing/plans?include_inactive=${includeInactive}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreatePlatformPlan() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: {
      name: string;
      description?: string;
      trial_days: number;
      max_projects?: number | null;
      max_team_members?: number | null;
      ai_monthly_messages?: number | null;
      storage_gb?: number | null;
      marketplace_included: boolean;
      prices: { currency: string; billing_period: "monthly" | "annual"; amount: string }[];
    }) => platformApi.post<SubscriptionPlan>("/platform/billing/plans", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-billing-plans"] }),
  });
}

export function useUpdatePlatformPlan() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ planId, ...input }: { planId: string; is_active?: boolean; max_projects?: number | null; max_team_members?: number | null; marketplace_included?: boolean }) =>
      platformApi.patch<SubscriptionPlan>(`/platform/billing/plans/${planId}`, input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-billing-plans"] }),
  });
}

export function useBillingOverview() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-billing-overview"],
    queryFn: () => platformApi.get<BillingOverview>("/platform/billing/overview", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function usePendingPayments() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-pending-payments"],
    queryFn: () => platformApi.get<PaymentSubmission[]>("/platform/billing/payments/pending", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useVerifyPayment() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (submissionId: string) => platformApi.post<PaymentSubmission>(`/platform/billing/payments/${submissionId}/verify`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-pending-payments"] });
      queryClient.invalidateQueries({ queryKey: ["platform-billing-overview"] });
    },
  });
}

export function useRejectPayment() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ submissionId, reason }: { submissionId: string; reason: string }) =>
      platformApi.post<PaymentSubmission>(`/platform/billing/payments/${submissionId}/reject`, { reason }, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-pending-payments"] }),
  });
}

export function useBillingCompanies(filters: { search?: string; plan_id?: string; status?: string }) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.plan_id) params.set("plan_id", filters.plan_id);
  if (filters.status) params.set("status", filters.status);
  return useQuery({
    queryKey: ["platform-billing-companies", filters.search ?? "", filters.plan_id ?? "", filters.status ?? ""],
    queryFn: () => platformApi.get<CompanyBillingSummary[]>(`/platform/billing/companies?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCompanyBillingSummary(companyId: string | undefined) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-billing-company-summary", companyId],
    queryFn: () => platformApi.get<CompanyBillingSummary>(`/platform/billing/companies/${companyId}/summary`, accessToken ?? undefined),
    enabled: !!accessToken && !!companyId,
  });
}

export function useAdminInvoices(filters: { company_id?: string; status?: string; date_from?: string; date_to?: string }) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams();
  if (filters.company_id) params.set("company_id", filters.company_id);
  if (filters.status) params.set("status", filters.status);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  return useQuery({
    queryKey: ["platform-billing-invoices", filters.company_id ?? "", filters.status ?? "", filters.date_from ?? "", filters.date_to ?? ""],
    queryFn: () => platformApi.get<AdminInvoice[]>(`/platform/billing/invoices?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useRevenueDashboard() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-billing-revenue"],
    queryFn: () => platformApi.get<RevenueDashboard>("/platform/billing/revenue", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCompanySubscriptions(companyId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-company-subscriptions", companyId],
    queryFn: () => platformApi.get<Subscription[]>(`/platform/billing/companies/${companyId}/subscriptions`, accessToken ?? undefined),
    enabled: !!accessToken && !!companyId,
  });
}

export function useCompanySubscriptionEvents(companyId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-company-events", companyId],
    queryFn: () => platformApi.get<SubscriptionEvent[]>(`/platform/billing/companies/${companyId}/events`, accessToken ?? undefined),
    enabled: !!accessToken && !!companyId,
  });
}

export function useEnterGracePeriod(companyId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (subscriptionId: string) => platformApi.post<Subscription>(`/platform/billing/companies/${companyId}/subscriptions/${subscriptionId}/grace-period`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-company-subscriptions", companyId] });
      queryClient.invalidateQueries({ queryKey: ["platform-billing-company-summary", companyId] });
      queryClient.invalidateQueries({ queryKey: ["platform-company-events", companyId] });
    },
  });
}

export function useExpireSubscription(companyId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (subscriptionId: string) => platformApi.post<Subscription>(`/platform/billing/companies/${companyId}/subscriptions/${subscriptionId}/expire`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-company-subscriptions", companyId] });
      queryClient.invalidateQueries({ queryKey: ["platform-billing-company-summary", companyId] });
      queryClient.invalidateQueries({ queryKey: ["platform-company-events", companyId] });
    },
  });
}

export function useLegacyEntitlements() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-legacy-entitlements"],
    queryFn: () => platformApi.get<LegacyEntitlement[]>("/platform/billing/legacy-entitlements", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}
