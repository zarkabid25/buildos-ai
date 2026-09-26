import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type DocumentCategory =
  | "contract"
  | "drawing"
  | "boq"
  | "invoice"
  | "report"
  | "quotation"
  | "other";

export const DOCUMENT_CATEGORIES: DocumentCategory[] = [
  "contract",
  "drawing",
  "boq",
  "invoice",
  "report",
  "quotation",
  "other",
];

export interface DocumentItem {
  id: string;
  project_id: string | null;
  title: string;
  category: DocumentCategory;
  description: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export function useDocuments(category: DocumentCategory | "") {
  const { accessToken } = useAuth();
  const query = category ? `?category=${category}` : "";
  return useQuery({
    queryKey: ["documents", category],
    queryFn: () => api.get<DocumentItem[]>(`/documents${query}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useUploadDocument() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    // Multipart, so this bypasses api.ts (which always sends JSON).
    mutationFn: async (input: {
      file: File;
      title: string;
      category: DocumentCategory;
      project_id?: string;
      description?: string;
    }) => {
      const body = new FormData();
      body.append("file", input.file);
      body.append("title", input.title);
      body.append("category", input.category);
      if (input.project_id) body.append("project_id", input.project_id);
      if (input.description) body.append("description", input.description);
      const res = await fetch(`${API_URL}/documents`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = Array.isArray(err.detail) ? "Please check the form fields" : err.detail;
        throw new ApiError(res.status, detail ?? "Upload failed");
      }
      return res.json() as Promise<DocumentItem>;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
}

export function useDeleteDocument() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/documents/${id}`, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
}

// The download endpoint needs the Authorization header, which a plain link or
// <a download> can't send, so fetch as a blob and hand the browser an object URL.
export async function fetchDocumentBlob(
  id: string,
  accessToken: string,
  inline: boolean
): Promise<Blob> {
  const res = await fetch(`${API_URL}/documents/${id}/download${inline ? "?inline=true" : ""}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new ApiError(res.status, "Could not load document");
  return res.blob();
}
