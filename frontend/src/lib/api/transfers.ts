import { request } from "./http";

export interface Transfer {
  id: number;
  from_account_id: number | null;
  to_account_id: number | null;
  kind: string;
  amount: string;
  date: string;
  description: string;
  op_id: number | null;
  asset_id: number | null;
}

export interface TransferBody {
  from_account_id: number;
  to_account_id: number;
  amount: string;
  date?: string;
  description?: string;
}

export const transfersApi = {
  list: (account_id: number | undefined, access: string) =>
    request<Transfer[]>(`/transfers${account_id ? `?account_id=${account_id}` : ""}`, {}, access),
  create: (body: TransferBody, access: string) =>
    request<Transfer>("/transfers", { method: "POST", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/transfers/${id}`, { method: "DELETE" }, access),
};
