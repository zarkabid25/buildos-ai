import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  Supplier,
  SupplierContact,
  SupplierPerformance,
  SupplierTransaction,
} from "@/lib/supplier-types";

export function useSuppliers() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/suppliers", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateSupplier() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; phone?: string; email?: string; address?: string }) =>
      api.post<Supplier>("/suppliers", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
  });
}

export function useSupplierContacts(supplierId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["suppliers", supplierId, "contacts"],
    queryFn: () =>
      api.get<SupplierContact[]>(`/suppliers/${supplierId}/contacts`, accessToken ?? undefined),
    enabled: !!accessToken && !!supplierId,
  });
}

export function useAddSupplierContact(supplierId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; role?: string; phone?: string; email?: string }) =>
      api.post<SupplierContact>(`/suppliers/${supplierId}/contacts`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers", supplierId, "contacts"] });
    },
  });
}

export function useSupplierTransactions(supplierId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["suppliers", supplierId, "transactions"],
    queryFn: () =>
      api.get<SupplierTransaction[]>(`/suppliers/${supplierId}/transactions`, accessToken ?? undefined),
    enabled: !!accessToken && !!supplierId,
  });
}

export function useSupplierPerformance(supplierId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["suppliers", supplierId, "performance"],
    queryFn: () =>
      api.get<SupplierPerformance>(`/suppliers/${supplierId}/performance`, accessToken ?? undefined),
    enabled: !!accessToken && !!supplierId,
  });
}
