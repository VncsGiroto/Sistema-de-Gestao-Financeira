import { request } from "./http";

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

export interface RegisterBody {
  name: string;
  email: string;
  password: string;
}

export interface LoginBody {
  email: string;
  password: string;
}

export const authApi = {
  register: (body: RegisterBody) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: LoginBody) =>
    request<TokenPair>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  refresh: (refresh_token?: string) =>
    request<TokenPair>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify(refresh_token ? { refresh_token } : {}),
    }),
  logout: (access: string | null, refresh_token?: string) =>
    request<void>(
      "/auth/logout",
      { method: "POST", body: JSON.stringify(refresh_token ? { refresh_token } : {}) },
      access,
    ),
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
};
