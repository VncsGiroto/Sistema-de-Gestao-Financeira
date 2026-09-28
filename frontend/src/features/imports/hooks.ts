import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ImportJob, ImportItem } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";

export function useImports() {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["imports"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<ImportJob[]>("/imports", access, refresh);
      return data;
    },
    enabled: !!access,
    refetchInterval: (q) =>
      q.state.data?.some((i) => i.status === "RECEIVED" || i.status === "PROCESSING") ? 1500 : false,
  });
}

export function useImport(id: number) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["import", id],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<ImportJob>(`/imports/${id}`, access, refresh);
      return data;
    },
    enabled: !!access,
    refetchInterval: (q) =>
      q.state.data?.status === "RECEIVED" || q.state.data?.status === "PROCESSING" ? 1500 : false,
  });
}

export function useImportItems(id: number, verdict?: string) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["import-items", id, verdict ?? "all"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<ImportItem[]>(
        `/imports/${id}/items${verdict ? `?verdict=${verdict}` : ""}`, access, refresh,
      );
      return data;
    },
    enabled: !!access,
    refetchInterval: 2000,
  });
}

export function useImportMutations(id: number) {
  const qc = useQueryClient();
  const { access, refresh } = useAuth();
  const run = <T,>(fn: (tok: string) => Promise<T>) => {
    if (!access) return Promise.reject(new Error("Sem sessão"));
    return api.authed(fn, access, refresh);
  };
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["import", id] });
    qc.invalidateQueries({ queryKey: ["import-items", id] });
    qc.invalidateQueries({ queryKey: ["imports"] });
    qc.invalidateQueries({ queryKey: ["txs"] });
  };
  return {
    upload: useMutation({
      mutationFn: (v: { account_id: number; file: File }) => run((t) => api.imports.upload(v.account_id, v.file, t)),
      onSuccess: () => qc.invalidateQueries({ queryKey: ["imports"] }),
    }),
    review: useMutation({
      mutationFn: (decisions: { item_id: number; decision: string }[]) => run((t) => api.imports.review(id, decisions, t)),
      onSuccess: inv,
    }),
    commit: useMutation({ mutationFn: () => run((t) => api.imports.commit(id, t)), onSuccess: inv }),
  };
}
