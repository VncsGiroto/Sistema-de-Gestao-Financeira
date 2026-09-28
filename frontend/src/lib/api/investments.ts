import { request } from "./http";

export interface Asset {
  id: number;
  ticker: string;
  name: string | null;
  asset_class: string;
  subtype: string;
  custodian: string | null;
  currency: string;
  category_id: number | null;
  rate_type: string | null;
  rate: string | null;
  maturity_date: string | null;
}

export interface AssetBody {
  ticker: string;
  name?: string;
  asset_class: string;
  subtype: string;
  custodian?: string;
  category_id?: number;
  rate_type?: string;
  rate?: string;
  maturity_date?: string;
}

export interface Op {
  id: number;
  asset_id: number;
  kind: string;
  date: string;
  quantity: string | null;
  price: string | null;
  fees: string;
  amount: string;
  transaction_id: number | null;
}

export interface OpBody {
  kind: string;
  date: string;
  quantity?: string;
  price?: string;
  fees?: string;
  amount?: string;
  account_id?: number;
  category_id?: number;
}

export interface Position {
  asset_id: number;
  quantity: string;
  average_price: string;
  invested: string;
  aportes: string;
  resgates: string;
  rendimentos: string;
  current_price: string | null;
  price_source: string | null;
  price_as_of: string | null;
  current_value: string | null;
  pnl: string | null;
  profitability: string | null;
}

export interface Returns {
  asset_id: number;
  start: string | null;
  end: string;
  simple: string | null;
  xirr: string | null;
  twr: string | null;
  twr_annualized: string | null;
  benchmarks: { cdi: string | null; ibov: string | null; ipca: string | null };
}

export const assetsApi = {
  list: (asset_class: string | undefined, access: string) =>
    request<Asset[]>(`/assets${asset_class ? `?asset_class=${asset_class}` : ""}`, {}, access),
  create: (body: AssetBody, access: string) =>
    request<Asset>("/assets", { method: "POST", body: JSON.stringify(body) }, access),
  patch: (id: number, body: Partial<AssetBody>, access: string) =>
    request<Asset>(`/assets/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/assets/${id}`, { method: "DELETE" }, access),
  ops: (id: number, access: string) =>
    request<Op[]>(`/assets/${id}/ops`, {}, access),
  addOp: (id: number, body: OpBody, access: string) =>
    request<Op>(`/assets/${id}/ops`, { method: "POST", body: JSON.stringify(body) }, access),
  removeOp: (id: number, opId: number, access: string) =>
    request<void>(`/assets/${id}/ops/${opId}`, { method: "DELETE" }, access),
  position: (id: number, access: string) =>
    request<Position>(`/assets/${id}/position`, {}, access),
  returns: (id: number, access: string) =>
    request<Returns>(`/assets/${id}/returns`, {}, access),
  setPrice: (id: number, date: string, price: string, access: string) =>
    request(`/assets/${id}/prices`, { method: "POST", body: JSON.stringify({ date, price }) }, access),
};
