import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api-client";
import type { Bill, BillBody } from "../../lib/api-client";
import { useAuth } from "../../lib/auth-store";

const STALE = 30_000;

export function useBills(upcomingDays?: number) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["bills", upcomingDays ?? "all"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const path = upcomingDays ? `/bills/upcoming?days=${upcomingDays}` : "/bills";
      const { data } = await api.authFetch<Bill[]>(path, access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function useBillMutations() {
  const qc = useQueryClient();
  const { access, refresh } = useAuth();
  const run = <T,>(fn: (tok: string) => Promise<T>) => {
    if (!access) return Promise.reject(new Error("Sem sessão"));
    return api.authed(fn, access, refresh);
  };
  const inv = () => qc.invalidateQueries({ queryKey: ["bills"] });
  return {
    create: useMutation({ mutationFn: (b: BillBody) => run((t) => api.bills.create(b, t)), onSuccess: inv }),
    patch: useMutation({
      mutationFn: (v: { id: number; body: Partial<BillBody> }) => run((t) => api.bills.patch(v.id, v.body, t)),
      onSuccess: inv,
    }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.bills.remove(id, t)), onSuccess: inv }),
  };
}
