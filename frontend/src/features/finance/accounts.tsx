import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "@tanstack/react-router";
import { useAccountMutations, useAccounts } from "./hooks";
import { ApiError } from "../../lib/api";
import { Button, PageHeader, useConfirm } from "../../components/ui";
import { accountTypeLabel, labelOf } from "../../lib/labels";

const TYPES = ["CHECKING", "SAVINGS", "CASH", "INVESTMENT", "OTHER"] as const;

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

  const confirm = useConfirm();

  async function onDelete(id: number, name: string) {
    setMsg("");
    const ok = await confirm.ask({
      title: "Excluir conta?",
      body: `“${name}” será excluída. O histórico de movimentações dela será perdido. Contas com movimentações são bloqueadas.`,
      confirmLabel: "Excluir conta",
    });
    if (!ok) return;
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
      {confirm.dialog}
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} aria-label="Nome da conta" placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} aria-label="Banco" placeholder="Banco" value={bank} onChange={(e) => setBank(e.target.value)} />
        <select className="fw-select" style={{ width: "auto" }} aria-label="Tipo de conta" value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => <option key={t} value={t}>{labelOf(accountTypeLabel, t)}</option>)}
        </select>
        <input className="fw-input" style={{ width: "auto" }} aria-label="Saldo inicial em R$" placeholder="Saldo inicial" value={balance} onChange={(e) => setBalance(e.target.value)} />
        <Button type="submit">Criar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      {error && <p className="fw-error">Falha ao carregar.</p>}
      <ul className="fw-list">
        {(data ?? []).map((a) => (
          <li className="fw-list-item" key={a.id}>
            {editing === a.id ? (
              <>
                <input className="fw-input" style={{ width: "auto" }} aria-label="Novo nome da conta" value={editName} onChange={(e) => setEditName(e.target.value)} />
                <Button size="sm" onClick={() => onRename(a.id)}>Salvar</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancelar</Button>
              </>
            ) : (
              <>
                <span>
                  <strong>{a.name}</strong> ({labelOf(accountTypeLabel, a.account_type)}) — Atual R$ {a.current_balance}
                  {" "}(Inicial R$ {a.initial_balance} · +R$ {a.total_income} / −R$ {a.total_expense}
                  {a.last_transaction_date ? ` · últ. mov. ${a.last_transaction_date}` : ""})
                  {" "}<Link to="/app/transactions" search={{ account_id: a.id }}>ver movimentações</Link>
                </span>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(a.id); setEditName(a.name); }}>Renomear</Button>
                <Button size="sm" variant="danger" onClick={() => onDelete(a.id, a.name)}>Excluir</Button>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
