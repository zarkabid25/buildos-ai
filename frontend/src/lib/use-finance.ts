import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Expense, ExpenseCategory, ProjectCostSummary } from "@/lib/finance-types";

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
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "cost-summary"] });
      queryClient.invalidateQueries({ queryKey: ["reports"] });
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

/** Every expense in the company, optionally for one project (the sidebar Expenses page). */
export function useAllExpenses(projectId?: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["expenses", "all", projectId ?? null],
    queryFn: () =>
      api.get<Expense[]>(`/expenses${projectId ? `?project_id=${projectId}` : ""}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useRecordExpense() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      project_id: string;
      category_id?: string;
      amount: string;
      description?: string;
      expense_date: string;
    }) => api.post<Expense>("/expenses", input, accessToken ?? undefined),
    onSuccess: (_expense, input) => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["projects", input.project_id, "cost-summary"] });
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function useExpenseCategories() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["expense-categories"],
    queryFn: () => api.get<ExpenseCategory[]>("/expense-categories", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateExpenseCategory() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.post<ExpenseCategory>("/expense-categories", { name }, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["expense-categories"] }),
  });
}
