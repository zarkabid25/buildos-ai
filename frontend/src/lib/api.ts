import { getAuthStoreSession, notifyRefreshFailed, notifyRefreshed } from "@/lib/auth-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

let refreshInFlight: Promise<TokenPair | null> | null = null;

async function refreshAccessToken(): Promise<TokenPair | null> {
  const { refreshToken } = getAuthStoreSession();
  if (!refreshToken) return null;

  // Coalesce concurrent refresh attempts (several queries can 401 at once)
  // into a single in-flight request instead of racing multiple refreshes.
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .catch(() => null)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

// FastAPI sends a string for most errors but a list of field errors for 422s;
// turn the list into a sentence so no caller ever shows "[object Object]".
function describeDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const field = d.loc?.filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg ?? "invalid"}` : (d.msg ?? "invalid");
      })
      .join("; ");
  }
  return "Request failed";
}

async function request<T>(
  path: string,
  options: RequestInit & { accessToken?: string; _isRetry?: boolean } = {}
): Promise<T> {
  const { accessToken, headers, _isRetry, ...rest } = options;

  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
  });

  if (res.status === 401 && accessToken && !_isRetry && path !== "/auth/refresh") {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      notifyRefreshed({ accessToken: refreshed.access_token, refreshToken: refreshed.refresh_token });
      return request<T>(path, { ...options, accessToken: refreshed.access_token, _isRetry: true });
    }
    notifyRefreshFailed();
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, describeDetail(body.detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, accessToken?: string) => request<T>(path, { method: "GET", accessToken }),
  post: <T>(path: string, body: unknown, accessToken?: string) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), accessToken }),
  patch: <T>(path: string, body: unknown, accessToken?: string) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body), accessToken }),
  delete: <T>(path: string, accessToken?: string) =>
    request<T>(path, { method: "DELETE", accessToken }),
};
