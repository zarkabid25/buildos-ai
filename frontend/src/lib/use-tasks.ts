import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Milestone, ProjectHealth, ProjectMember, Task, TaskStatus } from "@/lib/task-types";

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
    mutationFn: (input: { title: string; priority?: string; due_date?: string }) =>
      api.post<Task>(`/projects/${projectId}/tasks`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "tasks"] });
    },
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
