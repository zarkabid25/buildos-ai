"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { registerSupplierAuthCallbacks, setSupplierAuthStoreSession } from "@/lib/supplier-auth-store";
import type { SupplierAuthResponse, SupplierMembershipSummary, SupplierUser } from "@/lib/supplier-portal-types";

const STORAGE_KEY = "buildos_supplier_auth";

interface AuthState {
  user: SupplierUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  activeSupplierId: string | null;
  memberships: SupplierMembershipSummary[];
}

const EMPTY: AuthState = { user: null, accessToken: null, refreshToken: null, activeSupplierId: null, memberships: [] };

interface SupplierAuthContextValue extends AuthState {
  isLoading: boolean;
  setSession: (auth: SupplierAuthResponse) => void;
  setActiveSupplier: (args: { access_token: string; refresh_token: string; active_supplier_id: string }) => void;
  logout: () => void;
  activeMembership: SupplierMembershipSummary | null;
}

const SupplierAuthContext = createContext<SupplierAuthContextValue | undefined>(undefined);

function persist(state: AuthState) {
  setSupplierAuthStoreSession({ accessToken: state.accessToken, refreshToken: state.refreshToken });
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

export function SupplierAuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(EMPTY);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as AuthState;
        setState(parsed);
        setSupplierAuthStoreSession({ accessToken: parsed.accessToken, refreshToken: parsed.refreshToken });
      }
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }

    registerSupplierAuthCallbacks({
      onRefreshed: ({ accessToken, refreshToken }) => {
        setState((prev) => {
          const next = { ...prev, accessToken, refreshToken };
          persist(next);
          return next;
        });
      },
      onRefreshFailed: () => {
        setState(EMPTY);
        persist(EMPTY);
      },
    });
  }, []);

  function setSession(auth: SupplierAuthResponse) {
    const next: AuthState = {
      user: auth.user,
      accessToken: auth.access_token,
      refreshToken: auth.refresh_token,
      activeSupplierId: auth.active_supplier_id,
      memberships: auth.memberships,
    };
    setState(next);
    persist(next);
  }

  function setActiveSupplier(args: { access_token: string; refresh_token: string; active_supplier_id: string }) {
    setState((prev) => {
      const next = { ...prev, accessToken: args.access_token, refreshToken: args.refresh_token, activeSupplierId: args.active_supplier_id };
      persist(next);
      return next;
    });
  }

  function logout() {
    setState(EMPTY);
    persist(EMPTY);
  }

  const activeMembership = state.memberships.find((m) => m.marketplace_supplier_id === state.activeSupplierId) ?? null;

  return (
    <SupplierAuthContext.Provider value={{ ...state, isLoading, setSession, setActiveSupplier, logout, activeMembership }}>
      {children}
    </SupplierAuthContext.Provider>
  );
}

export function useSupplierAuth() {
  const ctx = useContext(SupplierAuthContext);
  if (!ctx) throw new Error("useSupplierAuth must be used within SupplierAuthProvider");
  return ctx;
}
