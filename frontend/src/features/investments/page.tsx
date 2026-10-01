import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { Asset, AssetBody, Position, Returns } from "../../lib/api";
import { brl } from "../../lib/money";
import { Badge, Button, PageHeader } from "../../components/ui";
import { useAuth } from "../../lib/auth-store";
import { useAccounts } from "../finance/hooks";
import { useAssetMutations, useAssets } from "./hooks";

const CLASSES = ["RENDA_FIXA", "RENDA_VARIAVEL", "FUNDOS", "CRIPTO", "OUTROS"] as const;
const RATE_TYPES = ["CDI_PCT", "PREFIXADO", "IPCA_MAIS"] as const;

function pct(v: string | null): string {
  if (v == null) return "—";
  return `${(Number(v) * 100).toFixed(2)}%`;
}

function AssetDetail({ asset }: { asset: Asset }) {
  const { access, refresh } = useAuth();
  const { data: accounts } = useAccounts();
  const m = useAssetMutations();
  const [msg, setMsg] = useState("");
  const [kind, setKind] = useState("APORTE");
  const [date, setDate] = useState("2026-09-28");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [amount, setAmount] = useState("");
  const [accountId, setAccountId] = useState("");
  const [mdate, setMdate] = useState("2026-09-28");
  const [mprice, setMprice] = useState("");

  const isRendimento = kind === "RENDIMENTO";

  const posQ = useQuery({
    queryKey: ["position", asset.id],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Position>(`/assets/${asset.id}/position`, access, refresh);
      return data;
    },
    enabled: !!access,
  });
  const retQ = useQuery({
    queryKey: ["returns", asset.id],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Returns>(`/assets/${asset.id}/returns`, access, refresh);
      return data;
    },
    enabled: !!access,
  });
  const pos = posQ.data;
  const ret = retQ.data;
  const hasOps = pos != null && (Number(pos.aportes) > 0 || Number(pos.resgates) > 0 || Number(pos.rendimentos) > 0);

  async function onOp(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!isRendimento && (!qty.trim() || !price.trim())) return setMsg("Aporte/resgate exige quantidade e preço.");
    if (isRendimento && !amount.trim()) return setMsg("Rendimento exige valor.");
    if (isRendimento && !accountId) return setMsg("Rendimento exige a conta de destino.");
    try {
      await m.addOp.mutateAsync({
        id: asset.id,
        body: {
          kind, date,
          ...(!isRendimento ? { quantity: qty.trim(), price: price.trim() } : {}),
          ...(isRendimento ? { amount: amount.trim(), account_id: Number(accountId) } : {}),
        },
      });
      setQty(""); setPrice(""); setAmount("");
      posQ.refetch(); retQ.refetch();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao lançar.");
    }
  }

  async function onPrice(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!mprice.trim()) return setMsg("Informe o preço.");
    try {
      await m.setPrice.mutateAsync({ id: asset.id, date: mdate, price: mprice.trim() });
      setMprice("");
      posQ.refetch(); retQ.refetch();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao precificar.");
    }
  }

  return (
    <div>
      {pos && !hasOps && (
        <p>Lance um aporte abaixo para começar — a posição aparece aqui.</p>
      )}
      {pos && hasOps && (
        <p>
          Qtd {pos.quantity} · médio {brl(pos.average_price)} · investido {brl(pos.invested)}
          {pos.current_value != null && (
            <> · atual {brl(pos.current_value)} <Badge tone="blue">{pos.price_source} {pos.price_as_of}</Badge> · P&L {brl(pos.pnl)} · {pct(pos.profitability)}</>
          )}
          {pos.current_value == null && (
            <> · <Badge tone="amber">Sem preço — informe o preço manual abaixo</Badge></>
          )}
        </p>
      )}
      {ret && (ret.simple != null || ret.xirr != null || ret.twr != null) && (
        <p>
          Simples {pct(ret.simple)} · XIRR {pct(ret.xirr)} · TWR {pct(ret.twr)} ({pct(ret.twr_annualized)} a.a.)
          {ret.benchmarks && (
            <> · CDI {pct(ret.benchmarks.cdi)} · IPCA {pct(ret.benchmarks.ipca)}</>
          )}
        </p>
      )}
      <form onSubmit={onOp} className="fw-row">
        <select className="fw-select" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="APORTE">Aporte (compra)</option>
          <option value="RESGATE">Resgate (venda)</option>
          <option value="RENDIMENTO">Rendimento (vira receita)</option>
        </select>
        <input className="fw-input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        {!isRendimento ? (
          <>
            <input className="fw-input" placeholder="Quantidade" value={qty} onChange={(e) => setQty(e.target.value)} />
            <input className="fw-input" placeholder="Preço" value={price} onChange={(e) => setPrice(e.target.value)} />
          </>
        ) : (
          <>
            <input className="fw-input" placeholder="Valor (rendimento)" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <select className="fw-select" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
              <option value="">Conta (rendimento)...</option>
              {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </>
        )}
        <Button size="sm">Lançar</Button>
      </form>
      <form onSubmit={onPrice} className="fw-row">
        <input className="fw-input" type="date" value={mdate} onChange={(e) => setMdate(e.target.value)} />
        <input className="fw-input" placeholder="Preço manual" value={mprice} onChange={(e) => setMprice(e.target.value)} />
        <Button size="sm" variant="ghost">Precificar</Button>
        <span>Use quando não houver cotação automática (ex.: ticker fora da B3).</span>
      </form>
      {msg && <p className="fw-error">{msg}</p>}
    </div>
  );
}

