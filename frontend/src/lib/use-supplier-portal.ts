import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, supplierApi } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import type {
  CommissionAgreement,
  CommissionDispute,
  CommissionInvoice,
  CommissionLedgerEntry,
} from "@/lib/commission-types";
import type {
  SupplierAuthResponse,
  SupplierDashboard,
  SupplierDeliveryUpdate,
  SupplierPortalDocument,
  SupplierInvitation,
  SupplierInvitationCreated,
  SupplierMembership,
  SupplierMembershipRole,
  SupplierOrder,
  SupplierOwnQuotation,
  SupplierPortalProduct,
  SupplierPortalProfile,
  SupplierQuotationHistoryItem,
  SupplierRfqDetail,
  SupplierRfqInboxItem,
} from "@/lib/supplier-portal-types";

export { ApiError };

// ---- auth --------------------------------------------------------------------------------

export function useSupplierLogin() {
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { email: string; password: string }) => supplierApi.post<SupplierAuthResponse>("/supplier-portal/auth/login", input),
  });
}

export function useSupplierSelectSupplier() {
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { refresh_token: string; marketplace_supplier_id: string }) =>
      supplierApi.post<{ access_token: string; refresh_token: string; active_supplier_id: string }>("/supplier-portal/auth/select-supplier", input),
  });
}

export function useSupplierInvitationInfo(token: string) {
  return useQuery({
    queryKey: ["supplier-invitation-info", token],
    queryFn: () => supplierApi.get(`/supplier-portal/auth/invitations/${token}`),
    enabled: !!token,
  });
}

export function useSupplierAcceptInvite() {
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { token: string; full_name: string; password: string }) => supplierApi.post("/supplier-portal/auth/accept-invite", input),
  });
}

// ---- dashboard / profile --------------------------------------------------------------------

export function useSupplierDashboard() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-dashboard"],
    queryFn: () => supplierApi.get<SupplierDashboard>("/supplier-portal/dashboard", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierPortalProfile() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-profile"],
    queryFn: () => supplierApi.get<SupplierPortalProfile>("/supplier-portal/profile", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useUpdateSupplierPortalProfile() {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: Partial<Pick<SupplierPortalProfile, "email" | "phone" | "website" | "address" | "notes" | "categories" | "coverage_areas">>) =>
      supplierApi.patch<SupplierPortalProfile>("/supplier-portal/profile", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-profile"] }),
  });
}

export function useSupplierDocuments() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-documents"],
    queryFn: () => supplierApi.get<SupplierPortalDocument[]>("/supplier-portal/profile/documents", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useUploadSupplierPortalDocument() {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: async (input: { file: File; title: string }) => {
      const body = new FormData();
      body.append("file", input.file);
      body.append("title", input.title);
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const res = await fetch(`${API_URL}/supplier-portal/profile/documents`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(res.status, Array.isArray(err.detail) ? "Please check the form fields" : err.detail ?? "Upload failed");
      }
      return res.json() as Promise<SupplierPortalDocument>;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-documents"] }),
  });
}

// ---- team ---------------------------------------------------------------------------------

export function useSupplierTeamMembers() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-team-members"],
    queryFn: () => supplierApi.get<SupplierMembership[]>("/supplier-portal/team/members", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierTeamInvitations() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-team-invitations"],
    queryFn: () => supplierApi.get<SupplierInvitation[]>("/supplier-portal/team/invitations", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useInviteSupplierTeamMember() {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { email: string; full_name?: string; role: SupplierMembershipRole }) =>
      supplierApi.post<SupplierInvitationCreated>("/supplier-portal/team/invitations", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-team-invitations"] }),
  });
}

function useMembershipAction(action: "suspend" | "revoke" | "reinstate") {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (membershipId: string) => supplierApi.post<SupplierMembership>(`/supplier-portal/team/members/${membershipId}/${action}`, {}, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-team-members"] }),
  });
}

export const useSuspendMember = () => useMembershipAction("suspend");
export const useRevokeMember = () => useMembershipAction("revoke");
export const useReinstateMember = () => useMembershipAction("reinstate");

export function useChangeMemberRole() {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ membershipId, role }: { membershipId: string; role: SupplierMembershipRole }) =>
      supplierApi.patch<SupplierMembership>(`/supplier-portal/team/members/${membershipId}/role`, { role }, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-team-members"] }),
  });
}

// ---- products -------------------------------------------------------------------------------

export function useSupplierProducts(filters: { search?: string; active_only?: boolean } = {}) {
  const { accessToken } = useSupplierAuth();
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.active_only) params.set("active_only", "true");
  return useQuery({
    queryKey: ["supplier-products", filters.search ?? "", filters.active_only ?? false],
    queryFn: () => supplierApi.get<SupplierPortalProduct[]>(`/supplier-portal/products?${params.toString()}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierPortalProduct(productId: string) {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-product", productId],
    queryFn: () => supplierApi.get<SupplierPortalProduct>(`/supplier-portal/products/${productId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!productId,
  });
}

export function useCreateSupplierPortalProduct() {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { name: string; category?: string; unit: string; price: string; minimum_order_quantity?: string; lead_time_days?: number }) =>
      supplierApi.post<SupplierPortalProduct>("/supplier-portal/products", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-products"] }),
  });
}

