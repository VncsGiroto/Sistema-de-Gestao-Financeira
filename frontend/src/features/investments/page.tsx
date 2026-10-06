import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { Asset, AssetBody, Position, Returns } from "../../lib/api";
import { CategoryPie, SnapshotsLine } from "../dashboard/charts";
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
import { Badge, Button, Field, PageHeader, useConfirm } from "../../components/ui";
import { useAuth } from "../../lib/auth-store";
import { useAccounts } from "../finance/hooks";
import { useAssetMutations, useAssets, useOps, usePortfolio } from "./hooks";

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
  const contracted = asset.asset_class === "RENDA_FIXA" && (asset.rate_type === "CDI_PCT" || asset.rate_type === "PREFIXADO");

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
      Number(pos.rendimentos) > 0 ||
      Number(pos.reinvestimentos) > 0);

  async function onOp(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (contracted && (kind === "APORTE" || kind === "RESGATE" || kind === "REINVESTIMENTO") && !amount.trim())
      return setMsg("Informe o valor em reais.");
    if (!isRendimento && !contracted && (!qty.trim() || !price.trim()))
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
          ...(!isRendimento && !contracted
            ? { quantity: qty.trim(), price: price.trim() }
            : {}),
          ...(isRendimento || contracted
            ? { amount: amount.trim() }
            : {}),
          ...(isRendimento
            ? { account_id: Number(accountId) }
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

  async function onFullRescue() {
    setMsg("");
    const ok = await confirm.ask({
      title: "Resgatar tudo?",
      body: `Toda a posição de ${asset.ticker} será liquidada pelo valor atual do contrato.`,
      confirmLabel: "Resgatar tudo",
    });
    if (!ok) return;
    try {
      await m.addOp.mutateAsync({ id: asset.id, body: { kind: "RESGATE", date: todayISO(), full: true } });
      posQ.refetch();
      retQ.refetch();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao resgatar.");
    }
  }

  async function onPrice(ev: FormEvent, override = false) {
    ev.preventDefault();
    setMsg("");
    if (!mprice.trim()) return setMsg("Informe o preço.");
    try {
      await m.setPrice.mutateAsync({
        id: asset.id,
        date: mdate,
        price: mprice.trim(),
        ...(override ? { override: true } : {}),
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
      {pos && hasOps && contracted && (
        <p>
          Aplicado {brl(pos.invested)} · atual {pos.current_value != null ? brl(pos.current_value) : "—"}
          {pos.current_value != null && (
            <> · rendimento {brl(String(Number(pos.current_value) - Number(pos.invested)))}</>
          )}
          {pos.current_value != null && (
            <>
              {" "}
              <Badge tone="blue">
                {labelOf(priceSourceLabel, pos.price_source)} {pos.price_as_of}
              </Badge>
            </>
          )}
        </p>
      )}
      {pos && hasOps && !contracted && (
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
          Simples {pct(ret.simple)} · XIRR {pct(ret.xirr)} · <span title="Apreciação da cotação; exclui proventos reinvestidos">TWR de preço {pct(ret.twr)}</span>{" "}
          ({pct(ret.twr_annualized)} a.a.)
          {ret.benchmarks && (
            <>
              {" "}
              · CDI {pct(ret.benchmarks.cdi)} · IPCA {pct(ret.benchmarks.ipca)}
            </>
          )}
        </p>
      )}
      <form onSubmit={onOp} className="fw-row" style={{ alignItems: "flex-end" }}>
        <Field label="Operação" title={opKindHelp[kind]}>
          <select
            className="fw-select"
            style={{ width: "auto" }}
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="APORTE">Aporte (compra)</option>
            <option value="RESGATE">Resgate (venda)</option>
            <option value="RENDIMENTO">Rendimento (vira receita)</option>
            <option value="REINVESTIMENTO">Reinvestimento (compõe posição)</option>
          </select>
        </Field>
        <Field label="Data">
          <input
            className="fw-input"
            style={{ width: "auto" }}
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </Field>
        {!isRendimento && !contracted ? (
          <>
            <Field label="Quantidade de cotas">
              <input
                className="fw-input"
                style={{ width: "auto" }}
                placeholder="Ex.: 10"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
              />
            </Field>
            <Field label="Preço por cota (R$)">
              <input
                className="fw-input"
                style={{ width: "auto" }}
                placeholder="0,00"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </Field>
          </>
        ) : !isRendimento ? (
          <Field label="Valor (R$)">
            <input
              className="fw-input"
              style={{ width: "auto" }}
              placeholder="0,00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </Field>
        ) : (
          <>
            <Field label="Valor do rendimento (R$)">
              <input
                className="fw-input"
                style={{ width: "auto" }}
                placeholder="0,00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </Field>
            <Field label="Conta de destino">
              <select
                className="fw-select"
                style={{ width: "auto" }}
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
            </Field>
          </>
        )}
        <Button size="sm">Lançar</Button>
        {contracted && kind === "RESGATE" && (
          <Button size="sm" variant="danger" type="button" onClick={onFullRescue}>Resgatar tudo</Button>
        )}
      </form>
      {(!contracted || (pos && pos.current_price == null)) && (
      <form onSubmit={(e) => onPrice(e, contracted)} className="fw-row" style={{ alignItems: "flex-end" }}>
        {contracted && <span>Contrato sem cotação — preço manual como exceção explícita.</span>}
        <Field label="Data de referência">
          <input
            className="fw-input"
            style={{ width: "auto" }}
            type="date"
            value={mdate}
            onChange={(e) => setMdate(e.target.value)}
          />
        </Field>
        <Field label={contracted ? "Preço de exceção (R$)" : "Preço manual (R$)"}>
          <input
            className="fw-input"
            style={{ width: "auto" }}
            placeholder="0,00"
            value={mprice}
            onChange={(e) => setMprice(e.target.value)}
          />
        </Field>
        <Button size="sm" variant="ghost">
          Precificar
        </Button>
      </form>
      )}
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
  const { data: pf } = usePortfolio();
  const m = useAssetMutations();
  const [msg, setMsg] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [ticker, setTicker] = useState("");
  const [aclass, setAclass] = useState("RENDA_VARIAVEL");
  const [subtype, setSubtype] = useState("ACAO");
  const [accountId, setAccountId] = useState("");
  const [rateType, setRateType] = useState("");
  const [rate, setRate] = useState("");
  const [maturity, setMaturity] = useState("");
  const confirm = useConfirm();
  const { data: accounts } = useAccounts();

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
      if (accountId) body.account_id = Number(accountId);
      if (isRF && rateType) {
        if (!rate.trim()) return setMsg("Contrato exige a taxa.");
        body.rate_type = rateType;
        body.rate = rate.trim();
        if (maturity) body.maturity_date = maturity;
      }
      await m.create.mutateAsync(body);
      setTicker("");
      setAccountId("");
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
      {pf && (
        <section className="fw-card" style={{ marginBottom: 12 }}>
          <h2 style={{ marginTop: 0 }}>Resumo da carteira</h2>
          <p style={{ marginTop: 0 }}><small>Escopo global e atual: ignora os filtros de conta/período do Painel.</small></p>
          <div className="fw-metrics">
            <div className="fw-metric"><strong>Caixa nas corretoras</strong><p>{brl(pf.cash)}</p><small>dinheiro disponível para investir</small></div>
            <div className="fw-metric"><strong>Posições</strong><p>{brl(pf.positions_value)}</p><small>quantidade × preço atual</small></div>
            <div className="fw-metric"><strong>Total</strong><p>{brl(pf.total)}</p><small>caixa + posições</small></div>
            <div className="fw-metric">
              <strong>Resultado</strong><p>{brl(pf.resultado)}</p>
              <small title="Taxa interna de retorno anualizada dos aportes, resgates e rendimentos (reinvestimento é fluxo interno e não entra)">XIRR {pf.xirr != null ? `${(Number(pf.xirr) * 100).toFixed(2)}% a.a.` : "—"} ⓘ</small>
              <small title="Apreciação da cotação da carteira; exclui proventos reinvestidos"> · TWR de preço {pf.twr != null ? `${(Number(pf.twr) * 100).toFixed(2)}%` : "—"}</small>
            </div>
          </div>
          <p>Aportes {brl(pf.aportes)} · reinvestido {brl(pf.reinvestimentos)} · resgates {brl(pf.resgates)} · rendimentos {brl(pf.rendimentos)} · investido líquido {brl(pf.net_invested)}</p>
          {pf.unpriced.length > 0 && <p>Sem cotação: {pf.unpriced.join(", ")} — informe o preço manual no ativo.</p>}
          {pf.by_class.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <CategoryPie title="Por classe" items={pf.by_class.map((s) => ({ name: labelOf(assetClassLabel, s.name), total: s.total }))} />
            </div>
          )}
          <h3>Evolução {pf.history_since ? `(desde ${pf.history_since})` : ""}</h3>
          <SnapshotsLine snapshots={pf.snapshots} />
        </section>
      )}
      <form onSubmit={onCreate} className="fw-row" style={{ alignItems: "flex-end" }}>
        <Field label="Ticker">
          <input
            className="fw-input"
            style={{ width: "auto" }}
            placeholder="Ex.: PETR4"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
          />
        </Field>
        <Field label="Classe do ativo">
          <select
            className="fw-select"
            style={{ width: "auto" }}
            value={aclass}
            onChange={(e) => setAclass(e.target.value)}
          >
            {CLASSES.map((c) => (
              <option key={c} value={c}>
                {labelOf(assetClassLabel, c)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Subtipo">
          <input
            className="fw-input"
            style={{ width: "auto" }}
            aria-label="Subtipo do ativo"
            placeholder="Ex.: ACAO"
            value={subtype}
            onChange={(e) => setSubtype(e.target.value)}
          />
        </Field>
        <Field label="Conta da corretora">
          <select
            className="fw-select"
            style={{ width: "auto" }}
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
          >
            <option value="">Sem conta vinculada</option>
            {(accounts ?? []).filter((a) => a.account_type === "INVESTMENT").map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </Field>
        {isRF && (
          <>
            <Field label="Contrato" title={rateType ? rateTypeHelp[rateType] : undefined}>
              <select
                className="fw-select"
                style={{ width: "auto" }}
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
            </Field>
            {rateType && (
              <>
                <Field label={rateType === "CDI_PCT" ? "Percentual do CDI" : "Taxa anual (%)"}>
                  <input
                    className="fw-input"
                    style={{ width: "auto" }}
                    placeholder="Ex.: 110"
                    value={rate}
                    onChange={(e) => setRate(e.target.value)}
                  />
                </Field>
                <Field label="Vencimento do contrato">
                  <input
                    className="fw-input"
                    style={{ width: "auto" }}
                    type="date"
                    value={maturity}
                    onChange={(e) => setMaturity(e.target.value)}
                  />
                </Field>
              </>
            )}
          </>
        )}
        <Button>Criar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      {!isLoading && (data ?? []).length === 0 && (
        <p>Nenhum ativo ainda — crie o primeiro acima.</p>
      )}
      <h2>Ativos</h2>
      <ul className="fw-list">
        {(data ?? []).map((a) => (
          <li className="fw-list-item" key={a.id}>
            <span>
              {a.ticker} <Badge>{labelOf(assetClassLabel, a.asset_class)}</Badge>{" "}
              {a.account_id
                ? (accounts ?? []).find((c) => c.id === a.account_id)?.name ?? ""
                : <Badge tone="amber">sem conta vinculada</Badge>}
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
      <div className="fw-row" style={{ marginTop: 16, alignItems: "flex-end" }}>
        <Field label="Filtrar por classe">
          <select
            className="fw-select"
            style={{ width: "auto" }}
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
        </Field>
      </div>
    </>
  );
}
