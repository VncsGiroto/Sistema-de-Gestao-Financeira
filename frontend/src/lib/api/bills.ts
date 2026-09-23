import { request } from "./http";

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

export const billsApi = {
  list: (access: string) => request<Bill[]>("/bills", {}, access),
  upcoming: (days: number, access: string) => request<Bill[]>(`/bills/upcoming?days=${days}`, {}, access),
  create: (body: BillBody, access: string) =>
    request<Bill>("/bills", { method: "POST", body: JSON.stringify(body) }, access),
  patch: (id: number, body: Partial<BillBody>, access: string) =>
    request<Bill>(`/bills/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/bills/${id}`, { method: "DELETE" }, access),
};
