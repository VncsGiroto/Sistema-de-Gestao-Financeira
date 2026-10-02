import { ApiError, downloadBlob, fetchBlob, qs, request, type RefreshFn } from "./http";

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

export interface TxFilters {
  from?: string;
  to?: string;
  account_id?: number;
  category_id?: number;
  type?: string;
  source?: string;
  min?: string;
  max?: string;
  q?: string;
  page?: number;
  per_page?: number;
}

export interface CreateTxBody {
  account_id: number;
  category_id: number | null;
  date: string;
  description: string;
  amount: string;
  type: string;
}

export type PatchTxBody = Partial<CreateTxBody>;

export const txsApi = {
  list: (f: TxFilters, access: string) =>
    request<TxPage>(`/transactions${qs({ ...f })}`, {}, access),
  create: (body: CreateTxBody, access: string) =>
    request<Tx>(`/transactions`, { method: "POST", body: JSON.stringify(body) }, access),
  patch: (id: number, body: PatchTxBody, access: string) =>
    request<Tx>(`/transactions/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/transactions/${id}`, { method: "DELETE" }, access),
};

export async function downloadTransactionsCsv(
  f: TxFilters,
  access: string,
  doRefresh: RefreshFn,
): Promise<void> {
  const path = `/transactions/export/csv${qs({ ...f })}`;
  const run = (tok: string) => fetchBlob(path, tok);
  let blob: Blob;
  try {
    blob = await run(access);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) blob = await run(await doRefresh());
    else throw e;
  }
  downloadBlob(blob!, "transactions.csv");
}
