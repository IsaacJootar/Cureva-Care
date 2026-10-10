"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { apiGet, apiPost, tokenStore } from "./api";
import { applyTheme } from "./theme";
import type { CurrentUser } from "./types";

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  signInWithTicket: (token: string) => Promise<CurrentUser>;
  signOut: () => void;
  setUser: (u: CurrentUser) => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

interface SessionResponse {
  access: string;
  refresh: string;
  user: CurrentUser;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!tokenStore.access) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiGet<CurrentUser>("/users/me");
      setUser(me);
      applyTheme(me.theme_preference);
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  const signInWithTicket = useCallback(async (token: string) => {
    const data = await apiPost<SessionResponse>("/auth/session", { token }, { auth: false });
    tokenStore.set(data.access, data.refresh);
    setUser(data.user);
    applyTheme(data.user.theme_preference);
    setLoading(false);
    return data.user;
  }, []);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, signInWithTicket, signOut, setUser, refresh: loadMe }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
