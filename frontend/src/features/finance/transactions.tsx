import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api";
import type { TxFilters } from "../../lib/api";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-store";
import { useAccounts, useCategories, useTxMutations, useTxs } from "./hooks";
import { Button, PageHeader, useConfirm } from "../../components/ui";
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

      <form onSubmit={onCreate} className="fw-row">
        <select className="fw-select" style={{ width: "auto" }} aria-label="Conta do lançamento" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Conta...</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select className="fw-select" style={{ width: "auto" }} aria-label="Categoria do lançamento" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Sem categoria</option>
          {(categories ?? []).filter((c) => c.type === type).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input className="fw-input" style={{ width: "auto" }} aria-label="Data do lançamento" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} aria-label="Descrição" placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} aria-label="Valor em R$" placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <select className="fw-select" style={{ width: "auto" }} aria-label="Tipo do lançamento" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <Button type="submit">Adicionar</Button>
      </form>

      <div className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} aria-label="Filtrar de" type="date" value={f.from ?? ""} onChange={(e) => set("from", e.target.value || undefined)} />
        <input className="fw-input" style={{ width: "auto" }} aria-label="Filtrar até" type="date" value={f.to ?? ""} onChange={(e) => set("to", e.target.value || undefined)} />
        <select className="fw-select" style={{ width: "auto" }} aria-label="Filtrar por conta" value={f.account_id ?? ""} onChange={(e) => set("account_id", e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">Todas as contas</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select className="fw-select" style={{ width: "auto" }} aria-label="Filtrar por tipo" value={f.type ?? ""} onChange={(e) => set("type", e.target.value || undefined)}>
          <option value="">Tipo...</option>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <select className="fw-select" style={{ width: "auto" }} aria-label="Filtrar por categoria" value={f.category_id ?? ""} onChange={(e) => set("category_id", e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">Todas as categorias</option>
          {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name} ({labelOf(txTypeLabel, c.type)})</option>)}
        </select>
        <select className="fw-select" style={{ width: "auto" }} aria-label="Filtrar por origem" value={f.source ?? ""} onChange={(e) => set("source", e.target.value || undefined)}>
          <option value="">Todas as origens</option>
          {Object.entries(txSourceLabel).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input className="fw-input" style={{ width: "auto" }} aria-label="Valor mínimo em R$" placeholder="Valor mín." value={f.min ?? ""} onChange={(e) => set("min", e.target.value || undefined)} />
        <input className="fw-input" style={{ width: "auto" }} aria-label="Valor máximo em R$" placeholder="Valor máx." value={f.max ?? ""} onChange={(e) => set("max", e.target.value || undefined)} />
        <input className="fw-input" style={{ width: "auto" }} aria-label="Buscar na descrição" placeholder="Buscar..." value={f.q ?? ""} onChange={(e) => set("q", e.target.value || undefined)} />
        <Button variant="ghost" onClick={onExport}>Exportar CSV</Button>
      </div>

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
