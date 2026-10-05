import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Payable, PayableBody, PayableScheduleItem, PayBody } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";

const STALE = 30_000;

export function usePayables(kind?: string, upcomingDays?: number) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["payables", kind ?? "all", upcomingDays ?? "all"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const path = upcomingDays
        ? `/payables/upcoming?days=${upcomingDays}`
        : `/payables${kind ? `?kind=${kind}` : ""}`;
      const { data } = await api.authFetch<Payable[]>(path, access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function usePayableHistory(id: number | null) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["payable-history", id],
    queryFn: async () => {
      if (!access || !id) throw new Error("Sem sessão");
      return api.authed((t) => api.payables.history(id, t), access, refresh);
    },
    staleTime: STALE,
    enabled: !!access && !!id,
  });
}

export function usePayableSchedule(id: number | null) {  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["payable-schedule", id],
    queryFn: async () => {
      if (!access || !id) throw new Error("Sem sessão");
      const { data } = await api.authFetch<PayableScheduleItem[]>(
        `/payables/${id}/schedule`, access, refresh,
      );
      return data;
    },
    staleTime: STALE,
    enabled: !!access && !!id,
  });
}

export function usePayableMutations() {
  const qc = useQueryClient();
  const { access, refresh } = useAuth();
  const run = <T,>(fn: (tok: string) => Promise<T>) => {
    if (!access) return Promise.reject(new Error("Sem sessão"));
    return api.authed(fn, access, refresh);
  };
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["payables"] });
    qc.invalidateQueries({ queryKey: ["payable-schedule"] });
    qc.invalidateQueries({ queryKey: ["txs"] });
  };
  return {
    create: useMutation({ mutationFn: (b: PayableBody) => run((t) => api.payables.create(b, t)), onSuccess: inv }),
    patch: useMutation({
      mutationFn: (v: { id: number; body: Partial<PayableBody> }) => run((t) => api.payables.patch(v.id, v.body, t)),
      onSuccess: inv,
    }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.payables.remove(id, t)), onSuccess: inv }),
    pay: useMutation({
      mutationFn: (v: { id: number; body: PayBody }) => run((t) => api.payables.pay(v.id, v.body, t)),
      onSuccess: inv,
    }),
  };
}
