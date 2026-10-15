import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  CompanySupplierConnection,
  DiscoverySupplier,
  DiscoverySupplierDetail,
} from "@/lib/marketplace-client-types";

export function useDiscoverSuppliers(filters: { search?: string; category?: string; area?: string }) {
  const { accessToken } = useAuth();
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.category) params.set("category", filters.category);
  if (filters.area) params.set("area", filters.area);
  const qs = params.toString();
  return useQuery({
    queryKey: ["marketplace-discovery", filters],
    queryFn: () => api.get<DiscoverySupplier[]>(`/marketplace/suppliers${qs ? `?${qs}` : ""}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useDiscoverSupplierDetail(id: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["marketplace-discovery-detail", id],
    queryFn: () => api.get<DiscoverySupplierDetail>(`/marketplace/suppliers/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useMarketplaceConnections() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["marketplace-connections"],
    queryFn: () => api.get<CompanySupplierConnection[]>("/marketplace/connections", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useConnectSupplier() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({
      supplierId,
      ...input
    }: {
      supplierId: string;
      link_existing_erp_supplier_id?: string;
      create_new_erp_supplier?: boolean;
      is_preferred?: boolean;
    }) => api.post<CompanySupplierConnection>(`/marketplace/suppliers/${supplierId}/connect`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketplace-discovery"] });
      queryClient.invalidateQueries({ queryKey: ["marketplace-connections"] });
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });
}
