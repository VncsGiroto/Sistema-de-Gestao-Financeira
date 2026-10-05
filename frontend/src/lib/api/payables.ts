import { request } from "./http";
import type { TxPage } from "./transactions";

export interface Payable {
  id: number;
  description: string;
  kind: string;
  amount: string | null;
  periodicity: string | null;
  due_day: number | null;
  next_due: string | null;
  total_amount: string | null;
  num_installments: number | null;
  installment_amount: string | null;
  first_due_date: string | null;
  paid_ns: number[];
  paid_at: string | null;
  account_id: number | null;
  category_id: number | null;
}

export interface PayableBody {
  description: string;
  kind: string;
  amount?: string;
  periodicity?: string;
  due_day?: number;
  next_due?: string;
  total_amount?: string;
  num_installments?: number;
  first_due_date?: string;
  account_id?: number;
  category_id?: number;
}

export interface PayableScheduleItem {
  n: number;
  due_date: string;
  amount: string;
  paid: boolean;
}

export interface PayBody {
  account_id: number;
  amount?: string;
  date?: string;
  category_id?: number;
  ns?: number[];
  discount?: string;
}

export interface PayResult {
  transactions: { id: number; description: string; amount: string; date: string }[];
  payable: Payable;
}

export const payablesApi = {
  list: (kind: string | undefined, access: string) =>
    request<Payable[]>(`/payables${kind ? `?kind=${kind}` : ""}`, {}, access),
  upcoming: (days: number, access: string) =>
    request<Payable[]>(`/payables/upcoming?days=${days}`, {}, access),
  create: (body: PayableBody, access: string) =>
    request<Payable>("/payables", { method: "POST", body: JSON.stringify(body) }, access),
  patch: (id: number, body: Partial<PayableBody>, access: string) =>
    request<Payable>(`/payables/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/payables/${id}`, { method: "DELETE" }, access),
  schedule: (id: number, access: string) =>
    request<PayableScheduleItem[]>(`/payables/${id}/schedule`, {}, access),
  pay: (id: number, body: PayBody, access: string) =>
    request<PayResult>(`/payables/${id}/pay`, { method: "POST", body: JSON.stringify(body) }, access),
  history: (id: number, access: string) =>
    request<TxPage>(`/transactions?payable_id=${id}&per_page=100`, {}, access),
};
