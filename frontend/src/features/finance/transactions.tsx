import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api-client";
import type { TxFilters } from "../../lib/api-client";
import { ApiError } from "../../lib/api-client";
import { useAuth } from "../../lib/auth-store";
import { useAccounts, useCategories, useTxMutations, useTxs } from "./hooks";
import { Button, PageHeader } from "../../components/ui";
import { labelOf, txTypeLabel } from "../../lib/labels";

export function TransactionsPage() {
  const { access, refresh } = useAuth();
  const [f, setF] = useState<TxFilters>({ page: 1, per_page: 20 });
  const { data, isLoading } = useTxs(f);
  const m = useTxMutations();
  const { data: accounts } = useAccounts();
  const { data: categories } = useCategories();
  const [msg, setMsg] = useState("");

  // form criar
  const [accountId, setAccountId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [date, setDate] = useState("2026-09-22");
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
      const { from, to, account_id, category_id, type: t, q } = f;
      await api.downloadCsv({ from, to, account_id, category_id, type: t, q }, access, refresh);
    } catch {
      setMsg("Falha ao exportar.");
    }
  }

  const set = (k: keyof TxFilters, v: string | number | undefined) =>
    setF((p) => ({ ...p, [k]: v === "" ? undefined : v, page: 1 }));

  return (
    <>
      <PageHeader title="Movimentações" sub="Receitas e despesas manuais." />
      {msg && <p className="fw-error">{msg}</p>}

      <form onSubmit={onCreate} className="fw-row">
        <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Conta...</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select className="fw-select" style={{ width: "auto" }} value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Sem categoria</option>
          {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name} ({labelOf(txTypeLabel, c.type)})</option>)}
        </select>
        <input className="fw-input" style={{ width: "auto" }} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <select className="fw-select" style={{ width: "auto" }} value={type} onChange={(e) => setType(e.target.value)}>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <Button type="submit">Adicionar</Button>
      </form>

      <div className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} type="date" value={f.from ?? ""} onChange={(e) => set("from", e.target.value || undefined)} />
        <input className="fw-input" style={{ width: "auto" }} type="date" value={f.to ?? ""} onChange={(e) => set("to", e.target.value || undefined)} />
        <select className="fw-select" style={{ width: "auto" }} value={f.type ?? ""} onChange={(e) => set("type", e.target.value || undefined)}>
          <option value="">Tipo...</option>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <input className="fw-input" style={{ width: "auto" }} placeholder="Buscar..." value={f.q ?? ""} onChange={(e) => set("q", e.target.value || undefined)} />
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
                  {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </td>
              <td><Button size="sm" variant="danger" onClick={() => m.remove.mutateAsync(t.id)}>Excluir</Button></td>
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
