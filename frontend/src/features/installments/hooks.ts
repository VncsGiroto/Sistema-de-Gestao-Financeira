import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api-client";
import type { Installment, ScheduleItem } from "../../lib/api-client";
import { useAuth } from "../../lib/auth-store";

const STALE = 30_000;

export function useInstallments() {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["installments"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Installment[]>("/installments", access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function useSchedule(id: number | null) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["schedule", id],
    queryFn: async () => {
      if (!access || !id) throw new Error("Sem sessão");
      const { data } = await api.authFetch<ScheduleItem[]>(
        `/installments/${id}/schedule`, access, refresh,
      );
      return data;
    },
    staleTime: STALE,
    enabled: !!access && !!id,
  });
}

export function useInstallmentMutations() {
  const qc = useQueryClient();
  const { access, refresh } = useAuth();
  const run = <T,>(fn: (tok: string) => Promise<T>) => {
    if (!access) return Promise.reject(new Error("Sem sessão"));
    return api.authed(fn, access, refresh);
  };
  const inv = () => qc.invalidateQueries({ queryKey: ["installments"] });
  return {
    create: useMutation({
      mutationFn: (b: { description: string; total_amount: string; num_installments: number; first_due_date: string; account_id?: number }) =>
        run((t) => api.installments.create(b, t)),
      onSuccess: inv,
    }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.installments.remove(id, t)), onSuccess: inv }),
  };
}
