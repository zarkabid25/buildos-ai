import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  CompanyTask,
  Milestone,
  ProjectHealth,
  ProjectMember,
  ProjectSchedule,
  Task,
  TaskStatus,
} from "@/lib/task-types";

export function useTasks(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "tasks"],
    queryFn: () => api.get<Task[]>(`/projects/${projectId}/tasks`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useCreateTask(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { title: string; priority?: string; start_date?: string; due_date?: string }) =>
      api.post<Task>(`/projects/${projectId}/tasks`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "schedule"] });
    },
  });
}

export function useAddDependency(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    meta: { inlineError: true },
    mutationFn: ({ taskId, dependsOnTaskId }: { taskId: string; dependsOnTaskId: string }) =>
      api.post<Task>(
        `/projects/${projectId}/tasks/${taskId}/dependencies`,
        { depends_on_task_id: dependsOnTaskId },
        accessToken ?? undefined
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "schedule"] });
    },
  });
}

export function useRemoveDependency(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, dependsOnTaskId }: { taskId: string; dependsOnTaskId: string }) =>
      api.delete<void>(
        `/projects/${projectId}/tasks/${taskId}/dependencies/${dependsOnTaskId}`,
        accessToken ?? undefined
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "schedule"] });
    },
  });
}

export function useProjectSchedule(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "schedule"],
    queryFn: () => api.get<ProjectSchedule>(`/projects/${projectId}/schedule`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useUpdateTaskStatus(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: TaskStatus }) =>
      api.patch<Task>(`/projects/${projectId}/tasks/${taskId}`, { status }, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "schedule"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useCompanyTasks(filters: { mine?: boolean; status?: TaskStatus; projectId?: string }) {
  const { accessToken } = useAuth();
  const params = new URLSearchParams();
  if (filters.mine) params.set("mine", "true");
  if (filters.status) params.set("status", filters.status);
  if (filters.projectId) params.set("project_id", filters.projectId);
  const query = params.toString();
  return useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => api.get<CompanyTask[]>(`/tasks${query ? `?${query}` : ""}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

/** Status change from the company-wide list, where each row belongs to a different project. */
export function useSetTaskStatus() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, taskId, status }: { projectId: string; taskId: string; status: TaskStatus }) =>
      api.patch<Task>(`/projects/${projectId}/tasks/${taskId}`, { status }, accessToken ?? undefined),
    onSuccess: (_task, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });
}

export function useMilestones(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "milestones"],
    queryFn: () => api.get<Milestone[]>(`/projects/${projectId}/milestones`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useCreateMilestone(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; due_date?: string }) =>
      api.post<Milestone>(`/projects/${projectId}/milestones`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "milestones"] });
    },
  });
}

export function useToggleMilestone(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ milestoneId, is_completed }: { milestoneId: string; is_completed: boolean }) =>
      api.patch<Milestone>(
        `/projects/${projectId}/milestones/${milestoneId}`,
        { is_completed },
        accessToken ?? undefined
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "milestones"] });
    },
  });
}

export function useProjectMembers(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "members"],
    queryFn: () => api.get<ProjectMember[]>(`/projects/${projectId}/members`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useProjectHealth(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "health"],
    queryFn: () => api.get<ProjectHealth>(`/projects/${projectId}/health`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}
