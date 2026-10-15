import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type {
  PlatformAdmin,
  PlatformAuditEntry,
  PlatformCompany,
  PlatformCompanyList,
  PlatformDashboardStats,
  PlatformInvitation,
  PlatformInvitationCreated,
  PlatformStaffRole,
} from "@/lib/platform-types";

export function usePlatformDashboard() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-dashboard"],
    queryFn: () => platformApi.get<PlatformDashboardStats>("/platform/dashboard", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function usePlatformCompanies(search: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-companies", search],
    queryFn: () =>
      platformApi.get<PlatformCompanyList>(
        `/platform/companies${search ? `?search=${encodeURIComponent(search)}` : ""}`,
        accessToken ?? undefined
      ),
    enabled: !!accessToken,
  });
}

export function usePlatformCompany(id: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-company", id],
    queryFn: () => platformApi.get<PlatformCompany>(`/platform/companies/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useSetCompanySuspended() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, suspend }: { id: string; suspend: boolean }) =>
      platformApi.post<PlatformCompany>(
        `/platform/companies/${id}/${suspend ? "suspend" : "reactivate"}`,
        {},
        accessToken ?? undefined
      ),
    onSuccess: (company) => {
      queryClient.invalidateQueries({ queryKey: ["platform-companies"] });
      queryClient.setQueryData(["platform-company", company.id], company);
    },
  });
}

export function useApproveCompany() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => platformApi.post<PlatformCompany>(`/platform/companies/${id}/approve`, {}, accessToken ?? undefined),
    onSuccess: (company) => {
      queryClient.invalidateQueries({ queryKey: ["platform-companies"] });
      queryClient.setQueryData(["platform-company", company.id], company);
    },
  });
}

export function usePlatformAuditLog(enabled: boolean) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-audit-log"],
    queryFn: () => platformApi.get<PlatformAuditEntry[]>("/platform/audit-log", accessToken ?? undefined),
    enabled: !!accessToken && enabled,
  });
}

export function usePlatformStaff(enabled: boolean) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-staff"],
    queryFn: () => platformApi.get<PlatformAdmin[]>("/platform/staff", accessToken ?? undefined),
    enabled: !!accessToken && enabled,
  });
}

export function useUpdateStaff() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ id, ...input }: { id: string; role?: PlatformStaffRole; is_active?: boolean }) =>
      platformApi.patch<PlatformAdmin>(`/platform/staff/${id}`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-staff"] });
      queryClient.invalidateQueries({ queryKey: ["platform-audit-log"] });
    },
  });
}

export function usePlatformInvitations(enabled: boolean) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["platform-invitations"],
    queryFn: () => platformApi.get<PlatformInvitation[]>("/platform/staff/invitations", accessToken ?? undefined),
    enabled: !!accessToken && enabled,
  });
}

export function useCreatePlatformInvitation() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { email: string; role: PlatformStaffRole; full_name?: string }) =>
      platformApi.post<PlatformInvitationCreated>("/platform/staff/invitations", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-invitations"] });
      queryClient.invalidateQueries({ queryKey: ["platform-audit-log"] });
    },
  });
}

export function useRevokePlatformInvitation() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => platformApi.delete<void>(`/platform/staff/invitations/${id}`, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-invitations"] }),
  });
}
