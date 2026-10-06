import { ApiError, downloadBlob, fetchBlob, qs, request, type RefreshFn } from "./http";

export interface MovementItem {
  id: string;
  kind: string;
  date: string;
  description: string;
  amount: string;
  direction: "in" | "out" | "neutral";
  cash_impact: string;
  account_id: number | null;
  from_account_id: number | null;
  to_account_id: number | null;
  asset_id: number | null;
  ticker: string | null;
  op_id: number | null;
  transaction_id: number | null;
  movement_id: number | null;
  category_id: number | null;
  editable: boolean;
  origin: "transaction" | "operation" | "transfer";
  origin_hint: string;
}

export interface MovementPage {
  data: MovementItem[];
  meta: { page: number; per_page: number; total: number };
}

export interface MovementFilters {
  from?: string;
  to?: string;
  account_id?: number;
  kind?: string;
  page?: number;
  per_page?: number;
}

export const movementsApi = {
  list: (f: MovementFilters, access: string) =>
    request<MovementPage>(`/movements${qs({ ...f })}`, {}, access),
};

export async function downloadMovementsCsv(
  f: MovementFilters,
  access: string,
  doRefresh: RefreshFn,
): Promise<void> {
  const path = `/movements/export/csv${qs({ ...f })}`;
  const run = (tok: string) => fetchBlob(path, tok);
  let blob: Blob;
  try {
    blob = await run(access);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) blob = await run(await doRefresh());
    else throw e;
  }
  downloadBlob(blob!, "movements.csv");
}
