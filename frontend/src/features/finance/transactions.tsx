import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api-client";
import type { TxFilters } from "../../lib/api-client";
import { ApiError } from "../../lib/api-client";
import { useAuth } from "../../lib/auth-store";
import { useAccounts, useCategories, useTxMutations, useTxs } from "./hooks";

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
    <main style={{ fontFamily: "system-ui", padding: 32 }}>
      <h1>Movimentações</h1>
      {msg && <p style={{ color: "crimson" }}>{msg}</p>}

      <form onSubmit={onCreate} style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Conta...</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Sem categoria</option>
          {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name} ({c.type})</option>)}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <input placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <input placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <button>Adicionar</button>
      </form>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <input type="date" value={f.from ?? ""} onChange={(e) => set("from", e.target.value || undefined)} />
        <input type="date" value={f.to ?? ""} onChange={(e) => set("to", e.target.value || undefined)} />
        <select value={f.type ?? ""} onChange={(e) => set("type", e.target.value || undefined)}>
          <option value="">Tipo...</option>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <input placeholder="Buscar..." value={f.q ?? ""} onChange={(e) => set("q", e.target.value || undefined)} />
        <button onClick={onExport}>Exportar CSV</button>
      </div>

      {isLoading && <p>Carregando...</p>}
      <table>
        <thead><tr><th>Data</th><th>Descrição</th><th>Valor</th><th>Tipo</th><th>Categoria</th><th></th></tr></thead>
        <tbody>
          {(data?.data ?? []).map((t) => (
            <tr key={t.id}>
              <td>{t.date}</td>
              <td>{t.description}</td>
              <td>{t.amount}</td>
              <td>{t.type}</td>
              <td>
                <select value={t.category_id ?? ""} onChange={(e) => onInlineCategory(t.id, e.target.value)}>
                  <option value="">—</option>
                  {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </td>
              <td><button onClick={() => m.remove.mutateAsync(t.id)}>Excluir</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Total: {data?.meta.total ?? 0} — página {data?.meta.page ?? 1}</p>
      <button disabled={(f.page ?? 1) <= 1} onClick={() => setF((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}>Anterior</button>
      <button onClick={() => setF((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}>Próxima</button>
    </main>
  );
}
