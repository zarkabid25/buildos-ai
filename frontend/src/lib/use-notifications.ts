import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export type NotificationType =
  | "task_assigned"
  | "material_request_pending"
  | "purchase_order_pending"
  | "ai_proposal_pending";

export interface Notification {
  id: string;
  notification_type: NotificationType;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export function useNotifications(unreadOnly = false) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["notifications", unreadOnly ? "unread" : "all"],
    queryFn: () =>
      api.get<Notification[]>(
        `/notifications${unreadOnly ? "?unread_only=true" : ""}`,
        accessToken ?? undefined
      ),
    enabled: !!accessToken,
  });
}

export function useUnreadCount() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () =>
      api.get<{ unread_count: number }>("/notifications/unread-count", accessToken ?? undefined),
    enabled: !!accessToken,
    // The bell should feel live without the user having to refresh the page.
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationRead() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<Notification>(`/notifications/${id}/read`, {}, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
}

export function useMarkAllNotificationsRead() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ unread_count: number }>("/notifications/read-all", {}, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
}
