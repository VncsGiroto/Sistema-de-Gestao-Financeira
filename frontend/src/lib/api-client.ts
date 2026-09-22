const base = (import.meta.env.VITE_API_URL as string) || "/api";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface User {
  id: number;
  name: string;
  email: string;
}

interface ApiErrorBody {
  detail?: { title?: string; detail?: string } | string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    if (typeof body.detail === "string") return body.detail;
    if (body.detail?.detail) return body.detail.detail;
    if (body.detail?.title) return body.detail.title;
  } catch {
    /* corpo não-JSON */
  }
  return `Erro ${res.status}`;
}

async function request<T>(path: string, init?: RequestInit, access?: string | null): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string; app: string }>("/health"),
  register: (body: { name: string; email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<TokenPair>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  refresh: (refresh_token: string) =>
    request<TokenPair>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),
  logout: (refresh_token: string, access: string) =>
    request<void>("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }, access),
  me: (access: string) => request<User>("/auth/me", {}, access),
  recover: (email: string) =>
    request<{ message: string }>("/auth/recover", { method: "POST", body: JSON.stringify({ email }) }),
  reset: (token: string, new_password: string) =>
    request<void>("/auth/reset", { method: "POST", body: JSON.stringify({ token, new_password }) }),
  change: (current_password: string, new_password: string, access: string) =>
    request<void>(
      "/auth/change",
      { method: "PATCH", body: JSON.stringify({ current_password, new_password }) },
      access,
    ),

  /** fetch autenticado com retry de refresh uma única vez (chamado pelo store) */
  authFetch: async <T>(
    path: string,
    access: string,
    doRefresh: () => Promise<string>,
    init?: RequestInit,
  ): Promise<{ data: T; access: string }> => {
    try {
      const data = await request<T>(path, init, access);
      return { data, access };
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        const fresh = await doRefresh();
        const data = await request<T>(path, init, fresh);
        return { data, access: fresh };
      }
      throw e;
    }
  },
};

export async function getHealth(): Promise<{ status: string; app: string }> {
  return api.health();
}