export function useUpdateSupplierPortalProduct(productId: string) {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: Partial<{ name: string; category: string; unit: string; price: string; minimum_order_quantity: string; lead_time_days: number; is_active: boolean }>) =>
      supplierApi.patch<SupplierPortalProduct>(`/supplier-portal/products/${productId}`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-products"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-product", productId] });
    },
  });
}

// ---- RFQs and quotations ----------------------------------------------------------------------

export function useSupplierRfqInbox(status?: string) {
  const { accessToken } = useSupplierAuth();
  const params = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["supplier-rfq-inbox", status ?? ""],
    queryFn: () => supplierApi.get<SupplierRfqInboxItem[]>(`/supplier-portal/rfqs${params}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierRfqDetail(rfqId: string) {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-rfq-detail", rfqId],
    queryFn: () => supplierApi.get<SupplierRfqDetail>(`/supplier-portal/rfqs/${rfqId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!rfqId,
  });
}

export function useDeclineRfqInvitation(rfqId: string) {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: () => supplierApi.post(`/supplier-portal/rfqs/${rfqId}/decline`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-rfq-inbox"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-rfq-detail", rfqId] });
    },
  });
}

export function useSubmitSupplierQuotation(rfqId: string) {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { delivery_days?: number; valid_until?: string; notes?: string; items: { rfq_item_id: string; rate: string }[] }) =>
      supplierApi.post<SupplierOwnQuotation>(`/supplier-portal/rfqs/${rfqId}/quotations`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-rfq-inbox"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-rfq-detail", rfqId] });
      queryClient.invalidateQueries({ queryKey: ["supplier-quotation-history"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-dashboard"] });
    },
  });
}

export function useSupplierQuotationHistory() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-quotation-history"],
    queryFn: () => supplierApi.get<SupplierQuotationHistoryItem[]>("/supplier-portal/quotations", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

// ---- orders and delivery updates ----------------------------------------------------------------

export function useSupplierOrders() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-orders"],
    queryFn: () => supplierApi.get<SupplierOrder[]>("/supplier-portal/orders", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierOrder(poId: string) {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-order", poId],
    queryFn: () => supplierApi.get<SupplierOrder>(`/supplier-portal/orders/${poId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!poId,
  });
}

export function useSupplierDeliveryUpdates(poId: string) {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-delivery-updates", poId],
    queryFn: () => supplierApi.get<SupplierDeliveryUpdate[]>(`/supplier-portal/orders/${poId}/delivery-updates`, accessToken ?? undefined),
    enabled: !!accessToken && !!poId,
  });
}

export function useSubmitDeliveryUpdate(poId: string) {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { external_reference: string; note?: string }) =>
      supplierApi.post<SupplierDeliveryUpdate>(`/supplier-portal/orders/${poId}/delivery-updates`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-delivery-updates", poId] });
      queryClient.invalidateQueries({ queryKey: ["supplier-dashboard"] });
    },
  });
}

// ---- commission statement ----------------------------------------------------------------------

export function useSupplierCommissionAgreements() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-commission-agreements"],
    queryFn: () => supplierApi.get<CommissionAgreement[]>("/supplier-portal/commissions/agreements", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierCommissionLedger() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-commission-ledger"],
    queryFn: () => supplierApi.get<CommissionLedgerEntry[]>("/supplier-portal/commissions/ledger", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierCommissionInvoices() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-commission-invoices"],
    queryFn: () => supplierApi.get<CommissionInvoice[]>("/supplier-portal/commissions/invoices", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierCommissionInvoice(invoiceId: string) {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-commission-invoice", invoiceId],
    queryFn: () => supplierApi.get<CommissionInvoice>(`/supplier-portal/commissions/invoices/${invoiceId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!invoiceId,
  });
}

// ---- PLAT-046: support desk ---------------------------------------------------------------------

export function useSupplierSupportTickets() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-support-tickets"],
    queryFn: () => supplierApi.get<import("@/lib/support-types").SupportTicketSummary[]>("/supplier-portal/support", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierSupportTicket(ticketId: string) {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-support-ticket", ticketId],
    queryFn: () => supplierApi.get<import("@/lib/support-types").SupportTicket>(`/supplier-portal/support/${ticketId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!ticketId,
  });
}

export function useCreateSupplierSupportTicket() {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { subject: string; category: string; priority?: string; message: string }) =>
      supplierApi.post("/supplier-portal/support", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-support-tickets"] }),
  });
}

export function useReplySupplierSupportTicket(ticketId: string) {
  const { accessToken } = useSupplierAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (body: string) => supplierApi.post(`/supplier-portal/support/${ticketId}/messages`, { body }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-support-ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["supplier-support-tickets"] });
    },
  });
}

export function useSupplierNotifications() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-portal-notifications"],
    queryFn: () => supplierApi.get<{ id: string; notification_type: string; title: string; body: string | null; link: string | null; is_read: boolean; created_at: string }[]>("/supplier-portal/notifications", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierCommissionDisputes() {
  const { accessToken } = useSupplierAuth();
  return useQuery({
    queryKey: ["supplier-commission-disputes"],
    queryFn: () => supplierApi.get<CommissionDispute[]>("/supplier-portal/commissions/disputes", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}
