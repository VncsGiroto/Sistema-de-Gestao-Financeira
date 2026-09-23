import { request } from "./http";

export interface Account {
  id: number;
  name: string;
  bank: string | null;
  account_type: string;
  initial_balance: string;
}

export interface CreateAccountBody {
  name: string;
  bank?: string;
  account_type: string;
  initial_balance?: string;
}

export type PatchAccountBody = Partial<Pick<Account, "name" | "bank" | "account_type">>;

export const accountsApi = {
  list: (access: string) => request<Account[]>("/accounts", {}, access),
  create: (body: CreateAccountBody, access: string) =>
    request<Account>("/accounts", { method: "POST", body: JSON.stringify(body) }, access),
  patch: (id: number, body: PatchAccountBody, access: string) =>
    request<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/accounts/${id}`, { method: "DELETE" }, access),
};
