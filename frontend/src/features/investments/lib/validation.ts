import type { Asset } from "../../../lib/api";

export function parseNum(s: string): number {
  return Number(s.trim().replace(",", "."));
}

export function isContracted(asset: Asset): boolean {
  return asset.asset_class === "RENDA_FIXA" && (asset.rate_type === "CDI_PCT" || asset.rate_type === "PREFIXADO");
}

export function hasOpsPosition(pos: { aportes: string; resgates: string; rendimentos: string; reinvestimentos: string } | null | undefined): boolean {
  if (pos == null) return false;
  return Number(pos.aportes) > 0 || Number(pos.resgates) > 0 || Number(pos.rendimentos) > 0 || Number(pos.reinvestimentos) > 0;
}
