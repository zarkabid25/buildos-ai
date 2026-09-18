// A plain module (not a React hook) holding the current session tokens, so the
// non-React api.ts fetch layer can read the latest refresh token and write back
// a refreshed access token without every hook having to thread that through.
// AuthProvider is the single source of truth and keeps this in sync.

interface Session {
  accessToken: string | null;
  refreshToken: string | null;
}

let session: Session = { accessToken: null, refreshToken: null };

let onRefreshed: ((session: Session) => void) | null = null;
let onRefreshFailed: (() => void) | null = null;

export function setAuthStoreSession(next: Session) {
  session = next;
}

export function getAuthStoreSession(): Session {
  return session;
}

export function registerAuthCallbacks(callbacks: {
  onRefreshed: (session: Session) => void;
  onRefreshFailed: () => void;
}) {
  onRefreshed = callbacks.onRefreshed;
  onRefreshFailed = callbacks.onRefreshFailed;
}

export function notifyRefreshed(next: Session) {
  session = next;
  onRefreshed?.(next);
}

export function notifyRefreshFailed() {
  onRefreshFailed?.();
}
