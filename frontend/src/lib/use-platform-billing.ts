import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type { BillingOverview, LegacyEntitlement, PaymentSubmission, Subscription, SubscriptionEvent, SubscriptionPlan } from "@/lib/billing-types";

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

export function useLegacyEntitlements() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-legacy-entitlements"],
    queryFn: () => platformApi.get<LegacyEntitlement[]>("/platform/billing/legacy-entitlements", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}
