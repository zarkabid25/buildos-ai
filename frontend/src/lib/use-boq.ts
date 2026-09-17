import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { BoqAiGenerateResponse, BoqItem, BoqSummary } from "@/lib/boq-types";

export interface BoqItemInput {
  item_code: string;
  description: string;
  category?: string;
  unit: string;
  quantity: string;
  rate: string;
}

export function useBoqItems(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "boq"],
    queryFn: () => api.get<BoqItem[]>(`/projects/${projectId}/boq`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useBoqSummary(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "boq", "summary"],
    queryFn: () => api.get<BoqSummary>(`/projects/${projectId}/boq/summary`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useCreateBoqItem(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: BoqItemInput) =>
      api.post<BoqItem>(`/projects/${projectId}/boq`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "boq"] });
    },
  });
}

export function useDeleteBoqItem(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) =>
      api.delete<void>(`/projects/${projectId}/boq/${itemId}`, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "boq"] });
    },
  });
}

export function useGenerateAiBoq(projectId: string) {
  const { accessToken } = useAuth();
  return useMutation({
    mutationFn: (input: { project_type: string; notes?: string }) =>
      api.post<BoqAiGenerateResponse>(
        `/projects/${projectId}/boq/ai-generate`,
        input,
        accessToken ?? undefined
      ),
  });
}

export function useAcceptAiBoq(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: BoqItemInput[]) =>
      api.post<BoqItem[]>(`/projects/${projectId}/boq/ai-accept`, items, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "boq"] });
    },
  });
}
