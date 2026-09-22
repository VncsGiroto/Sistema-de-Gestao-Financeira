import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api-client";
import type { User } from "./api-client";

const REFRESH_KEY = "financeway.refresh";

interface AuthState {
  access: string | null;
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<string>;
}

const AuthCtx = createContext<AuthState | null>(null);

function loadRefresh(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [access, setAccess] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const refreshing = useRef<Promise<string> | null>(null);

  const refresh = useCallback(async (): Promise<string> => {
    if (refreshing.current) return refreshing.current;
    const stored = loadRefresh();
    if (!stored) {
      setReady(true);
      throw new Error("Sem sessão");
    }
    refreshing.current = api
      .refresh(stored)
      .then((pair) => {
        setAccess(pair.access_token);
        try {
          localStorage.setItem(REFRESH_KEY, pair.refresh_token);
        } catch {
          /* storage indisponível */
        }
        setReady(true);
        return pair.access_token;
      })
      .catch((e) => {
        try {
          localStorage.removeItem(REFRESH_KEY);
        } catch {
          /* noop */
        }
        setAccess(null);
        setUser(null);
        setReady(true);
        throw e;
      })
      .finally(() => {
        refreshing.current = null;
      });
    return refreshing.current;
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const pair = await api.login({ email, password });
    setAccess(pair.access_token);
    try {
      localStorage.setItem(REFRESH_KEY, pair.refresh_token);
    } catch {
      /* noop */
    }
    const me = await api.me(pair.access_token);
    setUser(me);
    setReady(true);
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    await api.register({ name, email, password });
    await login(email, password);
  }, [login]);

  const logout = useCallback(async () => {
    const stored = loadRefresh();
    if (stored && access) {
      try {
        await api.logout(stored, access);
      } catch {
        /* logout best-effort */
      }
    }
    try {
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* noop */
    }
    setAccess(null);
    setUser(null);
    setReady(true);
  }, [access]);

  const value = useMemo(
    () => ({ access, user, ready, login, register, logout, refresh }),
    [access, user, ready, login, register, logout, refresh],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
