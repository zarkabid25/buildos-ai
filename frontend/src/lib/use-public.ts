import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function publicGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : "Request failed");
  }
  return res.json() as Promise<T>;
}

async function publicPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((d: { loc?: string[]; msg?: string }) => d.msg).join("; ")
      : err.detail;
    throw new ApiError(res.status, detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export interface PublicPlan {
  id: string;
  name: string;
  description: string | null;
  trial_days: number;
  max_projects: number | null;
  max_team_members: number | null;
  marketplace_included: boolean;
  is_active: boolean;
  prices: { currency: string; billing_period: "monthly" | "annual"; amount: string; is_current: boolean }[];
}

export function usePublicPlans() {
  return useQuery({
    queryKey: ["public-plans"],
    queryFn: () => publicGet<PublicPlan[]>("/public/plans"),
  });
}

export function useRequestDemo() {
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: { full_name: string; email: string; phone?: string; company_name: string; message?: string }) =>
      publicPost<{ id: string; already_submitted: boolean }>("/public/demo-requests", input),
  });
}

export function useSubmitSupplierApplication() {
  return useMutation({
    meta: { inlineError: true },
    mutationFn: (input: {
      business_name: string; contact_name: string; email: string; phone?: string;
      business_registration_info?: string; categories: string[]; delivery_locations: string[]; business_description?: string;
    }) => publicPost<{ id: string; status: string }>("/public/supplier-applications", input),
  });
}

export async function uploadSupplierApplicationDocument(applicationId: string, file: File, title: string) {
  const body = new FormData();
  body.append("file", file);
  body.append("title", title);
  const res = await fetch(`${API_URL}/public/supplier-applications/${applicationId}/documents`, { method: "POST", body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, Array.isArray(err.detail) ? "Please check the file" : err.detail ?? "Upload failed");
  }
  return res.json();
}
