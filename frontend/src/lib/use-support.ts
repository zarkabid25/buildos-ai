import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SupportTicket, SupportTicketCategory, SupportTicketPriority, SupportTicketSummary } from "@/lib/support-types";

export function useSupportTickets() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["support-tickets"],
    queryFn: () => api.get<SupportTicketSummary[]>("/support", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useSupportTicket(ticketId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["support-ticket", ticketId],
    queryFn: () => api.get<SupportTicket>(`/support/${ticketId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!ticketId,
  });
}

export function useCreateSupportTicket() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { subject: string; category: SupportTicketCategory; priority?: SupportTicketPriority; message: string }) =>
      api.post<SupportTicket>("/support", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["support-tickets"] }),
  });
}

export function useReplySupportTicket(ticketId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (body: string) => api.post<SupportTicket>(`/support/${ticketId}/messages`, { body }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["support-ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["support-tickets"] });
    },
  });
}
