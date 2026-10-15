// Mirrors api.ts, but refreshes against /platform/auth/refresh and reads/writes the
// separate platform session store, so a platform access token is never sent to a
// tenant endpoint or vice versa.
import {
  getPlatformAuthStoreSession,
  notifyPlatformRefreshFailed,
  notifyPlatformRefreshed,
} from "@/lib/platform-auth-store";

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
  const { refreshToken } = getPlatformAuthStoreSession();
  if (!refreshToken) return null;

  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_URL}/platform/auth/refresh`, {
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

  if (res.status === 401 && accessToken && !_isRetry && path !== "/platform/auth/refresh") {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      notifyPlatformRefreshed({ accessToken: refreshed.access_token, refreshToken: refreshed.refresh_token });
      return request<T>(path, { ...options, accessToken: refreshed.access_token, _isRetry: true });
    }
    notifyPlatformRefreshFailed();
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, describeDetail(body.detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const platformApi = {
  get: <T>(path: string, accessToken?: string) => request<T>(path, { method: "GET", accessToken }),
  post: <T>(path: string, body: unknown, accessToken?: string) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), accessToken }),
  patch: <T>(path: string, body: unknown, accessToken?: string) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body), accessToken }),
  delete: <T>(path: string, accessToken?: string) => request<T>(path, { method: "DELETE", accessToken }),
};
