import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type { SupportTicket, SupportTicketPriority, SupportTicketStatus, SupportTicketSummary } from "@/lib/support-types";

export interface SupplierApplication {
  id: string;
  business_name: string;
  contact_name: string;
  email: string;
  phone: string | null;
  business_registration_info: string | null;
  categories: string[];
  delivery_locations: string[];
  business_description: string | null;
  status: "pending" | "approved" | "rejected";
  review_notes: string | null;
  reviewed_by_staff_name: string | null;
  reviewed_at: string | null;
  marketplace_supplier_id: string | null;
  document_count: number;
  created_at: string;
}

export interface SupplierApplicationDocument {
  id: string;
  title: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface PlatformNotification {
  id: string;
  notification_type: string;
  title: string;
  body: string | null;
  link: string | null;
  dismissed_at: string | null;
  created_at: string;
}

// ---- Supplier applications ---------------------------------------------------------------------

export function useSupplierApplications(status?: string) {
  const { accessToken } = usePlatformAuth();
  const params = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["platform-supplier-applications", status ?? ""],
    queryFn: () => platformApi.get<SupplierApplication[]>(`/platform/supplier-applications${params}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupplierApplication(applicationId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-supplier-application", applicationId],
    queryFn: () => platformApi.get<SupplierApplication>(`/platform/supplier-applications/${applicationId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!applicationId,
  });
}

export function useSupplierApplicationDocuments(applicationId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-supplier-application-documents", applicationId],
    queryFn: () => platformApi.get<SupplierApplicationDocument[]>(`/platform/supplier-applications/${applicationId}/documents`, accessToken ?? undefined),
    enabled: !!accessToken && !!applicationId,
  });
}

export function useReviewSupplierApplication(applicationId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { approve: boolean; review_notes: string }) =>
      platformApi.post<SupplierApplication>(`/platform/supplier-applications/${applicationId}/review`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-supplier-applications"] });
      queryClient.invalidateQueries({ queryKey: ["platform-supplier-application", applicationId] });
    },
  });
}

// ---- Support desk (staff side) ------------------------------------------------------------------

export function useAllSupportTickets(status?: SupportTicketStatus) {
  const { accessToken } = usePlatformAuth();
  const params = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["platform-support-tickets", status ?? ""],
    queryFn: () => platformApi.get<SupportTicketSummary[]>(`/platform/support${params}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupportTicketForStaff(ticketId: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-support-ticket", ticketId],
    queryFn: () => platformApi.get<SupportTicket>(`/platform/support/${ticketId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!ticketId,
  });
}

export function useUpdateSupportTicket(ticketId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { status?: SupportTicketStatus; priority?: SupportTicketPriority; assigned_staff_id?: string }) =>
      platformApi.patch<SupportTicket>(`/platform/support/${ticketId}`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-support-ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["platform-support-tickets"] });
    },
  });
}

export function useReplyAsStaff(ticketId: string) {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ body, is_internal }: { body: string; is_internal: boolean }) =>
      platformApi.post<SupportTicket>(`/platform/support/${ticketId}/messages?is_internal=${is_internal}`, { body }, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-support-ticket", ticketId] }),
  });
}

// ---- Platform notification feed -----------------------------------------------------------------

export function usePlatformNotificationFeed() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-notification-feed"],
    queryFn: () => platformApi.get<PlatformNotification[]>("/platform/notifications", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useDismissPlatformNotification() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => platformApi.post(`/platform/notifications/${id}/dismiss`, {}, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-notification-feed"] }),
  });
}
