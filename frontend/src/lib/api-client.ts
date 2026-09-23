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

export interface Account {
  id: number;
  name: string;
  bank: string | null;
  account_type: string;
  initial_balance: string;
}

export interface Category {
  id: number;
  name: string;
  type: string;
}

export interface Tx {
  id: number;
  account_id: number;
  category_id: number | null;
  date: string;
  description: string;
  amount: string;
  type: string;
  source: string;
}

export interface TxPage {
  data: Tx[];
  meta: { page: number; per_page: number; total: number };
}

export interface CommitmentItem {
  kind: string;
  description: string;
  due_date: string;
  amount: string;
  ref_id: number;
}

export interface CommitmentsData {
  total: string;
  items: CommitmentItem[];
}

export interface DashboardData {
  balance: string;
  income: { total: string; by_category: { name: string; total: string }[] };
  expense: { total: string; by_category: { name: string; total: string }[] };
  evolution: { month: string; income: string; expense: string }[];
}

export interface ImportJob {
  id: number;
  account_id: number;
  source: string;
  file_name: string;
  status: string;
  total_rows: number;
  imported_rows: number;
  duplicate_rows: number;
  error: string | null;
  processed_at: string | null;
}

export interface ImportItem {
  id: number;
  row_no: number;
  verdict: string;
  payload: Record<string, unknown>;
  matched_transaction_id: number | null;
}

export interface Bill {
  id: number;
  description: string;
  amount: string;
  kind: string;
  periodicity: string | null;
  due_day: number | null;
  next_due: string | null;
}

export interface BillBody {
  description: string;
  amount: string;
  kind: string;
  periodicity?: string;
  due_day?: number;
  next_due?: string;
}

export interface Installment {
  id: number;
  description: string;
  total_amount: string;
  num_installments: number;
  installment_amount: string;
  first_due_date: string;
  account_id: number | null;
}

export interface ScheduleItem {
  n: number;
  due_date: string;
  amount: string;
}

export interface TxFilters {
  from?: string;
  to?: string;
  account_id?: number;
  category_id?: number;
  type?: string;
  q?: string;
  page?: number;
  per_page?: number;
}

