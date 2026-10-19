// Mirrors auth-store.ts for the third, fully independent auth system: a
// plain module (not a React hook) so the non-React supplier-api.ts fetch
// layer can read/write the latest tokens without every hook threading them
// through manually.

interface Session {
  accessToken: string | null;
  refreshToken: string | null;
}

let session: Session = { accessToken: null, refreshToken: null };

let onRefreshed: ((session: Session) => void) | null = null;
let onRefreshFailed: (() => void) | null = null;

export function setSupplierAuthStoreSession(next: Session) {
  session = next;
}

export function getSupplierAuthStoreSession(): Session {
  return session;
}

export function registerSupplierAuthCallbacks(callbacks: { onRefreshed: (session: Session) => void; onRefreshFailed: () => void }) {
  onRefreshed = callbacks.onRefreshed;
  onRefreshFailed = callbacks.onRefreshFailed;
}

export function notifySupplierRefreshed(next: Session) {
  session = next;
  onRefreshed?.(next);
}

export function notifySupplierRefreshFailed() {
  onRefreshFailed?.();
}
