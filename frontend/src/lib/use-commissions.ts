import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type {
  CommissionAgreement,
  CommissionBasis,
  CommissionDispute,
  CommissionDisputeStatus,
  CommissionInvoice,
  CommissionInvoiceStatus,
  CommissionLedgerEntry,
  CommissionRevenueDashboard,
} from "@/lib/commission-types";

// ---- PLAT-033: agreements -------------------------------------------------------------------

export function useCommissionAgreements(marketplaceSupplierId: string | undefined) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["commission-agreements", marketplaceSupplierId],
    queryFn: () => platformApi.get<CommissionAgreement[]>(`/platform/commissions/suppliers/${marketplaceSupplierId}/agreements`, accessToken ?? undefined),
    enabled: !!accessToken && !!marketplaceSupplierId,
  });
}

export function useAllActiveAgreements() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["commission-agreements-active"],
    queryFn: () => platformApi.get<CommissionAgreement[]>("/platform/commissions/agreements", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateCommissionAgreement(marketplaceSupplierId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { basis: CommissionBasis; rate?: string; fixed_fee_amount?: string; notes?: string }) =>
      platformApi.post<CommissionAgreement>(`/platform/commissions/suppliers/${marketplaceSupplierId}/agreements`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commission-agreements", marketplaceSupplierId] });
      queryClient.invalidateQueries({ queryKey: ["commission-agreements-active"] });
    },
  });
}

export function useCancelCommissionAgreement(marketplaceSupplierId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (agreementId: string) => platformApi.post<CommissionAgreement>(`/platform/commissions/agreements/${agreementId}/cancel`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commission-agreements", marketplaceSupplierId] });
      queryClient.invalidateQueries({ queryKey: ["commission-agreements-active"] });
    },
  });
}

// ---- PLAT-034: ledger ------------------------------------------------------------------------

export function useCommissionLedger(filters: { marketplace_supplier_id?: string; purchase_order_id?: string }) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams();
  if (filters.marketplace_supplier_id) params.set("marketplace_supplier_id", filters.marketplace_supplier_id);
  if (filters.purchase_order_id) params.set("purchase_order_id", filters.purchase_order_id);
  return useQuery({
    queryKey: ["commission-ledger", filters.marketplace_supplier_id ?? "", filters.purchase_order_id ?? ""],
    queryFn: () => platformApi.get<CommissionLedgerEntry[]>(`/platform/commissions/ledger?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function usePostCommissionAdjustment() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { purchase_order_id: string; marketplace_supplier_id: string; amount: string; note: string }) =>
      platformApi.post<CommissionLedgerEntry>("/platform/commissions/ledger/adjustments", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["commission-ledger"] }),
  });
}

// ---- PLAT-036: disputes -----------------------------------------------------------------------

export function useCommissionDisputes(filters: { marketplace_supplier_id?: string; status?: CommissionDisputeStatus }) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams();
  if (filters.marketplace_supplier_id) params.set("marketplace_supplier_id", filters.marketplace_supplier_id);
  if (filters.status) params.set("status", filters.status);
  return useQuery({
    queryKey: ["commission-disputes", filters.marketplace_supplier_id ?? "", filters.status ?? ""],
    queryFn: () => platformApi.get<CommissionDispute[]>(`/platform/commissions/disputes?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useRaiseDispute() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { ledger_entry_id: string; reason: string }) => platformApi.post<CommissionDispute>("/platform/commissions/disputes", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commission-disputes"] });
      queryClient.invalidateQueries({ queryKey: ["commission-ledger"] });
    },
  });
}

export function useReviewDispute() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ disputeId, approve, resolution_notes }: { disputeId: string; approve: boolean; resolution_notes: string }) =>
      platformApi.post<CommissionDispute>(`/platform/commissions/disputes/${disputeId}/review`, { approve, resolution_notes }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commission-disputes"] });
      queryClient.invalidateQueries({ queryKey: ["commission-ledger"] });
      queryClient.invalidateQueries({ queryKey: ["commission-revenue"] });
    },
  });
}

// ---- PLAT-035: commission invoices and payments ------------------------------------------------

export function useCommissionInvoices(filters: { marketplace_supplier_id?: string; status?: CommissionInvoiceStatus }) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams();
  if (filters.marketplace_supplier_id) params.set("marketplace_supplier_id", filters.marketplace_supplier_id);
  if (filters.status) params.set("status", filters.status);
  return useQuery({
    queryKey: ["commission-invoices", filters.marketplace_supplier_id ?? "", filters.status ?? ""],
    queryFn: () => platformApi.get<CommissionInvoice[]>(`/platform/commissions/invoices?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useGenerateCommissionInvoice() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { marketplace_supplier_id: string; period_start: string; period_end: string; due_date: string }) =>
      platformApi.post<CommissionInvoice>("/platform/commissions/invoices", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commission-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["commission-ledger"] });
    },
  });
}

export function useRecordCommissionPayment(invoiceId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { amount: string; paid_on: string; method?: string; receipt_reference?: string; notes?: string }) =>
      platformApi.post<CommissionInvoice>(`/platform/commissions/invoices/${invoiceId}/payments`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commission-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["commission-revenue"] });
    },
  });
}

// ---- PLAT-037: revenue dashboard ----------------------------------------------------------------

export function useCommissionRevenueDashboard() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["commission-revenue"],
    queryFn: () => platformApi.get<CommissionRevenueDashboard>("/platform/commissions/revenue", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}