function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") sp.set(k, String(v));
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
    credentials: "include", // refresh via cookie HttpOnly
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

  // --- finance (usar via authed() abaixo para retry de refresh) ---
  accounts: {
    list: (access: string) => request<Account[]>("/accounts", {}, access),
    create: (body: { name: string; bank?: string; account_type: string; initial_balance?: string }, access: string) =>
      request<Account>("/accounts", { method: "POST", body: JSON.stringify(body) }, access),
    patch: (id: number, body: Partial<{ name: string; bank: string; account_type: string }>, access: string) =>
      request<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
    remove: (id: number, access: string) =>
      request<void>(`/accounts/${id}`, { method: "DELETE" }, access),
  },
  categories: {
    list: (type: string | undefined, access: string) =>
      request<Category[]>(`/categories${qs({ type })}`, {}, access),
    create: (body: { name: string; type: string }, access: string) =>
      request<Category>("/categories", { method: "POST", body: JSON.stringify(body) }, access),
    patch: (id: number, body: { name: string }, access: string) =>
      request<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
    remove: (id: number, access: string) =>
      request<void>(`/categories/${id}`, { method: "DELETE" }, access),
  },
  txs: {
    list: (f: TxFilters, access: string) => request<TxPage>(`/transactions${qs(f as Record<string, string | number | undefined>)}`, {}, access),
    create: (
      body: { account_id: number; category_id: number | null; date: string; description: string; amount: string; type: string },
      access: string,
    ) => request<Tx>(`/transactions`, { method: "POST", body: JSON.stringify(body) }, access),
    patch: (id: number, body: Partial<{ account_id: number; category_id: number | null; date: string; description: string; amount: string; type: string }>, access: string) =>
      request<Tx>(`/transactions/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
    remove: (id: number, access: string) =>
      request<void>(`/transactions/${id}`, { method: "DELETE" }, access),
  },
  imports: {
    upload: async (account_id: number, file: File, access: string) => {
      const fd = new FormData();
      fd.set("account_id", String(account_id));
      fd.set("file", file);
      const res = await fetch(`${base}/imports/ofx`, {
        method: "POST",
        headers: { Authorization: `Bearer ${access}` },
        body: fd,
      });
      if (!res.ok) {
        let msg = `Erro ${res.status}`;
        try {
          const b = (await res.json()) as { detail?: { detail?: string } | string };
          msg = typeof b.detail === "string" ? b.detail : (b.detail?.detail ?? msg);
        } catch { /* mantém */ }
        throw new ApiError(res.status, msg);
      }
      return (await res.json()) as { import_id: number; status: string };
    },
    list: (access: string) => request<ImportJob[]>("/imports", {}, access),
    get: (id: number, access: string) => request<ImportJob>(`/imports/${id}`, {}, access),
    items: (id: number, verdict: string | undefined, access: string) =>
      request<ImportItem[]>(`/imports/${id}/items${verdict ? `?verdict=${verdict}` : ""}`, {}, access),
    review: (id: number, decisions: { item_id: number; decision: string }[], access: string) =>
      request<{ decided: number }>(`/imports/${id}/review`, { method: "POST", body: JSON.stringify({ decisions }) }, access),
    commit: (id: number, access: string) =>
      request<{ imported_rows: number; duplicate_rows: number; skipped: number }>(`/imports/${id}/commit`, { method: "POST" }, access),
    matched: (txId: number, access: string) => request<Tx>(`/transactions/${txId}`, {}, access),
  },
  dashboard: {
    get: (f: { from?: string; to?: string; account_id?: number }, access: string) =>
      request<DashboardData>(`/dashboard${qs(f as Record<string, string | number | undefined>)}`, {}, access),
  },
  bills: {
    list: (access: string) => request<Bill[]>("/bills", {}, access),
    upcoming: (days: number, access: string) => request<Bill[]>(`/bills/upcoming?days=${days}`, {}, access),
    create: (body: BillBody, access: string) =>
      request<Bill>("/bills", { method: "POST", body: JSON.stringify(body) }, access),
    patch: (id: number, body: Partial<BillBody>, access: string) =>
      request<Bill>(`/bills/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
    remove: (id: number, access: string) =>
      request<void>(`/bills/${id}`, { method: "DELETE" }, access),
  },
  installments: {
    list: (access: string) => request<Installment[]>("/installments", {}, access),
    create: (
      body: { description: string; total_amount: string; num_installments: number; first_due_date: string; account_id?: number },
      access: string,
    ) => request<Installment>("/installments", { method: "POST", body: JSON.stringify(body) }, access),
    schedule: (id: number, access: string) =>
      request<ScheduleItem[]>(`/installments/${id}/schedule`, {}, access),
    remove: (id: number, access: string) =>
      request<void>(`/installments/${id}`, { method: "DELETE" }, access),
  },

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

  /** envolve qualquer chamada autenticada com retry de refresh 1x (para mutations) */
  authed: async <T>(
    fn: (tok: string) => Promise<T>,
    access: string,
    doRefresh: () => Promise<string>,
  ): Promise<T> => {
    try {
      return await fn(access);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        return await fn(await doRefresh());
      }
      throw e;
    }
  },

  downloadCsv: async (f: TxFilters, access: string, doRefresh: () => Promise<string>): Promise<void> => {
    const run = async (tok: string) => {
      const res = await fetch(`${base}/transactions/export/csv${qs(f as Record<string, string | number | undefined>)}`, {
        headers: { Authorization: `Bearer ${tok}` },
      });
      if (!res.ok) throw new ApiError(res.status, `Erro ${res.status}`);
      return res.blob();
    };
    let blob: Blob;
    try {
      blob = await run(access);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) blob = await run(await doRefresh());
      else throw e;
    }
    const url = URL.createObjectURL(blob!);
    const a = document.createElement("a");
    a.href = url;
    a.download = "transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  },
};

export async function getHealth(): Promise<{ status: string; app: string }> {
  return api.health();
}
