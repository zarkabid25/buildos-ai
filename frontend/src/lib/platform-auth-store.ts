// Mirrors auth-store.ts, but kept entirely separate so a platform-admin session
// and a tenant session can coexist in the same browser without overwriting each other.

interface PlatformSession {
  accessToken: string | null;
  refreshToken: string | null;
}

let session: PlatformSession = { accessToken: null, refreshToken: null };

let onRefreshed: ((session: PlatformSession) => void) | null = null;
let onRefreshFailed: (() => void) | null = null;

export function setPlatformAuthStoreSession(next: PlatformSession) {
  session = next;
}

export function getPlatformAuthStoreSession(): PlatformSession {
  return session;
}

export function registerPlatformAuthCallbacks(callbacks: {
  onRefreshed: (session: PlatformSession) => void;
  onRefreshFailed: () => void;
}) {
  onRefreshed = callbacks.onRefreshed;
  onRefreshFailed = callbacks.onRefreshFailed;
}

export function notifyPlatformRefreshed(next: PlatformSession) {
  session = next;
  onRefreshed?.(next);
}

export function notifyPlatformRefreshFailed() {
  onRefreshFailed?.();
}