export function InvestmentsPage() {
  const [cls, setCls] = useState("");
  const { data, isLoading } = useAssets(cls || undefined);
  const m = useAssetMutations();
  const [msg, setMsg] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [ticker, setTicker] = useState("");
  const [aclass, setAclass] = useState("RENDA_VARIAVEL");
  const [subtype, setSubtype] = useState("ACAO");
  const [rateType, setRateType] = useState("");
  const [rate, setRate] = useState("");
  const [maturity, setMaturity] = useState("");

  const isRF = aclass === "RENDA_FIXA";

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!ticker.trim()) return setMsg("Informe o ticker.");
    try {
      const body: AssetBody = { ticker: ticker.trim(), asset_class: aclass, subtype };
      if (isRF && rateType) {
        if (!rate.trim()) return setMsg("Contrato exige a taxa.");
        body.rate_type = rateType;
        body.rate = rate.trim();
        if (maturity) body.maturity_date = maturity;
      }
      await m.create.mutateAsync(body);
      setTicker(""); setRateType(""); setRate(""); setMaturity("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <>
      <PageHeader title="Investimentos" sub="Ativos, operações, posição e rentabilidade." />
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row">
        <input className="fw-input" placeholder="Ticker" value={ticker} onChange={(e) => setTicker(e.target.value)} />
        <select className="fw-select" value={aclass} onChange={(e) => setAclass(e.target.value)}>
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input className="fw-input" placeholder="Subtipo" value={subtype} onChange={(e) => setSubtype(e.target.value)} />
        {isRF && (
          <>
            <select className="fw-select" value={rateType} onChange={(e) => setRateType(e.target.value)}>
              <option value="">Sem contrato (preço manual)</option>
              {RATE_TYPES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {rateType && (
              <>
                <input className="fw-input" placeholder="Taxa (% CDI ou % a.a.)" value={rate} onChange={(e) => setRate(e.target.value)} />
                <input className="fw-input" type="date" value={maturity} onChange={(e) => setMaturity(e.target.value)} />
              </>
            )}
          </>
        )}
        <Button>Criar</Button>
        <select className="fw-select" value={cls} onChange={(e) => setCls(e.target.value)}>
          <option value="">Todas as classes</option>
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </form>
      <p>B3 (ex.: PETR4, MXRF11) tem preço automático; ticker fora da B3 use o preço manual abaixo do ativo.</p>
      {isLoading && <p>Carregando...</p>}
      {!isLoading && (data ?? []).length === 0 && <p>Nenhum ativo ainda — crie o primeiro acima.</p>}
      <ul className="fw-list">
        {(data ?? []).map((a) => (
          <li className="fw-list-item" key={a.id}>
            <span>
              {a.ticker} <Badge>{a.asset_class}</Badge>
            </span>
            <span>
              <Button size="sm" variant="ghost" onClick={() => setOpenId(openId === a.id ? null : a.id)}>Detalhar</Button>{" "}
              <Button size="sm" variant="danger" onClick={() => m.remove.mutateAsync(a.id)}>Excluir</Button>
            </span>
            {openId === a.id && <AssetDetail asset={a} />}
          </li>
        ))}
      </ul>
    </>
  );
}
