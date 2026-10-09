import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "@tanstack/react-router";
import { useAccountMutations, useAccounts } from "./hooks";
import { ApiError } from "../../lib/api";
import { todayISO } from "../../lib/date";
import { Button, Field, PageHeader, useConfirm } from "../../components/ui";
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
  const [transferId, setTransferId] = useState<number | null>(null);
  const [transferTo, setTransferTo] = useState("");
  const [transferAmount, setTransferAmount] = useState("");
  const [transferDate, setTransferDate] = useState(todayISO);

  async function onTransfer(fromId: number, fromName: string) {
    setMsg("");
    if (!transferTo) return setMsg("Selecione a conta de destino.");
    if (!transferAmount.trim()) return setMsg("Informe o valor.");
    if (!transferDate) return setMsg("Informe a data.");
    const toName = (data ?? []).find((a) => String(a.id) === transferTo)?.name ?? "conta";
    const dateBR = transferDate.split("-").reverse().join("/");
    const ok = await confirm.ask({
      title: "Confirmar transferência?",
      body: `R$ ${transferAmount.trim()} de “${fromName}” para “${toName}” em ${dateBR}. Não entra em receitas nem despesas.`,
      confirmLabel: "Transferir",
    });
    if (!ok) return;
    try {
      await m.transfer.mutateAsync({ from_account_id: fromId, to_account_id: Number(transferTo), amount: transferAmount.trim(), date: transferDate });
      setTransferId(null); setTransferTo(""); setTransferAmount(""); setTransferDate(todayISO());
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao transferir.");
    }
  }

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
      <form onSubmit={onCreate} className="fw-row" style={{ alignItems: "flex-end" }}>
        <Field label="Nome da conta">
          <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: Nubank" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Banco">
          <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: Nu Pagamentos" value={bank} onChange={(e) => setBank(e.target.value)} />
        </Field>
        <Field label="Tipo de conta">
          <select className="fw-select" style={{ width: "auto" }} value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map((t) => <option key={t} value={t}>{labelOf(accountTypeLabel, t)}</option>)}
          </select>
        </Field>
        <Field label="Saldo inicial">
          <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={balance} onChange={(e) => setBalance(e.target.value)} />
        </Field>
        <Button type="submit">Criar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      {error && <p className="fw-error">Falha ao carregar.</p>}
      <ul className="fw-list">
        {(data ?? []).map((a) => (
          <li className="fw-list-item" key={a.id}>
            {editing === a.id ? (
              <>
                <Field label="Novo nome">
                  <input className="fw-input" style={{ width: "auto" }} value={editName} onChange={(e) => setEditName(e.target.value)} />
                </Field>
                <Button size="sm" onClick={() => onRename(a.id)}>Salvar</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancelar</Button>
              </>
            ) : (
              <>
                <span>
                  <strong>{a.name}</strong> ({labelOf(accountTypeLabel, a.account_type)})
                  <br />
                  <span className="fw-sub">
                    Atual R$ {a.current_balance} · inicial R$ {a.initial_balance} · +R$ {a.total_income} / −R$ {a.total_expense}
                    {a.last_transaction_date ? ` · últ. mov. ${a.last_transaction_date}` : ""}
                  </span>
                  {" "}<Link to="/app/transactions" search={{ account_id: a.id }}>ver movimentações</Link>
                </span>
                <Button size="sm" variant="ghost" onClick={() => { setTransferId(transferId === a.id ? null : a.id); setTransferTo(""); setTransferAmount(""); setTransferDate(todayISO()); }}>Transferir</Button>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(a.id); setEditName(a.name); }}>Renomear</Button>
                <Button size="sm" variant="danger" onClick={() => onDelete(a.id, a.name)}>Excluir</Button>
                {transferId === a.id && (
                  <form onSubmit={(e) => { e.preventDefault(); onTransfer(a.id, a.name); }} className="fw-row" style={{ marginTop: 8, alignItems: "flex-end", width: "100%" }}>
                    <Field label="Destino">
                      <select className="fw-select" style={{ width: "auto" }} value={transferTo} onChange={(e) => setTransferTo(e.target.value)}>
                        <option value="">Destino...</option>
                        {(data ?? []).filter((o) => o.id !== a.id).map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                      </select>
                    </Field>
                    <Field label="Valor (R$)">
                      <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={transferAmount} onChange={(e) => setTransferAmount(e.target.value)} />
                    </Field>
                    <Field label="Data">
                      <input className="fw-input" style={{ width: "auto" }} type="date" value={transferDate} onChange={(e) => setTransferDate(e.target.value)} />
                    </Field>
                    <Button size="sm" type="submit">Enviar</Button>
                  </form>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
