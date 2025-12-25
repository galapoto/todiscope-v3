"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Role as UiRole } from "@/lib/permissions";

type Role = "admin" | "user";

type AuthState = {
  token: "session" | null;
  role: Role;
  email: string | null;
  expiresAt: number | null;
};

function toUiRole(role: Role): UiRole {
  if (role === "admin") return "admin";
  return "analyst";
}

type AuthContextValue = AuthState & {
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function fetchSession(): Promise<{
  authenticated: boolean;
  email?: string;
  role?: Role;
  exp?: number;
}> {
  const response = await fetch("/api/auth/session", { cache: "no-store" });
  if (!response.ok) {
    return { authenticated: false };
  }
  return (await response.json()) as {
    authenticated: boolean;
    email?: string;
    role?: Role;
    exp?: number;
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [auth, setAuth] = useState<AuthState>({
    token: null,
    role: "user",
    email: null,
    expiresAt: null,
  });

  const refreshSession = useCallback(async () => {
    const session = await fetchSession();
    if (!session.authenticated) {
      setAuth({ token: null, role: "user", email: null, expiresAt: null });
      return;
    }
    setAuth({
      token: "session",
      role: session.role ?? "user",
      email: session.email ?? null,
      expiresAt: session.exp ? session.exp * 1000 : null,
    });
  }, []);

  useEffect(() => {
    setIsLoading(true);
    refreshSession().finally(() => setIsLoading(false));
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...auth,
      isLoading,
      refreshSession,
      login: async (email, password) => {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!response.ok) {
          const text = await response.text().catch(() => "");
          throw new Error(text || "Login failed");
        }
        await refreshSession();
      },
      logout: async () => {
        await fetch("/api/auth/logout", { method: "POST" }).catch(() => null);
        await refreshSession();
      },
    }),
    [auth, isLoading, refreshSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

export function useUiRole(): UiRole {
  const { role } = useAuth();
  return toUiRole(role);
}
