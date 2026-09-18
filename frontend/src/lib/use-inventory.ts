import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  InventoryDashboard,
  Material,
  MaterialStockLevel,
  Warehouse,
} from "@/lib/inventory-types";

export function useMaterials() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["materials"],
    queryFn: () => api.get<Material[]>("/materials", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateMaterial() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; sku: string; unit: string; reorder_point?: number }) =>
      api.post<Material>("/materials", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["materials"] }),
  });
}

export function useWarehouses() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["warehouses"],
    queryFn: () => api.get<Warehouse[]>("/warehouses", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateWarehouse() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; location?: string }) =>
      api.post<Warehouse>("/warehouses", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["warehouses"] }),
  });
}

export function useInventoryDashboard() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["inventory", "dashboard"],
    queryFn: () => api.get<InventoryDashboard>("/inventory/dashboard", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useStockLevels() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["inventory", "stock"],
    queryFn: () => api.get<MaterialStockLevel[]>("/inventory/stock", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useStockIn() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      material_id: string;
      warehouse_id: string;
      quantity: string;
      reference?: string;
    }) => api.post("/inventory/stock-in", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}

export function useStockOut() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      material_id: string;
      warehouse_id: string;
      quantity: string;
      reference?: string;
    }) => api.post("/inventory/stock-out", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}
