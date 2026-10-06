import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api";
import type { MovementFilters, MovementItem } from "../../lib/api";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";
import { useAccountMutations, useAccounts, useCategories, useMovements, useTxMutations } from "./hooks";
import { Button, Field, PageHeader, useConfirm } from "../../components/ui";
import { labelOf, movementDirectionLabel, movementKindLabel } from "../../lib/labels";
import { todayISO } from "../../lib/date";

const KINDS = ["INCOME", "EXPENSE", "TRANSFER", "APORTE", "RESGATE", "RENDIMENTO", "REINVESTIMENTO"] as const;

function sides(m: MovementItem, names: Map<number, string>): string {
  if (m.kind === "TRANSFER") {
    const from = m.from_account_id ? names.get(m.from_account_id) ?? `#${m.from_account_id}` : "?";
    const to = m.to_account_id ? names.get(m.to_account_id) ?? `#${m.to_account_id}` : "?";
    return `${from} → ${to}`;
  }
  if (m.account_id) return names.get(m.account_id) ?? `#${m.account_id}`;
  return m.ticker ? `Ativo ${m.ticker}` : "—";
}

export function TransactionsPage() {
  const { access, refresh } = useAuth();
  const [f, setF] = useState<MovementFilters>(() => {
    const q = new URLSearchParams(window.location.search).get("account_id");
    const account_id = q && /^\d+$/.test(q) ? Number(q) : undefined;
    return { page: 1, per_page: 20, account_id };
  });
  const { data, isLoading } = useMovements(f);
  const m = useTxMutations();
  const ma = useAccountMutations();
  const { data: accounts } = useAccounts();
  const { data: categories } = useCategories();
  const [msg, setMsg] = useState("");
  const confirm = useConfirm();
  const names = new Map((accounts ?? []).map((a) => [a.id, a.name]));

  async function onDelete(mv: MovementItem) {
    setMsg("");
    if (mv.origin === "operation") {
      setMsg("Gerado por operação de investimento — gerencie pelo ativo em Investimentos.");
      return;
    }
    const ok = await confirm.ask({
      title: mv.origin === "transfer" ? "Reverter transferência?" : "Excluir lançamento?",
      body: mv.origin === "transfer"
        ? `“${mv.description}” será revertida dos dois lados.`
        : `“${mv.description}” será excluído do extrato.`,
      confirmLabel: mv.origin === "transfer" ? "Reverter" : "Excluir lançamento",
    });
    if (!ok) return;
    try {
      if (mv.origin === "transfer" && mv.movement_id) await ma.removeTransfer.mutateAsync(mv.movement_id);
      else if (mv.transaction_id) await m.remove.mutateAsync(mv.transaction_id);
    } catch {
      setMsg("Falha ao excluir.");
    }
  }

  // form criar (lançamento manual de receita/despesa)
  const [accountId, setAccountId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [date, setDate] = useState(todayISO);
  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState("");
  const [type, setType] = useState("EXPENSE");

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    try {
      await m.create.mutateAsync({
        account_id: Number(accountId), category_id: categoryId ? Number(categoryId) : null,
        date, description: desc.trim(), amount: amount.trim(), type,
      });
      setDesc(""); setAmount("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  async function onInlineCategory(txId: number, value: string) {
    setMsg("");
    try {
      await m.patch.mutateAsync({ id: txId, body: { category_id: value ? Number(value) : null } });
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao alterar categoria.");
    }
  }

  async function onExport() {
    setMsg("");
    try {
      if (!access) return;
      const { from, to, account_id, kind } = f;
      await api.downloadMovementsCsv({ from, to, account_id, kind }, access, refresh);
    } catch {
      setMsg("Falha ao exportar.");
    }
  }

  const set = (k: keyof MovementFilters, v: string | number | undefined) =>
    setF((p) => ({ ...p, [k]: v === "" ? undefined : v, page: 1 }));

  return (
    <>
      <PageHeader title="Movimentações" sub="Receitas, despesas, transferências e operações de investimento — uma linha por evento." />
      {confirm.dialog}
      {msg && <p className="fw-error">{msg}</p>}

      <form onSubmit={onCreate} className="fw-row" style={{ alignItems: "flex-end" }}>
        <Field label="Conta">
          <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">Conta...</option>
            {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </Field>
        <Field label="Tipo">
          <select className="fw-select" style={{ width: "auto" }} value={type} onChange={(e) => { setType(e.target.value); setCategoryId(""); }}>
            <option value="EXPENSE">Despesa</option>
            <option value="INCOME">Receita</option>
          </select>
        </Field>
        <Field label="Categoria">
          <select className="fw-select" style={{ width: "auto" }} value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">Sem categoria</option>
            {(categories ?? []).filter((c) => c.type === type).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Descrição">
          <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: Supermercado" value={desc} onChange={(e) => setDesc(e.target.value)} />
        </Field>
        <Field label="Data">
          <input className="fw-input" style={{ width: "auto" }} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
        <Field label="Valor (R$)">
          <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
        <Button type="submit">Adicionar</Button>
      </form>

      <details className="fw-filters">
        <summary>Filtros</summary>
        <div className="fw-row" style={{ marginTop: 8, alignItems: "flex-end" }}>
          <Field label="De">
            <input className="fw-input" style={{ width: "auto" }} type="date" value={f.from ?? ""} onChange={(e) => set("from", e.target.value || undefined)} />
          </Field>
          <Field label="Até">
            <input className="fw-input" style={{ width: "auto" }} type="date" value={f.to ?? ""} onChange={(e) => set("to", e.target.value || undefined)} />
          </Field>
          <Field label="Conta">
            <select className="fw-select" style={{ width: "auto" }} value={f.account_id ?? ""} onChange={(e) => set("account_id", e.target.value ? Number(e.target.value) : undefined)}>
              <option value="">Todas as contas</option>
              {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </Field>
          <Field label="Tipo">
            <select className="fw-select" style={{ width: "auto" }} value={f.kind ?? ""} onChange={(e) => set("kind", e.target.value || undefined)}>
              <option value="">Todos os tipos</option>
              {KINDS.map((k) => <option key={k} value={k}>{labelOf(movementKindLabel, k)}</option>)}
            </select>
          </Field>
          <Button variant="ghost" onClick={onExport}>Exportar CSV</Button>
        </div>
      </details>

      {isLoading && <p>Carregando...</p>}
      <table className="fw-table">
        <thead><tr><th>Data</th><th>Descrição</th><th>Valor</th><th>Tipo</th><th>Efeito no caixa</th><th>Conta</th><th></th></tr></thead>
        <tbody>
          {(data?.data ?? []).map((mv) => (
            <tr key={mv.id}>
              <td>{mv.date}</td>
              <td>{mv.description}{mv.ticker ? ` (${mv.ticker})` : ""}</td>
              <td>R$ {mv.amount}</td>
              <td>{labelOf(movementKindLabel, mv.kind)}</td>
              <td title={mv.origin_hint}>{labelOf(movementDirectionLabel, mv.direction)}</td>
              <td>{sides(mv, names)}</td>
              <td>
                {mv.origin === "transaction" && mv.transaction_id && (mv.kind === "INCOME" || mv.kind === "EXPENSE") ? (
                  <select className="fw-select" value={mv.category_id ?? ""} onChange={(e) => onInlineCategory(mv.transaction_id!, e.target.value)}>
                    <option value="">—</option>
                    {(categories ?? []).filter((c) => c.type === mv.kind).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                ) : null}
                {mv.origin === "operation" ? (
                  <small title={mv.origin_hint}>via operação</small>
                ) : (
                  <Button size="sm" variant="danger" onClick={() => onDelete(mv)}>
                    {mv.origin === "transfer" ? "Reverter" : "Excluir"}
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Total: {data?.meta.total ?? 0} — página {data?.meta.page ?? 1}</p>
      <div className="fw-row">
        <Button variant="ghost" disabled={(f.page ?? 1) <= 1} onClick={() => setF((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}>Anterior</Button>
        <Button variant="ghost" onClick={() => setF((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}>Próxima</Button>
      </div>
    </>
  );
}
