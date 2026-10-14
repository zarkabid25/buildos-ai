import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type { PlatformCompany, PlatformCompanyList, PlatformDashboardStats } from "@/lib/platform-types";

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
