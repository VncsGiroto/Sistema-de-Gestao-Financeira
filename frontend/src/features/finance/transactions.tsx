import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api";
import type { TxFilters } from "../../lib/api";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";
import { useAccounts, useCategories, useTxMutations, useTxs } from "./hooks";
import { Button, Field, PageHeader, useConfirm } from "../../components/ui";
import { labelOf, txSourceLabel, txTypeLabel } from "../../lib/labels";
import { todayISO } from "../../lib/date";

export function TransactionsPage() {
  const { access, refresh } = useAuth();
  const [f, setF] = useState<TxFilters>(() => {
    const q = new URLSearchParams(window.location.search).get("account_id");
    const account_id = q && /^\d+$/.test(q) ? Number(q) : undefined;
    return { page: 1, per_page: 20, account_id };
  });
  const { data, isLoading } = useTxs(f);
  const m = useTxMutations();
  const { data: accounts } = useAccounts();
  const { data: categories } = useCategories();
  const [msg, setMsg] = useState("");
  const confirm = useConfirm();

  async function onDelete(id: number, description: string, source: string) {
    setMsg("");
    const origin = source === "PAYABLE"
      ? "Ela foi gerada pela baixa de uma conta a pagar — excluí-la não reabre a conta."
      : source === "OFX" || source === "IMPORT"
        ? "Ela veio de uma importação de extrato."
        : "Ela é um lançamento manual.";
    const ok = await confirm.ask({
      title: "Excluir lançamento?",
      body: `“${description}” será excluído do extrato. ${origin}`,
      confirmLabel: "Excluir lançamento",
    });
    if (!ok) return;
    try {
      await m.remove.mutateAsync(id);
    } catch {
      setMsg("Falha ao excluir.");
    }
  }

  // form criar
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
      const { from, to, account_id, category_id, type: t, source, min, max, q } = f;
      await api.downloadCsv({ from, to, account_id, category_id, type: t, source, min, max, q }, access, refresh);
    } catch {
      setMsg("Falha ao exportar.");
    }
  }

  const set = (k: keyof TxFilters, v: string | number | undefined) =>
    setF((p) => ({ ...p, [k]: v === "" ? undefined : v, page: 1 }));

  return (
    <>
      <PageHeader title="Movimentações" sub="Receitas e despesas manuais." />
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
            <select className="fw-select" style={{ width: "auto" }} value={f.type ?? ""} onChange={(e) => set("type", e.target.value || undefined)}>
              <option value="">Tipo...</option>
              <option value="EXPENSE">Despesa</option>
              <option value="INCOME">Receita</option>
            </select>
          </Field>
          <Field label="Categoria">
            <select className="fw-select" style={{ width: "auto" }} value={f.category_id ?? ""} onChange={(e) => set("category_id", e.target.value ? Number(e.target.value) : undefined)}>
              <option value="">Todas as categorias</option>
              {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name} ({labelOf(txTypeLabel, c.type)})</option>)}
            </select>
          </Field>
          <Field label="Origem">
            <select className="fw-select" style={{ width: "auto" }} value={f.source ?? ""} onChange={(e) => set("source", e.target.value || undefined)}>
              <option value="">Todas as origens</option>
              {Object.entries(txSourceLabel).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>
          <Field label="Valor mín. (R$)">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={f.min ?? ""} onChange={(e) => set("min", e.target.value || undefined)} />
          </Field>
          <Field label="Valor máx. (R$)">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={f.max ?? ""} onChange={(e) => set("max", e.target.value || undefined)} />
          </Field>
          <Field label="Busca">
            <input className="fw-input" style={{ width: "auto" }} placeholder="Descrição..." value={f.q ?? ""} onChange={(e) => set("q", e.target.value || undefined)} />
          </Field>
          <Button variant="ghost" onClick={onExport}>Exportar CSV</Button>
        </div>
      </details>

      {isLoading && <p>Carregando...</p>}
      <table className="fw-table">
        <thead><tr><th>Data</th><th>Descrição</th><th>Valor</th><th>Tipo</th><th>Categoria</th><th></th></tr></thead>
        <tbody>
          {(data?.data ?? []).map((t) => (
            <tr key={t.id}>
              <td>{t.date}</td>
              <td>{t.description}</td>
              <td>R$ {t.amount}</td>
              <td>{labelOf(txTypeLabel, t.type)}</td>
              <td>
                <select className="fw-select" value={t.category_id ?? ""} onChange={(e) => onInlineCategory(t.id, e.target.value)}>
                  <option value="">—</option>
                  {(categories ?? []).filter((c) => c.type === t.type).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </td>
              <td><Button size="sm" variant="danger" onClick={() => onDelete(t.id, t.description, t.source)}>Excluir</Button></td>
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
