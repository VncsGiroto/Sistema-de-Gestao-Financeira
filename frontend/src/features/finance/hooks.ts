import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api-client";
import type { Account, Category, TxFilters, TxPage } from "../../lib/api-client";
import { useAuth } from "../../lib/auth-store";

const STALE = 30_000;

function useAuthed() {
  const { access, refresh } = useAuth();
  return {
    access,
    run: <T,>(fn: (tok: string) => Promise<T>) => {
      if (!access) return Promise.reject(new Error("Sem sessão"));
      return api.authed(fn, access, refresh);
    },
  };
}

export function useAccounts() {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Account[]>("/accounts", access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function useAccountMutations() {
  const qc = useQueryClient();
  const { run } = useAuthed();
  const inv = () => qc.invalidateQueries({ queryKey: ["accounts"] });
  return {
    create: useMutation({ mutationFn: (b: { name: string; bank?: string; account_type: string; initial_balance?: string }) => run((t) => api.accounts.create(b, t)), onSuccess: inv }),
    patch: useMutation({ mutationFn: (v: { id: number; body: { name?: string; bank?: string } }) => run((t) => api.accounts.patch(v.id, v.body, t)), onSuccess: inv }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.accounts.remove(id, t)), onSuccess: inv }),
  };
}

export function useCategories(type?: string) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["categories", type ?? "all"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const q = type ? `?type=${type}` : "";
      const { data } = await api.authFetch<Category[]>(`/categories${q}`, access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function useCategoryMutations() {
  const qc = useQueryClient();
  const { run } = useAuthed();
  const inv = () => qc.invalidateQueries({ queryKey: ["categories"] });
  return {
    create: useMutation({ mutationFn: (b: { name: string; type: string }) => run((t) => api.categories.create(b, t)), onSuccess: inv }),
    patch: useMutation({ mutationFn: (v: { id: number; name: string }) => run((t) => api.categories.patch(v.id, { name: v.name }, t)), onSuccess: inv }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.categories.remove(id, t)), onSuccess: inv }),
  };
}

export function useTxs(f: TxFilters) {
  const { access, refresh } = useAuth();
  const key = ["txs", f.from, f.to, f.account_id, f.category_id, f.type, f.q, f.page, f.per_page];
  return useQuery({
    queryKey: key,
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const sp = new URLSearchParams();
      if (f.from) sp.set("from", f.from);
      if (f.to) sp.set("to", f.to);
      if (f.account_id) sp.set("account_id", String(f.account_id));
      if (f.category_id) sp.set("category_id", String(f.category_id));
      if (f.type) sp.set("type", f.type);
      if (f.q) sp.set("q", f.q);
      sp.set("page", String(f.page ?? 1));
      sp.set("per_page", String(f.per_page ?? 20));
      const { data } = await api.authFetch<TxPage>(`/transactions?${sp}`, access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function useTxMutations() {
  const qc = useQueryClient();
  const { run } = useAuthed();
  const inv = () => qc.invalidateQueries({ queryKey: ["txs"] });
  return {
    create: useMutation({
      mutationFn: (b: { account_id: number; category_id: number | null; date: string; description: string; amount: string; type: string }) =>
        run((t) => api.txs.create(b, t)),
      onSuccess: inv,
    }),
    patch: useMutation({
      mutationFn: (v: { id: number; body: Partial<{ category_id: number | null; description: string; amount: string; type: string }> }) =>
        run((t) => api.txs.patch(v.id, v.body, t)),
      onSuccess: inv,
    }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.txs.remove(id, t)), onSuccess: inv }),
  };
}
