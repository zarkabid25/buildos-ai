import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { MaterialRequest, PurchaseOrder } from "@/lib/procurement-types";

export function useMaterialRequests() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["material-requests"],
    queryFn: () => api.get<MaterialRequest[]>("/material-requests", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateMaterialRequest() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      project_id: string;
      notes?: string;
      items: { material_id: string; quantity: string }[];
    }) => api.post<MaterialRequest>("/material-requests", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["material-requests"] }),
  });
}

export function usePurchaseOrders() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["purchase-orders"],
    queryFn: () => api.get<PurchaseOrder[]>("/purchase-orders", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreatePurchaseOrder() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      supplier_id: string;
      project_id?: string;
      material_request_id?: string;
      items: { material_id: string; quantity: string; rate: string }[];
    }) => api.post<PurchaseOrder>("/purchase-orders", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["material-requests"] });
    },
  });
}

export function useApprovePurchaseOrder() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (poId: string) =>
      api.post<PurchaseOrder>(`/purchase-orders/${poId}/approve`, {}, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["purchase-orders"] }),
  });
}

export function useReceiveGoods() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      poId,
      warehouse_id,
      items,
    }: {
      poId: string;
      warehouse_id: string;
      items: { purchase_order_item_id: string; quantity_received: string }[];
    }) =>
      api.post(`/purchase-orders/${poId}/goods-receipts`, { warehouse_id, items }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}
