import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { User, UserRole } from "@/lib/auth-types";
import type { Company, CompanyUpdate } from "@/lib/settings-types";

export function useCompany() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["company"],
    queryFn: () => api.get<Company>("/companies/me", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useUpdateCompany() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: CompanyUpdate) => api.patch<Company>("/companies/me", input, accessToken ?? undefined),
    // Currency shows up in amounts everywhere, so refresh everything, not just the company.
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

export function useUpdateMe() {
  const { accessToken, updateUser } = useAuth();
  return useMutation({
    mutationFn: (input: { full_name: string }) => api.patch<User>("/auth/me", input, accessToken ?? undefined),
    onSuccess: (user) => updateUser(user),
  });
}

export function useChangePassword() {
  const { accessToken } = useAuth();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { current_password: string; new_password: string }) =>
      api.post<void>("/auth/me/password", input, accessToken ?? undefined),
  });
}

export function useUsers(enabled: boolean) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users", accessToken ?? undefined),
    enabled: !!accessToken && enabled,
  });
}

export function useUpdateUser() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ id, ...input }: { id: string; role?: UserRole; is_active?: boolean }) =>
      api.patch<User>(`/users/${id}`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export interface AuditEntry {
  id: string;
  created_at: string;
  actor_id: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  summary: string;
  details: Record<string, unknown> | null;
}

export function useAuditLog(enabled: boolean) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["audit-log"],
    queryFn: () => api.get<AuditEntry[]>("/audit-log?limit=50", accessToken ?? undefined),
    enabled: !!accessToken && enabled,
  });
}
