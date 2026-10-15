import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type {
  CrmActivity,
  CrmContact,
  CrmConvertResult,
  CrmOrganization,
  CrmOrganizationDetail,
  CrmPipelineType,
  CrmStage,
} from "@/lib/crm-types";

export function useCrmOrganizations(pipelineType: CrmPipelineType) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["crm-organizations", pipelineType],
    queryFn: () =>
      platformApi.get<CrmOrganization[]>(
        `/platform/crm/organizations?pipeline_type=${pipelineType}`,
        accessToken ?? undefined
      ),
    enabled: !!accessToken,
  });
}

export function useCrmOrganization(id: string) {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["crm-organization", id],
    queryFn: () => platformApi.get<CrmOrganizationDetail>(`/platform/crm/organizations/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useCreateCrmOrganization() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: {
      name: string;
      pipeline_type: CrmPipelineType;
      source?: string;
      industry?: string;
      website?: string;
      phone?: string;
      email?: string;
      notes?: string;
    }) => platformApi.post<CrmOrganization>("/platform/crm/organizations", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-organizations"] }),
  });
}

export function useUpdateCrmOrganization() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: { id: string; stage?: CrmStage; owner_staff_id?: string | null }) =>
      platformApi.patch<CrmOrganization>(`/platform/crm/organizations/${id}`, input, accessToken ?? undefined),
    onSuccess: (org) => {
      queryClient.invalidateQueries({ queryKey: ["crm-organizations"] });
      queryClient.invalidateQueries({ queryKey: ["crm-organization", org.id] });
    },
  });
}

export function useAddCrmContact() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ orgId, ...input }: { orgId: string; name: string; title?: string; email?: string; phone?: string; is_primary?: boolean }) =>
      platformApi.post<CrmContact>(`/platform/crm/organizations/${orgId}/contacts`, input, accessToken ?? undefined),
    onSuccess: (_contact, vars) => queryClient.invalidateQueries({ queryKey: ["crm-organization", vars.orgId] }),
  });
}

export function useAddCrmActivity() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ orgId, ...input }: { orgId: string; type: string; summary: string; due_at?: string }) =>
      platformApi.post<CrmActivity>(`/platform/crm/organizations/${orgId}/activities`, input, accessToken ?? undefined),
    onSuccess: (_activity, vars) => {
      queryClient.invalidateQueries({ queryKey: ["crm-organization", vars.orgId] });
      queryClient.invalidateQueries({ queryKey: ["crm-follow-ups"] });
    },
  });
}

export function useCrmFollowUps() {
  const { accessToken } = usePlatformAuth();
  return useQuery({
    queryKey: ["crm-follow-ups"],
    queryFn: () => platformApi.get<CrmActivity[]>("/platform/crm/follow-ups", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCompleteCrmActivity() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activityId: string) =>
      platformApi.post<CrmActivity>(`/platform/crm/activities/${activityId}/complete`, {}, accessToken ?? undefined),
    onSuccess: (activity) => {
      queryClient.invalidateQueries({ queryKey: ["crm-follow-ups"] });
      queryClient.invalidateQueries({ queryKey: ["crm-organization", activity.organization_id] });
    },
  });
}

export function useConvertCrmOrganization() {
  const { accessToken } = usePlatformAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({
      orgId,
      ...input
    }: {
      orgId: string;
      link_existing_company_id?: string;
      create_company_name?: string;
      create_company_code?: string;
    }) => platformApi.post<CrmConvertResult>(`/platform/crm/organizations/${orgId}/convert`, input, accessToken ?? undefined),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["crm-organizations"] });
      queryClient.invalidateQueries({ queryKey: ["crm-organization", result.organization.id] });
      queryClient.invalidateQueries({ queryKey: ["platform-companies"] });
    },
  });
}
