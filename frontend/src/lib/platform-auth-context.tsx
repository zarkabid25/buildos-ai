"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { registerPlatformAuthCallbacks, setPlatformAuthStoreSession } from "@/lib/platform-auth-store";
import type { PlatformAdmin, PlatformAuthResponse } from "@/lib/platform-types";

const STORAGE_KEY = "buildos_platform_auth";

interface PlatformAuthState {
  admin: PlatformAdmin | null;
  accessToken: string | null;
  refreshToken: string | null;
}

interface PlatformAuthContextValue extends PlatformAuthState {
  isLoading: boolean;
  setSession: (auth: PlatformAuthResponse) => void;
  logout: () => void;
}

const PlatformAuthContext = createContext<PlatformAuthContextValue | undefined>(undefined);

function persist(state: PlatformAuthState) {
  setPlatformAuthStoreSession({ accessToken: state.accessToken, refreshToken: state.refreshToken });
  try {
    if (state.admin) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // ignore corrupt/blocked storage
  }
}

export function PlatformAuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PlatformAuthState>({ admin: null, accessToken: null, refreshToken: null });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as PlatformAuthState;
        setState(parsed);
        setPlatformAuthStoreSession({ accessToken: parsed.accessToken, refreshToken: parsed.refreshToken });
      }
    } catch {
      // ignore corrupt/blocked storage
    } finally {
      setIsLoading(false);
    }

    registerPlatformAuthCallbacks({
      onRefreshed: ({ accessToken, refreshToken }) => {
        setState((prev) => {
          const next = { ...prev, accessToken, refreshToken };
          persist(next);
          return next;
        });
      },
      onRefreshFailed: () => {
        const cleared = { admin: null, accessToken: null, refreshToken: null };
        setState(cleared);
        persist(cleared);
      },
    });
  }, []);

  function setSession(auth: PlatformAuthResponse) {
    const next: PlatformAuthState = {
      admin: auth.admin,
      accessToken: auth.access_token,
      refreshToken: auth.refresh_token,
    };
    setState(next);
    persist(next);
  }

  function logout() {
    const next: PlatformAuthState = { admin: null, accessToken: null, refreshToken: null };
    setState(next);
    persist(next);
  }

  return (
    <PlatformAuthContext.Provider value={{ ...state, isLoading, setSession, logout }}>
      {children}
    </PlatformAuthContext.Provider>
  );
}

export function usePlatformAuth() {
  const ctx = useContext(PlatformAuthContext);
  if (!ctx) throw new Error("usePlatformAuth must be used within PlatformAuthProvider");
  return ctx;
}
