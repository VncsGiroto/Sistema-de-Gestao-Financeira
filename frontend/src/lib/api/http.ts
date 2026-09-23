const base = (import.meta.env.VITE_API_URL as string) || "/api";

export type QueryValue = string | number | undefined;
export type QueryParams = Record<string, QueryValue>;
export type RefreshFn = () => Promise<string>;

export function qs(params: QueryParams): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
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

export async function parseError(res: Response): Promise<string> {
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

export function authHeaders(access?: string | null, extra?: HeadersInit): HeadersInit {
  return {
    ...(extra || {}),
    ...(access ? { Authorization: `Bearer ${access}` } : {}),
  };
}

export async function request<T>(path: string, init?: RequestInit, access?: string | null): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    credentials: "include", // refresh via cookie HttpOnly
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(access, init?.headers),
    },
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** POST/PUT multipart (ex: upload OFX) sem Content-Type JSON, com erro padronizado. */
export async function requestForm<T>(path: string, form: FormData, access?: string | null): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(access),
    body: form,
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return (await res.json()) as T;
}

/** GET binário (ex: export CSV) com erro padronizado. */
export async function fetchBlob(path: string, access: string): Promise<Blob> {
  const res = await fetch(`${base}${path}`, {
    credentials: "include",
    headers: authHeaders(access),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.blob();
}

/** fetch autenticado com retry de refresh uma única vez (chamado pelo store) */
export async function authFetch<T>(
  path: string,
  access: string,
  doRefresh: RefreshFn,
  init?: RequestInit,
): Promise<{ data: T; access: string }> {
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
}

/** envolve qualquer chamada autenticada com retry de refresh 1x (para mutations) */
export async function authed<T>(
  fn: (tok: string) => Promise<T>,
  access: string,
  doRefresh: RefreshFn,
): Promise<T> {
  try {
    return await fn(access);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      return await fn(await doRefresh());
    }
    throw e;
  }
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
