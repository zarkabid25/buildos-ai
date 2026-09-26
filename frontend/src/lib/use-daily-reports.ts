import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export interface DailyReportPhoto {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
}

export interface DailyReport {
  id: string;
  project_id: string;
  report_date: string;
  weather: string | null;
  workers_count: number;
  work_completed: string | null;
  materials_consumed: string | null;
  equipment_used: string | null;
  problems: string | null;
  notes: string | null;
  photos: DailyReportPhoto[];
}

export interface DailyReportInput {
  report_date: string;
  weather?: string;
  workers_count?: number;
  work_completed?: string;
  materials_consumed?: string;
  equipment_used?: string;
  problems?: string;
  notes?: string;
}

export function useDailyReports(projectId: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["projects", projectId, "daily-reports"],
    queryFn: () =>
      api.get<DailyReport[]>(`/projects/${projectId}/daily-reports`, accessToken ?? undefined),
    enabled: !!accessToken && !!projectId,
  });
}

export function useCreateDailyReport(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: DailyReportInput) =>
      api.post<DailyReport>(`/projects/${projectId}/daily-reports`, input, accessToken ?? undefined),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "daily-reports"] }),
  });
}

export function useUploadReportPhoto(projectId: string) {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    // api.ts always sends JSON, so multipart goes through fetch directly (the
    // browser must set the multipart boundary header itself).
    mutationFn: async ({ reportId, file }: { reportId: string; file: File }) => {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API_URL}/daily-reports/${reportId}/photos`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(res.status, err.detail ?? "Upload failed");
      }
      return res.json();
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "daily-reports"] }),
  });
}

// <img src> can't send an Authorization header, so photos are fetched as blobs.
export async function fetchPhotoBlobUrl(
  reportId: string,
  photoId: string,
  accessToken: string
): Promise<string> {
  const res = await fetch(`${API_URL}/daily-reports/${reportId}/photos/${photoId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new ApiError(res.status, "Could not load photo");
  return URL.createObjectURL(await res.blob());
}
