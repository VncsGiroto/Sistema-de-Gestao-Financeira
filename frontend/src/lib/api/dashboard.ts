import { qs, request } from "./http";

export interface CommitmentItem {
  kind: string;
  description: string;
  due_date: string;
  amount: string;
  ref_id: number;
  account_id: number | null;
}

export interface CommitmentsData {
  total: string;
  items: CommitmentItem[];
  unassigned_total: string;
}

export interface DashboardData {
  balance: string;
  income: { total: string; by_category: { name: string; total: string }[] };
  expense: { total: string; by_category: { name: string; total: string }[] };
  evolution: { month: string; income: string; expense: string }[];
}

export interface DashboardFilters {
  from?: string;
  to?: string;
  account_id?: number;
}

export const dashboardApi = {
  get: (f: DashboardFilters, access: string) =>
    request<DashboardData>(`/dashboard${qs({ ...f })}`, {}, access),
};
