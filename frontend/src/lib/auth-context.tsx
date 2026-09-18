"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { registerAuthCallbacks, setAuthStoreSession } from "@/lib/auth-store";
import type { AuthResponse, User } from "@/lib/auth-types";

const STORAGE_KEY = "buildos_auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
}

interface AuthContextValue extends AuthState {
  isLoading: boolean;
  setSession: (auth: AuthResponse) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function persist(state: AuthState) {
  setAuthStoreSession({ accessToken: state.accessToken, refreshToken: state.refreshToken });
  try {
    if (state.user) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // ignore corrupt/blocked storage
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, accessToken: null, refreshToken: null });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as AuthState;
        setState(parsed);
        setAuthStoreSession({ accessToken: parsed.accessToken, refreshToken: parsed.refreshToken });
      }
    } catch {
      // ignore corrupt/blocked storage
    } finally {
      setIsLoading(false);
    }

    // Lets the plain (non-React) api.ts fetch layer silently refresh an expired
    // access token and update this context, or log out if the refresh token is
    // also invalid -- without every hook having to pass tokens through manually.
    registerAuthCallbacks({
      onRefreshed: ({ accessToken, refreshToken }) => {
        setState((prev) => {
          const next = { ...prev, accessToken, refreshToken };
          persist(next);
          return next;
        });
      },
      onRefreshFailed: () => {
        const cleared = { user: null, accessToken: null, refreshToken: null };
        setState(cleared);
        persist(cleared);
      },
    });
  }, []);

  function setSession(auth: AuthResponse) {
    const next: AuthState = {
      user: auth.user,
      accessToken: auth.access_token,
      refreshToken: auth.refresh_token,
    };
    setState(next);
    persist(next);
  }

  function logout() {
    const next: AuthState = { user: null, accessToken: null, refreshToken: null };
    setState(next);
    persist(next);
  }

  return (
    <AuthContext.Provider value={{ ...state, isLoading, setSession, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
