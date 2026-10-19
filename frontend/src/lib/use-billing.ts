import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { BillingPeriod, Entitlements, Invoice, PaymentSubmission, Subscription, SubscriptionEvent, SubscriptionPlan } from "@/lib/billing-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function useAvailablePlans() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["billing-plans"],
    queryFn: () => api.get<SubscriptionPlan[]>("/billing/plans", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCurrentSubscription() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["billing-subscription"],
    queryFn: () => api.get<Subscription | null>("/billing/subscription", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateSubscription() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { plan_id: string; billing_period: BillingPeriod; currency?: string }) =>
      api.post<Subscription>("/billing/subscriptions", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing-subscription"] });
      queryClient.invalidateQueries({ queryKey: ["billing-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["billing-entitlements"] });
    },
  });
}

export function useChangePlan(subscriptionId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (plan_id: string) => api.post<Subscription>(`/billing/subscriptions/${subscriptionId}/change-plan`, { plan_id }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing-subscription"] });
      queryClient.invalidateQueries({ queryKey: ["billing-entitlements"] });
      queryClient.invalidateQueries({ queryKey: ["marketplace-status"] });
    },
  });
}

export function useCancelSubscription(subscriptionId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Subscription>(`/billing/subscriptions/${subscriptionId}/cancel`, {}, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["billing-subscription"] }),
  });
}

export function useRenewSubscription(subscriptionId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: () => api.post<Invoice>(`/billing/subscriptions/${subscriptionId}/renew`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["billing-events", subscriptionId] });
    },
  });
}

export function useSubscriptionEvents(subscriptionId: string | undefined) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["billing-events", subscriptionId],
    queryFn: () => api.get<SubscriptionEvent[]>(`/billing/subscriptions/${subscriptionId}/events`, accessToken ?? undefined),
    enabled: !!accessToken && !!subscriptionId,
  });
}

export function useInvoices() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["billing-invoices"],
    queryFn: () => api.get<Invoice[]>("/billing/invoices", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useInvoice(id: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["billing-invoice", id],
    queryFn: () => api.get<Invoice>(`/billing/invoices/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useEntitlements() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["billing-entitlements"],
    queryFn: () => api.get<Entitlements>("/billing/entitlements", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSubmitPayment(invoiceId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: async (input: { amount: string; reference?: string; file: File }) => {
      const body = new FormData();
      body.append("file", input.file);
      body.append("amount", input.amount);
      if (input.reference) body.append("reference", input.reference);
      const res = await fetch(`${API_URL}/billing/invoices/${invoiceId}/payments`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = Array.isArray(err.detail) ? "Please check the form fields" : err.detail;
        throw new ApiError(res.status, detail ?? "Submission failed");
      }
      return res.json() as Promise<PaymentSubmission>;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["billing-invoice", invoiceId] }),
  });
}

export async function fetchPaymentProofBlob(submissionId: string, accessToken: string): Promise<Blob> {
  const res = await fetch(`${API_URL}/billing/payments/${submissionId}/proof`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new ApiError(res.status, "Could not load proof");
  return res.blob();
}
