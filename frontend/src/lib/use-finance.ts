import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Expense, ProjectCostSummary } from "@/lib/finance-types";

export function useProjectExpenses(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["expenses", projectId],
    queryFn: () => api.get<Expense[]>(`/expenses?project_id=${projectId}`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useCreateExpense(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { amount: string; description?: string; expense_date: string }) =>
      api.post<Expense>("/expenses", { project_id: projectId, ...input }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "cost-summary"] });
    },
  });
}

export function useProjectCostSummary(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "cost-summary"],
    queryFn: () =>
      api.get<ProjectCostSummary>(`/projects/${projectId}/cost-summary`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}
