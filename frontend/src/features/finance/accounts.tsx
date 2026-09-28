import { useState } from "react";
import type { FormEvent } from "react";
import { useAccountMutations, useAccounts } from "./hooks";
import { ApiError } from "../../lib/api";
import { Button, PageHeader } from "../../components/ui";
import { accountTypeLabel, labelOf } from "../../lib/labels";

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
    <>
      <PageHeader title="Contas" sub="Gerencie suas contas e saldos iniciais." />
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} placeholder="Banco" value={bank} onChange={(e) => setBank(e.target.value)} />
        <select className="fw-select" style={{ width: "auto" }} value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => <option key={t} value={t}>{labelOf(accountTypeLabel, t)}</option>)}
        </select>
        <input className="fw-input" style={{ width: "auto" }} placeholder="Saldo inicial" value={balance} onChange={(e) => setBalance(e.target.value)} />
        <Button type="submit">Criar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      {error && <p className="fw-error">Falha ao carregar.</p>}
      <ul className="fw-list">
        {(data ?? []).map((a) => (
          <li className="fw-list-item" key={a.id}>
            {editing === a.id ? (
              <>
                <input className="fw-input" style={{ width: "auto" }} value={editName} onChange={(e) => setEditName(e.target.value)} />
                <Button size="sm" onClick={() => onRename(a.id)}>Salvar</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancelar</Button>
              </>
            ) : (
              <>
                <span><strong>{a.name}</strong> ({labelOf(accountTypeLabel, a.account_type)}) — R$ {a.initial_balance}</span>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(a.id); setEditName(a.name); }}>Renomear</Button>
                <Button size="sm" variant="danger" onClick={() => onDelete(a.id)}>Excluir</Button>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
