import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../lib/api-client";
import type { BillBody } from "../../lib/api-client";
import { useBillMutations, useBills } from "./hooks";
import { Button, PageHeader } from "../../components/ui";
import { billKindLabel, labelOf, periodicityLabel } from "../../lib/labels";

const KINDS = ["FIXED", "VARIABLE", "RECURRING", "ONE_TIME"] as const;
const PERIODS = ["MONTHLY", "WEEKLY", "YEARLY"] as const;

export function BillsPage() {
  const [onlyUpcoming, setOnlyUpcoming] = useState(false);
  const { data, isLoading } = useBills(onlyUpcoming ? 30 : undefined);
  const m = useBillMutations();
  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState("");
  const [kind, setKind] = useState<string>("FIXED");
  const [periodicity, setPeriodicity] = useState<string>("MONTHLY");
  const [dueDay, setDueDay] = useState("10");
  const [nextDue, setNextDue] = useState("");
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editAmount, setEditAmount] = useState("");

  const oneTime = kind === "ONE_TIME";

  async function onSaveAmount(id: number) {
    setMsg("");
    try {
      await m.patch.mutateAsync({ id, body: { amount: editAmount.trim() } });
      setEditing(null);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao salvar valor.");
    }
  }

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (desc.trim().length < 2) return setMsg("Descrição mínima de 2 caracteres.");
    if (!amount.trim()) return setMsg("Informe o valor.");
    const body: BillBody = { description: desc.trim(), amount: amount.trim(), kind };
    if (oneTime) {
      if (!nextDue) return setMsg("Conta única exige a data de vencimento.");
      body.next_due = nextDue;
    } else {
      if (!dueDay) return setMsg("Informe o dia do vencimento.");
      body.periodicity = periodicity;
      body.due_day = Number(dueDay);
    }
    try {
      await m.create.mutateAsync(body);
      setDesc(""); setAmount(""); setNextDue("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <>
      <PageHeader title="Contas futuras" sub="Despesas que se repetem todo ciclo (fixas ou variáveis com vencimento) ou vencem uma única vez." />
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <select className="fw-select" style={{ width: "auto" }} value={kind} onChange={(e) => setKind(e.target.value)}>
          {KINDS.map((k) => <option key={k} value={k}>{labelOf(billKindLabel, k)}</option>)}
        </select>
        {oneTime ? (
          <input className="fw-input" style={{ width: "auto" }} type="date" value={nextDue} onChange={(e) => setNextDue(e.target.value)} />
        ) : (
          <>
            <select className="fw-select" style={{ width: "auto" }} value={periodicity} onChange={(e) => setPeriodicity(e.target.value)}>
              {PERIODS.map((p) => <option key={p} value={p}>{labelOf(periodicityLabel, p)}</option>)}
            </select>
            <input className="fw-input" placeholder="Dia" value={dueDay} onChange={(e) => setDueDay(e.target.value)} style={{ width: 64 }} />
          </>
        )}
        <Button type="submit">Criar</Button>
        <label><input type="checkbox" checked={onlyUpcoming} onChange={(e) => setOnlyUpcoming(e.target.checked)} /> Próximas 30d</label>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul className="fw-list">
        {(data ?? []).map((b) => (
          <li className="fw-list-item" key={b.id}>
            <span>{b.description} — R$ {b.amount} ({labelOf(billKindLabel, b.kind)}
            {b.periodicity ? `/${labelOf(periodicityLabel, b.periodicity)}` : ""}) — vence {b.next_due ?? "—"}</span>
            {editing === b.id ? (
              <>
                <input className="fw-input" style={{ width: 110 }} placeholder="Novo valor" value={editAmount} onChange={(e) => setEditAmount(e.target.value)} />
                <Button size="sm" onClick={() => onSaveAmount(b.id)}>Salvar</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancelar</Button>
              </>
            ) : (
              <>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(b.id); setEditAmount(b.amount); }}>Editar valor</Button>
                <Button size="sm" variant="danger" onClick={() => m.remove.mutateAsync(b.id)}>Excluir</Button>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
