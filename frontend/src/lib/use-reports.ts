import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Period, ReportKind } from "@/lib/report-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function query(period: Period, extra: Record<string, string> = {}) {
  const params = new URLSearchParams(extra);
  if (period.date_from) params.set("date_from", period.date_from);
  if (period.date_to) params.set("date_to", period.date_to);
  const s = params.toString();
  return s ? `?${s}` : "";
}

export function useReport<T>(kind: ReportKind, period: Period) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["reports", kind, period],
    queryFn: () => api.get<T>(`/reports/${kind}${query(period)}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

// Needs the Authorization header, which a plain link can't send, so fetch as a blob.
export async function downloadReportCsv(kind: ReportKind, period: Period, accessToken: string) {
  const res = await fetch(`${API_URL}/reports/${kind}${query(period, { format: "csv" })}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new ApiError(res.status, "Could not download the report");
  const url = URL.createObjectURL(await res.blob());
  const a = window.document.createElement("a");
  a.href = url;
  a.download = `${kind}-report.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
