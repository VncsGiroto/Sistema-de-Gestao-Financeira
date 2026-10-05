import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Asset, AssetBody, Op, OpBody, Portfolio } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";

const STALE = 30_000;

export function useAssets(asset_class?: string) {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["assets", asset_class ?? "all"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Asset[]>(
        `/assets${asset_class ? `?asset_class=${asset_class}` : ""}`, access, refresh,
      );
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function usePortfolio() {
  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Portfolio>("/portfolio", access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access,
  });
}

export function useOps(assetId: number | null) {  const { access, refresh } = useAuth();
  return useQuery({
    queryKey: ["asset-ops", assetId],
    queryFn: async () => {
      if (!access || !assetId) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Op[]>(`/assets/${assetId}/ops`, access, refresh);
      return data;
    },
    staleTime: STALE,
    enabled: !!access && !!assetId,
  });
}

export function useAssetMutations() {
  const qc = useQueryClient();
  const { access, refresh } = useAuth();
  const run = <T,>(fn: (tok: string) => Promise<T>) => {
    if (!access) return Promise.reject(new Error("Sem sessão"));
    return api.authed(fn, access, refresh);
  };
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["assets"] });
    qc.invalidateQueries({ queryKey: ["asset-ops"] });
    qc.invalidateQueries({ queryKey: ["position"] });
    qc.invalidateQueries({ queryKey: ["returns"] });
    qc.invalidateQueries({ queryKey: ["txs"] });
  };
  return {
    create: useMutation({ mutationFn: (b: AssetBody) => run((t) => api.assets.create(b, t)), onSuccess: inv }),
    remove: useMutation({ mutationFn: (id: number) => run((t) => api.assets.remove(id, t)), onSuccess: inv }),
    addOp: useMutation({
      mutationFn: (v: { id: number; body: OpBody }) => run((t) => api.assets.addOp(v.id, v.body, t)),
      onSuccess: inv,
    }),
    delOp: useMutation({
      mutationFn: (v: { id: number; opId: number }) => run((t) => api.assets.removeOp(v.id, v.opId, t)),
      onSuccess: inv,
    }),
    setPrice: useMutation({
      mutationFn: (v: { id: number; date: string; price: string }) =>
        run((t) => api.assets.setPrice(v.id, v.date, v.price, t)),
      onSuccess: inv,
    }),
  };
}
