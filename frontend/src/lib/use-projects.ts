import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Project, ProjectSummary } from "@/lib/project-types";

export interface ProjectCreateInput {
  name: string;
  code: string;
  client_name?: string;
  location?: string;
  project_type?: string;
  start_date?: string;
  end_date?: string;
  budget?: string;
}

export function useProjects() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useProject(id: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", id],
    queryFn: () => api.get<Project>(`/projects/${id}`, accessToken ?? undefined),
    enabled: !!accessToken && !!id,
  });
}

export function useProjectSummary() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", "summary"],
    queryFn: () => api.get<ProjectSummary>("/projects/summary", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateProject() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ProjectCreateInput) =>
      api.post<Project>("/projects", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
