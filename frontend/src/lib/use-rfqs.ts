import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { CashSummary, ClientReceipt, PaymentMethod, Rfq, RfqSummary, SupplierPayment } from "@/lib/rfq-types";

export function useRfqs() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["rfqs"],
    queryFn: () => api.get<RfqSummary[]>("/rfqs", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useRfq(id: string | null) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["rfqs", id],
    queryFn: () => api.get<Rfq>(`/rfqs/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

function useRfqMutation<TInput>(request: (input: TInput, token?: string) => Promise<Rfq>) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TInput) => request(input, accessToken ?? undefined),
    onSuccess: (rfq) => {
      queryClient.setQueryData(["rfqs", rfq.id], rfq);
      queryClient.invalidateQueries({ queryKey: ["rfqs"], exact: true });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["material-requests"] });
    },
  });
}

export function useCreateRfq() {
  return useRfqMutation(
    (
      input: {
        title: string;
        project_id?: string;
        material_request_id?: string;
        response_due?: string;
        items: { material_id: string; quantity: string }[];
        supplier_ids: string[];
      },
      token
    ) => api.post<Rfq>("/rfqs", input, token)
  );
}

export function useRecordQuotation(rfqId: string) {
  return useRfqMutation(
    (
      input: {
        supplier_id: string;
        delivery_days?: number;
        valid_until?: string;
        notes?: string;
        items: { rfq_item_id: string; rate: string }[];
      },
      token
    ) => api.post<Rfq>(`/rfqs/${rfqId}/quotations`, input, token)
  );
}

export function useAwardRfq(rfqId: string) {
  return useRfqMutation((quotationId: string, token) =>
    api.post<Rfq>(`/rfqs/${rfqId}/award`, { quotation_id: quotationId }, token)
  );
}

export function useCancelRfq(rfqId: string) {
  return useRfqMutation((_: void, token) => api.post<Rfq>(`/rfqs/${rfqId}/cancel`, {}, token));
}

// ---- Payments ---------------------------------------------------------------

export function useCashSummary() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["payments", "summary"],
    queryFn: () => api.get<CashSummary>("/payments/summary", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierPayments() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["payments", "supplier"],
    queryFn: () => api.get<SupplierPayment[]>("/payments/supplier", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useClientReceipts() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["payments", "client"],
    queryFn: () => api.get<ClientReceipt[]>("/payments/client", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

interface PaymentInput {
  amount: string;
  method: PaymentMethod;
  reference?: string;
  notes?: string;
}

export function useRecordSupplierPayment() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PaymentInput & { purchase_order_id: string; paid_on: string }) =>
      api.post<SupplierPayment>("/payments/supplier", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useRecordClientReceipt() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PaymentInput & { project_id: string; received_on: string }) =>
      api.post<ClientReceipt>("/payments/client", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["payments"] }),
  });
}
