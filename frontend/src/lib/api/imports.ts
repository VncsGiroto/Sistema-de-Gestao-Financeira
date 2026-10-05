import { request, requestForm } from "./http";
import type { Tx, TxPage } from "./transactions";

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
  decision: string | null;
}

export interface ReviewDecision {
  item_id: number;
  decision: string;
}

export interface BulkCategorizeResult {
  updated: number;
  skipped_type: number;
  skipped_missing: number;
}

export interface UploadImportResult {
  import_id: number;
  status: string;
}

export interface CommitImportResult {
  imported_rows: number;
  duplicate_rows: number;
  skipped: number;
}

export const importsApi = {
  upload: (account_id: number, file: File, access: string) => {
    const fd = new FormData();
    fd.set("account_id", String(account_id));
    fd.set("file", file);
    return requestForm<UploadImportResult>("/imports/ofx", fd, access);
  },
  list: (access: string) => request<ImportJob[]>("/imports", {}, access),
  get: (id: number, access: string) => request<ImportJob>(`/imports/${id}`, {}, access),
  items: (id: number, verdict: string | undefined, access: string) =>
    request<ImportItem[]>(
      `/imports/${id}/items${verdict ? `?verdict=${verdict}` : ""}`,
      {},
      access,
    ),
  review: (id: number, decisions: ReviewDecision[], access: string) =>
    request<{ decided: number }>(
      `/imports/${id}/review`,
      { method: "POST", body: JSON.stringify({ decisions }) },
      access,
    ),
  commit: (id: number, access: string) =>
    request<CommitImportResult>(`/imports/${id}/commit`, { method: "POST" }, access),
  matched: (txId: number, access: string) => request<Tx>(`/transactions/${txId}`, {}, access),
  batch: (id: number, access: string) =>
    request<TxPage>(`/transactions?import_id=${id}&per_page=100`, {}, access),
};
