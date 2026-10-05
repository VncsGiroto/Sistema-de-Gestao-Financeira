import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { Asset, AssetBody, Position, Returns } from "../../lib/api";
import { brl } from "../../lib/money";
import { todayISO } from "../../lib/date";
import {
  assetClassLabel,
  labelOf,
  opKindHelp,
  opKindLabel,
  priceSourceLabel,
  rateTypeHelp,
  rateTypeLabel,
} from "../../lib/labels";
import { Badge, Button, PageHeader, useConfirm } from "../../components/ui";
import { useAuth } from "../../lib/auth-store";
import { useAccounts } from "../finance/hooks";
import { useAssetMutations, useAssets, useOps } from "./hooks";

const CLASSES = [
  "RENDA_FIXA",
  "RENDA_VARIAVEL",
  "FUNDOS",
  "CRIPTO",
  "OUTROS",
] as const;
const RATE_TYPES = ["CDI_PCT", "PREFIXADO", "IPCA_MAIS"] as const;

function pct(v: string | null): string {
  if (v == null) return "—";
  return `${(Number(v) * 100).toFixed(2)}%`;
}

function AssetDetail({ asset }: { asset: Asset }) {
  const { access, refresh } = useAuth();
  const { data: accounts } = useAccounts();
  const m = useAssetMutations();
  const { data: ops } = useOps(asset.id);
  const confirm = useConfirm();
  const [msg, setMsg] = useState("");
  const [kind, setKind] = useState("APORTE");
  const [date, setDate] = useState(todayISO);
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [amount, setAmount] = useState("");
  const [accountId, setAccountId] = useState("");
  const [mdate, setMdate] = useState(todayISO);
  const [mprice, setMprice] = useState("");

  const isRendimento = kind === "RENDIMENTO";

  const posQ = useQuery({
    queryKey: ["position", asset.id],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Position>(
        `/assets/${asset.id}/position`,
        access,
        refresh,
      );
      return data;
    },
    enabled: !!access,
  });
  const retQ = useQuery({
    queryKey: ["returns", asset.id],
    queryFn: async () => {
      if (!access) throw new Error("Sem sessão");
      const { data } = await api.authFetch<Returns>(
        `/assets/${asset.id}/returns`,
        access,
        refresh,
      );
      return data;
    },
    enabled: !!access,
  });
  const pos = posQ.data;
  const ret = retQ.data;
  const hasOps =
    pos != null &&
    (Number(pos.aportes) > 0 ||
      Number(pos.resgates) > 0 ||
      Number(pos.rendimentos) > 0);

  async function onOp(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!isRendimento && (!qty.trim() || !price.trim()))
      return setMsg("Aporte/resgate exige quantidade e preço.");
    if (isRendimento && !amount.trim())
      return setMsg("Rendimento exige valor.");
    if (isRendimento && !accountId)
      return setMsg("Rendimento exige a conta de destino.");
    try {
      await m.addOp.mutateAsync({
        id: asset.id,
        body: {
          kind,
          date,
          ...(!isRendimento
            ? { quantity: qty.trim(), price: price.trim() }
            : {}),
          ...(isRendimento
            ? { amount: amount.trim(), account_id: Number(accountId) }
            : {}),
        },
      });
      setQty("");
      setPrice("");
      setAmount("");
      posQ.refetch();
      retQ.refetch();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao lançar.");
    }
  }

  async function onPrice(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!mprice.trim()) return setMsg("Informe o preço.");
    try {
      await m.setPrice.mutateAsync({
        id: asset.id,
        date: mdate,
        price: mprice.trim(),
      });
      setMprice("");
      posQ.refetch();
      retQ.refetch();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao precificar.");
    }
  }

  async function onDelOp(opId: number, kind: string) {
    setMsg("");
    const ok = await confirm.ask({
      title: "Excluir operação?",
      body: kind === "RENDIMENTO"
        ? "A operação e a receita espelhada no extrato serão removidas."
        : "A operação será removida e a posição recalculada.",
      confirmLabel: "Excluir operação",
    });
    if (!ok) return;
    try {
      await m.delOp.mutateAsync({ id: asset.id, opId });
    } catch {
      setMsg("Falha ao excluir operação.");
    }
  }

  return (
    <div>
      {confirm.dialog}
      {pos && !hasOps && (
        <p>Lance um aporte abaixo para começar — a posição aparece aqui.</p>
      )}
      {pos && hasOps && (
        <p>
          Qtd {pos.quantity} · médio {brl(pos.average_price)} · investido{" "}
          {brl(pos.invested)}
          {pos.current_value != null && (
            <>
              {" "}
              · atual {brl(pos.current_value)}{" "}
              <Badge tone="blue">
                {labelOf(priceSourceLabel, pos.price_source)} {pos.price_as_of}
              </Badge>{" "}
              · P&L {brl(pos.pnl)} · {pct(pos.profitability)}
            </>
          )}
          {pos.current_value == null && (
            <>
              {" "}
              ·{" "}
              <Badge tone="amber">
                Sem preço — informe o preço manual abaixo
              </Badge>
            </>
          )}
        </p>
      )}
      {ret && (ret.simple != null || ret.xirr != null || ret.twr != null) && (
        <p>
          Simples {pct(ret.simple)} · XIRR {pct(ret.xirr)} · TWR {pct(ret.twr)}{" "}
          ({pct(ret.twr_annualized)} a.a.)
          {ret.benchmarks && (
            <>
              {" "}
              · CDI {pct(ret.benchmarks.cdi)} · IPCA {pct(ret.benchmarks.ipca)}
            </>
          )}
        </p>
      )}
      <form onSubmit={onOp} className="fw-row">
        <select
          className="fw-select"
          aria-label="Tipo de operação"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="APORTE">Aporte (compra)</option>
          <option value="RESGATE">Resgate (venda)</option>
          <option value="RENDIMENTO">Rendimento (vira receita)</option>
        </select>
        <span>{opKindHelp[kind]}</span>
        <input
          className="fw-input"
          aria-label="Data da operação"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        {!isRendimento ? (
          <>
            <input
              className="fw-input"
              aria-label="Quantidade (cotas/unidades)"
              placeholder="Quantidade"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />
            <input
              className="fw-input"
              aria-label="Preço unitário em R$"
              placeholder="Preço"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </>
        ) : (
          <>
            <input
              className="fw-input"
              aria-label="Valor do rendimento em R$ (vira receita no extrato)"
              placeholder="Valor (rendimento)"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <select
              className="fw-select"
              aria-label="Conta de destino do rendimento"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
            >
              <option value="">Conta (rendimento)...</option>
              {(accounts ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </>
        )}
        <Button size="sm">Lançar</Button>
      </form>
      <form onSubmit={onPrice} className="fw-row">        <input
          className="fw-input"
          aria-label="Data de referência do preço"
          type="date"
          value={mdate}
          onChange={(e) => setMdate(e.target.value)}
        />
        <input
          className="fw-input"
          aria-label="Preço manual por unidade em R$"
          placeholder="Preço manual"
          value={mprice}
          onChange={(e) => setMprice(e.target.value)}
        />
        <Button size="sm" variant="ghost">
          Precificar
        </Button>
      </form>
      <h4>Histórico de operações ({(ops ?? []).length})</h4>
      {(ops ?? []).length === 0 && <p>Nenhuma operação lançada.</p>}
      <ul className="fw-list">
        {(ops ?? []).map((o) => (
          <li className="fw-list-item" key={o.id}>
            <span>
              {o.date} — {labelOf(opKindLabel, o.kind)} — {o.quantity != null ? `${o.quantity} un. × ` : ""}{o.price != null ? brl(o.price) : brl(o.amount)}
              {o.fees !== "0" && o.fees !== "0.00" ? ` (taxas ${brl(o.fees)})` : ""}
            </span>
            <Button size="sm" variant="danger" onClick={() => onDelOp(o.id, o.kind)}>Excluir</Button>
          </li>
        ))}
      </ul>
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
  const confirm = useConfirm();

  async function onDelete(id: number, ticker: string) {
    setMsg("");
    const ok = await confirm.ask({
      title: "Excluir ativo?",
      body: `“${ticker}” e todo o seu histórico de operações serão excluídos. Rendimentos espelhados no extrato também serão removidos.`,
      confirmLabel: "Excluir ativo",
    });
    if (!ok) return;
    try {
      await m.remove.mutateAsync(id);
    } catch {
      setMsg("Falha ao excluir.");
    }
  }

  const isRF = aclass === "RENDA_FIXA";

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!ticker.trim()) return setMsg("Informe o ticker.");
    try {
      const body: AssetBody = {
        ticker: ticker.trim(),
        asset_class: aclass,
        subtype,
      };
      if (isRF && rateType) {
        if (!rate.trim()) return setMsg("Contrato exige a taxa.");
        body.rate_type = rateType;
        body.rate = rate.trim();
        if (maturity) body.maturity_date = maturity;
      }
      await m.create.mutateAsync(body);
      setTicker("");
      setRateType("");
      setRate("");
      setMaturity("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <>
      <PageHeader
        title="Investimentos"
        sub="Ativos, operações, posição e rentabilidade."
      />
      {msg && <p className="fw-error">{msg}</p>}
      {confirm.dialog}
      <form onSubmit={onCreate} className="fw-row">
        <input
          className="fw-input"
          placeholder="Ticker"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
        />
        <select
          className="fw-select"
          value={aclass}
          onChange={(e) => setAclass(e.target.value)}
        >
          {CLASSES.map((c) => (
            <option key={c} value={c}>
              {labelOf(assetClassLabel, c)}
            </option>
          ))}
        </select>
        <input
          className="fw-input"
          placeholder="Subtipo"
          value={subtype}
          onChange={(e) => setSubtype(e.target.value)}
        />
        {isRF && (
          <>
            <select
              className="fw-select"
              value={rateType}
              onChange={(e) => setRateType(e.target.value)}
            >
              <option value="">Sem contrato (preço manual)</option>
              {RATE_TYPES.map((r) => (
                <option key={r} value={r}>
                  {labelOf(rateTypeLabel, r)}
                </option>
              ))}
            </select>
            {rateType && <span>{rateTypeHelp[rateType]}</span>}
            {rateType && (
              <>
                <input
                  className="fw-input"
                  aria-label={rateType === "CDI_PCT" ? "Percentual do CDI" : "Taxa anual em %"}
                  placeholder="Taxa (% CDI ou % a.a.)"
                  value={rate}
                  onChange={(e) => setRate(e.target.value)}
                />
                <input
                  className="fw-input"
                  aria-label="Vencimento do contrato"
                  type="date"
                  value={maturity}
                  onChange={(e) => setMaturity(e.target.value)}
                />
              </>
            )}
          </>
        )}
        <Button>Criar</Button>
        <select
          className="fw-select"
          value={cls}
          onChange={(e) => setCls(e.target.value)}
        >
          <option value="">Todas as classes</option>
          {CLASSES.map((c) => (
            <option key={c} value={c}>
              {labelOf(assetClassLabel, c)}
            </option>
          ))}
        </select>
      </form>
      {isLoading && <p>Carregando...</p>}
      {!isLoading && (data ?? []).length === 0 && (
        <p>Nenhum ativo ainda — crie o primeiro acima.</p>
      )}
      <ul className="fw-list">
        {(data ?? []).map((a) => (
          <li className="fw-list-item" key={a.id}>
            <span>
              {a.ticker} <Badge>{labelOf(assetClassLabel, a.asset_class)}</Badge>
            </span>
            <span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setOpenId(openId === a.id ? null : a.id)}
              >
                Detalhar
              </Button>{" "}
              <Button
                size="sm"
                variant="danger"
                onClick={() => onDelete(a.id, a.ticker)}
              >
                Excluir
              </Button>
            </span>
            {openId === a.id && <AssetDetail asset={a} />}
          </li>
        ))}
      </ul>
    </>
  );
}
