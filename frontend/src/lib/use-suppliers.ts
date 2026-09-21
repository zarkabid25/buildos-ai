import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Supplier, SupplierContact } from "@/lib/supplier-types";

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
