import { useState } from "react";
import type { FormEvent } from "react";
import { useAccountMutations, useAccounts } from "./hooks";
import { ApiError } from "../../lib/api-client";

const TYPES = ["CHECKING", "SAVINGS", "CREDIT_CARD", "CASH", "OTHER"] as const;

export function AccountsPage() {
  const { data, isLoading, error } = useAccounts();
  const m = useAccountMutations();
  const [name, setName] = useState("");
  const [bank, setBank] = useState("");
  const [type, setType] = useState<string>("CHECKING");
  const [balance, setBalance] = useState("");
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (name.trim().length < 2) return setMsg("Nome mínimo de 2 caracteres.");
    try {
      await m.create.mutateAsync({
        name: name.trim(), bank: bank.trim() || undefined,
        account_type: type, initial_balance: balance.trim() || undefined,
      });
      setName(""); setBank(""); setBalance("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  async function onDelete(id: number) {
    setMsg("");
    try {
      await m.remove.mutateAsync(id);
    } catch (e) {
      setMsg(e instanceof ApiError && e.status === 409
        ? "Conta possui movimentações e não pode ser excluída."
        : "Falha ao excluir.");
    }
  }

  async function onRename(id: number) {
    setMsg("");
    try {
      await m.patch.mutateAsync({ id, body: { name: editName.trim() } });
      setEditing(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao renomear.");
    }
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: 32, maxWidth: 720 }}>
      <h1>Contas</h1>
      {msg && <p style={{ color: "crimson" }}>{msg}</p>}
      <form onSubmit={onCreate} style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="Banco" value={bank} onChange={(e) => setBank(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input placeholder="Saldo inicial" value={balance} onChange={(e) => setBalance(e.target.value)} />
        <button>Criar</button>
      </form>
      {isLoading && <p>Carregando...</p>}
      {error && <p style={{ color: "crimson" }}>Falha ao carregar.</p>}
      <ul>
        {(data ?? []).map((a) => (
          <li key={a.id}>
            {editing === a.id ? (
              <>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} />
                <button onClick={() => onRename(a.id)}>Salvar</button>
                <button onClick={() => setEditing(null)}>Cancelar</button>
              </>
            ) : (
              <>
                {a.name} ({a.account_type}) — R$ {a.initial_balance}
                <button onClick={() => { setEditing(a.id); setEditName(a.name); }}>Renomear</button>
                <button onClick={() => onDelete(a.id)}>Excluir</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
