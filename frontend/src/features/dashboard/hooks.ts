import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { CommitmentsData, DashboardData } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";

export interface DashboardFilters {
  from?: string;
  to?: string;
  account_id?: number;
}

export function useDashboard(f: DashboardFilters) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["dashboard", f.from, f.to, f.account_id],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const sp = new URLSearchParams();
      if (f.from) sp.set("from", f.from);
      if (f.to) sp.set("to", f.to);
      if (f.account_id) sp.set("account_id", String(f.account_id));
      const q = sp.toString();
      const { data } = await api.authFetch<DashboardData>(`/dashboard${q ? `?${q}` : ""}`, access, refresh);
      return data;
    },
    staleTime: 30_000,
    enabled: !!access,
  });
}

export function useCommitments(horizonDays: number) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["commitments", horizonDays],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<CommitmentsData>(
        `/dashboard/commitments?horizon_days=${horizonDays}`, access, refresh,
      );
      return data;
    },
    staleTime: 30_000,
    enabled: !!access,
  });
}
