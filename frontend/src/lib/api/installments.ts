import { request } from "./http";

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

export interface CreateInstallmentBody {
  description: string;
  total_amount: string;
  num_installments: number;
  first_due_date: string;
  account_id?: number;
}

export const installmentsApi = {
  list: (access: string) => request<Installment[]>("/installments", {}, access),
  create: (body: CreateInstallmentBody, access: string) =>
    request<Installment>("/installments", { method: "POST", body: JSON.stringify(body) }, access),
  schedule: (id: number, access: string) =>
    request<ScheduleItem[]>(`/installments/${id}/schedule`, {}, access),
  remove: (id: number, access: string) =>
    request<void>(`/installments/${id}`, { method: "DELETE" }, access),
};
