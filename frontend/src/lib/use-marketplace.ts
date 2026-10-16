import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type {
  CompanyRfqDetail,
  CompanyRfqSummary,
  MarketplaceCompanyLink,
  MarketplaceContact,
  MarketplaceDocument,
  MarketplaceProduct,
  MarketplaceSupplier,
  MarketplaceSupplierCreated,
  MarketplaceSupplierDetail,
  MarketplaceSupplierList,
  MarketplaceSupplierStatus,
  SupplierMatch,
} from "@/lib/marketplace-types";
import type { PlatformAuditEntry } from "@/lib/platform-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function useMarketplaceSuppliers(filters: {
  search?: string;
  category?: string;
  area?: string;
  verification_status?: MarketplaceSupplierStatus;
}) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.category) params.set("category", filters.category);
  if (filters.area) params.set("area", filters.area);
  if (filters.verification_status) params.set("verification_status", filters.verification_status);
  const qs = params.toString();
  return useQuery({
    queryKey: ["marketplace-suppliers", filters],
    queryFn: () =>
      platformApi.get<MarketplaceSupplierList>(`/platform/marketplace/suppliers${qs ? `?${qs}` : ""}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useMarketplaceSupplier(id: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["marketplace-supplier", id],
    queryFn: () => platformApi.get<MarketplaceSupplierDetail>(`/platform/marketplace/suppliers/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useCreateMarketplaceSupplier() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: {
      name: string;
      legal_name?: string;
      email?: string;
      phone?: string;
      website?: string;
      address?: string;
      notes?: string;
      categories?: string[];
      coverage_areas?: string[];
    }) => platformApi.post<MarketplaceSupplierCreated>("/platform/marketplace/suppliers", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["marketplace-suppliers"] }),
  });
}

export function useUpdateMarketplaceSupplier() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ id, ...input }: { id: string; [key: string]: unknown }) =>
      platformApi.patch<MarketplaceSupplier>(`/platform/marketplace/suppliers/${id}`, input, accessToken ?? undefined),
    onSuccess: (supplier) => {
      queryClient.invalidateQueries({ queryKey: ["marketplace-suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["marketplace-supplier", supplier.id] });
    },
  });
}

export function useSetVerificationStatus() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ id, status, reason }: { id: string; status: MarketplaceSupplierStatus; reason?: string }) =>
      platformApi.post<MarketplaceSupplier>(`/platform/marketplace/suppliers/${id}/verification`, { status, reason }, accessToken ?? undefined),
    onSuccess: (supplier) => {
      queryClient.invalidateQueries({ queryKey: ["marketplace-suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["marketplace-supplier", supplier.id] });
      queryClient.invalidateQueries({ queryKey: ["marketplace-supplier-activity", supplier.id] });
    },
  });
}

export function useMarketplaceSupplierActivity(id: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["marketplace-supplier-activity", id],
    queryFn: () => platformApi.get<PlatformAuditEntry[]>(`/platform/marketplace/suppliers/${id}/activity`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useAddMarketplaceContact() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ supplierId, ...input }: { supplierId: string; name: string; role?: string; email?: string; phone?: string; is_primary?: boolean }) =>
      platformApi.post<MarketplaceContact>(`/platform/marketplace/suppliers/${supplierId}/contacts`, input, accessToken ?? undefined),
    onSuccess: (_c, vars) => queryClient.invalidateQueries({ queryKey: ["marketplace-supplier", vars.supplierId] }),
  });
}

export function useAddMarketplaceProduct() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({
      supplierId,
      ...input
    }: {
      supplierId: string;
      name: string;
      category?: string;
      unit: string;
      price: string;
      minimum_order_quantity?: string;
      lead_time_days?: number;
    }) => platformApi.post<MarketplaceProduct>(`/platform/marketplace/suppliers/${supplierId}/products`, input, accessToken ?? undefined),
    onSuccess: (_p, vars) => queryClient.invalidateQueries({ queryKey: ["marketplace-supplier", vars.supplierId] }),
  });
}

export function useUploadMarketplaceDocument() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: async ({ supplierId, file, title }: { supplierId: string; file: File; title: string }) => {
      const body = new FormData();
      body.append("file", file);
      body.append("title", title);
      const res = await fetch(`${API_URL}/platform/marketplace/suppliers/${supplierId}/documents`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = Array.isArray(err.detail) ? "Please check the form fields" : err.detail;
        throw new ApiError(res.status, detail ?? "Upload failed");
      }
      return res.json() as Promise<MarketplaceDocument>;
    },
    onSuccess: (_d, vars) => queryClient.invalidateQueries({ queryKey: ["marketplace-supplier", vars.supplierId] }),
  });
}

export async function fetchMarketplaceDocumentBlob(supplierId: string, documentId: string, accessToken: string): Promise<Blob> {
  const res = await fetch(`${API_URL}/platform/marketplace/suppliers/${supplierId}/documents/${documentId}/download`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new ApiError(res.status, "Could not load document");
  return res.blob();
}

export function useMarketplaceCompanyLinks(supplierId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["marketplace-company-links", supplierId],
    queryFn: () => platformApi.get<MarketplaceCompanyLink[]>(`/platform/marketplace/suppliers/${supplierId}/company-links`, accessToken ?? undefined),
    enabled: !!accessToken && !!supplierId,
  });
}

export function useLinkMarketplaceCompany() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ supplierId, ...input }: { supplierId: string; company_id: string; notes?: string }) =>
      platformApi.post<MarketplaceCompanyLink>(`/platform/marketplace/suppliers/${supplierId}/company-links`, input, accessToken ?? undefined),
    onSuccess: (_l, vars) => queryClient.invalidateQueries({ queryKey: ["marketplace-company-links", vars.supplierId] }),
  });
}

// ---- Matching UI (Phase 4.1 Task 2) ----------------------------------------------------

export function useCompanyRfqs(companyId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-company-rfqs", companyId],
    queryFn: () => platformApi.get<CompanyRfqSummary[]>(`/platform/marketplace/companies/${companyId}/rfqs`, accessToken ?? undefined),
    enabled: !!accessToken && !!companyId,
  });
}

export function useCompanyRfqDetail(companyId: string, rfqId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-company-rfq", companyId, rfqId],
    queryFn: () => platformApi.get<CompanyRfqDetail>(`/platform/marketplace/companies/${companyId}/rfqs/${rfqId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!companyId && !!rfqId,
  });
}

export function useSupplierMatch(companyId: string, materialId: string, area?: string) {
  const { accessToken } = usePlatformAuth();
  const params = new URLSearchParams({ material_id: materialId });
  if (area) params.set("area", area);
  return useQuery({
    queryKey: ["platform-marketplace-match", companyId, materialId, area],
    queryFn: () => platformApi.get<SupplierMatch[]>(`/platform/marketplace/companies/${companyId}/match?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken && !!companyId && !!materialId,
  });
}

export function useAssistInviteSuppliers(companyId: string, rfqId: string) {
  const { accessToken } = usePlatformAuth();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (marketplace_supplier_ids: string[]) =>
      platformApi.post(`/platform/marketplace/companies/${companyId}/rfqs/${rfqId}/invite-suppliers`, { marketplace_supplier_ids }, accessToken ?? undefined),
  });
}
