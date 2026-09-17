"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, accessToken: null, refreshToken: null });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setState(JSON.parse(raw));
    } catch {
      // ignore corrupt/blocked storage
    } finally {
      setIsLoading(false);
    }
  }, []);

  function setSession(auth: AuthResponse) {
    const next: AuthState = {
      user: auth.user,
      accessToken: auth.access_token,
      refreshToken: auth.refresh_token,
    };
    setState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore
    }
  }

  function logout() {
    setState({ user: null, accessToken: null, refreshToken: null });
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
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
