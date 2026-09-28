import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../lib/api";
import type { Payable, PayableBody } from "../../lib/api";
import { payableKindLabel, labelOf, periodicityLabel } from "../../lib/labels";
import { brl } from "../../lib/money";
import { Badge, Button, PageHeader } from "../../components/ui";
import { useAccounts, useCategories } from "../finance/hooks";
import { usePayableMutations, usePayableSchedule, usePayables } from "./hooks";

const KINDS = ["FIXED", "RECURRING", "INSTALLMENT", "ONE_TIME"] as const;
const PERIODS = ["MONTHLY", "WEEKLY", "YEARLY"] as const;

function kindTone(kind: string): "green" | "red" | "amber" | "blue" | "" {
  if (kind === "FIXED") return "blue";
  if (kind === "RECURRING") return "amber";
  if (kind === "INSTALLMENT") return "";
  return "green";
}

function PayBox({ p, onDone }: { p: Payable; onDone: (msg?: string) => void }) {
  const m = usePayableMutations();
  const { data: accounts } = useAccounts();
  const { data: sched } = usePayableSchedule(p.kind === "INSTALLMENT" ? p.id : null);
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [discount, setDiscount] = useState("");
  const [ns, setNs] = useState<number[]>([]);
  const [msg, setMsg] = useState("");

  const unpaid = (sched ?? []).filter((s) => !s.paid);

  function toggleN(n: number) {
    setNs((cur) => (cur.includes(n) ? cur.filter((x) => x !== n) : [...cur, n]));
  }

  async function submit(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!accountId) return setMsg("Selecione a conta.");
    try {
      const res = await m.pay.mutateAsync({
        id: p.id,
        body: {
          account_id: Number(accountId),
          ...(amount.trim() ? { amount: amount.trim() } : {}),
          ...(date ? { date } : {}),
          ...(p.kind === "INSTALLMENT"
            ? {
                ...(ns.length ? { ns } : {}),
                ...(discount.trim() ? { discount: discount.trim() } : {}),
              }
            : {}),
        },
      });
      onDone(`Baixado: ${res.transactions.length} lançamento(s).`);
      setNs([]); setDiscount(""); setAmount("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao baixar.");
    }
  }

  return (
    <form onSubmit={submit} className="fw-row" style={{ marginTop: 8 }}>
      <select className="fw-select" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
        <option value="">Conta...</option>
        {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
      </select>
      {(p.kind === "RECURRING" || p.kind === "ONE_TIME") && (
        <input className="fw-input" placeholder={`Valor (padrão ${p.amount})`} value={amount} onChange={(e) => setAmount(e.target.value)} />
      )}
      <input className="fw-input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      {p.kind === "INSTALLMENT" && (
        <>
          <span>
            {(sched ?? []).map((s) => (
              <label key={s.n} style={{ marginRight: 8 }}>
                <input type="checkbox" checked={ns.includes(s.n)} disabled={s.paid} onChange={() => toggleN(s.n)} />
                {s.n} ({brl(s.amount)}){s.paid ? " ✓" : ""}
              </label>
            ))}
            {unpaid.length === 0 && "Quitado"}
          </span>
          <input className="fw-input" placeholder="Desconto" value={discount} onChange={(e) => setDiscount(e.target.value)} style={{ width: 96 }} />
        </>
      )}
      <Button size="sm">Baixar</Button>
      {msg && <span className="fw-error">{msg}</span>}
    </form>
  );
}

export function PayablesPage() {
  const [kind, setKind] = useState("");
  const [onlyUpcoming, setOnlyUpcoming] = useState(false);
  const { data, isLoading } = usePayables(kind || undefined, onlyUpcoming ? 30 : undefined);
  const { data: categories } = useCategories("EXPENSE");
  const m = usePayableMutations();
  const [msg, setMsg] = useState("");
  const [payId, setPayId] = useState<number | null>(null);
  const [openSched, setOpenSched] = useState<number | null>(null);

  // form criar
  const [desc, setDesc] = useState("");
  const [ckind, setCkind] = useState<string>("FIXED");
  const [amount, setAmount] = useState("");
  const [periodicity, setPeriodicity] = useState("MONTHLY");
  const [dueDay, setDueDay] = useState("10");
  const [nextDue, setNextDue] = useState("");
  const [total, setTotal] = useState("");
  const [n, setN] = useState("12");
  const [firstDue, setFirstDue] = useState("");
  const [categoryId, setCategoryId] = useState("");

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (desc.trim().length < 2) return setMsg("Descrição mínima de 2 caracteres.");
    const body: PayableBody = { description: desc.trim(), kind: ckind };
    try {
      if (ckind === "ONE_TIME") {
        if (!amount.trim()) return setMsg("Informe o valor.");
        if (!nextDue) return setMsg("Informe o vencimento.");
        body.amount = amount.trim();
        body.next_due = nextDue;
      } else if (ckind === "INSTALLMENT") {
        if (!total.trim()) return setMsg("Informe o valor total.");
        const num = Number(n);
        if (!Number.isInteger(num) || num < 2 || num > 60) return setMsg("Parcelas entre 2 e 60.");
        if (!firstDue) return setMsg("Informe o primeiro vencimento.");
        body.total_amount = total.trim();
        body.num_installments = num;
        body.first_due_date = firstDue;
      } else {
        if (!amount.trim()) return setMsg("Informe o valor.");
        if (!dueDay) return setMsg("Informe o dia.");
        body.amount = amount.trim();
        body.periodicity = periodicity;
        body.due_day = Number(dueDay);
      }
      if (categoryId) body.category_id = Number(categoryId);
      await m.create.mutateAsync(body);
      setDesc(""); setAmount(""); setTotal(""); setNextDue(""); setFirstDue("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <>
      <PageHeader title="Contas a pagar" sub="Fixas, recorrentes, parceladas e únicas — com baixa em movimentações." />
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row">
        <input className="fw-input" placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <select className="fw-select" value={ckind} onChange={(e) => setCkind(e.target.value)}>
          {KINDS.map((k) => <option key={k} value={k}>{labelOf(payableKindLabel, k)}</option>)}
        </select>
        {(ckind === "FIXED" || ckind === "RECURRING") && (
          <>
            <input className="fw-input" placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <select className="fw-select" value={periodicity} onChange={(e) => setPeriodicity(e.target.value)}>
              {PERIODS.map((p) => <option key={p} value={p}>{labelOf(periodicityLabel, p)}</option>)}
            </select>
            <input className="fw-input" placeholder="Dia" value={dueDay} onChange={(e) => setDueDay(e.target.value)} style={{ width: 64 }} />
          </>
        )}
        {ckind === "ONE_TIME" && (
          <>
            <input className="fw-input" placeholder="Valor" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <input className="fw-input" type="date" value={nextDue} onChange={(e) => setNextDue(e.target.value)} />
          </>
        )}
        {ckind === "INSTALLMENT" && (
          <>
            <input className="fw-input" placeholder="Valor total" value={total} onChange={(e) => setTotal(e.target.value)} />
            <input className="fw-input" placeholder="Nº" value={n} onChange={(e) => setN(e.target.value)} style={{ width: 64 }} />
            <input className="fw-input" type="date" value={firstDue} onChange={(e) => setFirstDue(e.target.value)} />
          </>
        )}
        <select className="fw-select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Categoria...</option>
          {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <Button>Criar</Button>
        <select className="fw-select" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">Todas</option>
          {KINDS.map((k) => <option key={k} value={k}>{labelOf(payableKindLabel, k)}</option>)}
        </select>
        <label><input type="checkbox" checked={onlyUpcoming} onChange={(e) => setOnlyUpcoming(e.target.checked)} /> Próximas 30d</label>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul className="fw-list">
        {(data ?? []).map((p) => {
          const paid = (p.kind === "ONE_TIME" && !!p.paid_at) ||
            (p.kind === "INSTALLMENT" && p.num_installments != null && (p.paid_ns ?? []).length >= p.num_installments);
          return (
            <li className="fw-list-item" key={p.id}>
              <span>
                {p.description} <Badge tone={kindTone(p.kind)}>{labelOf(payableKindLabel, p.kind)}</Badge>{" "}
                {p.amount ? brl(p.amount) : ""}
                {p.total_amount ? ` ${brl(p.total_amount)} em ${p.num_installments}x` : ""}
                {p.next_due ? ` · vence ${p.next_due}` : ""}{" "}
                <Badge tone={paid ? "green" : "amber"}>{paid ? "Paga" : "Em aberto"}</Badge>
              </span>
              <span>
                <Button size="sm" onClick={() => setPayId(payId === p.id ? null : p.id)}>Pagar</Button>{" "}
                {p.kind === "INSTALLMENT" && (
                  <Button size="sm" variant="ghost" onClick={() => setOpenSched(openSched === p.id ? null : p.id)}>Parcelas</Button>
                )}{" "}
                <Button size="sm" variant="danger" onClick={() => m.remove.mutateAsync(p.id)}>Excluir</Button>
              </span>
              {payId === p.id && <PayBox p={p} onDone={(m) => { setPayId(null); if (m) setMsg(m); }} />}
              {openSched === p.id && <SchedTable id={p.id} />}
            </li>
          );
        })}
      </ul>
    </>
  );
}

function SchedTable({ id }: { id: number }) {
  const { data } = usePayableSchedule(id);
  return (
    <table className="fw-table">
      <thead><tr><th>Nº</th><th>Vencimento</th><th>Valor</th><th>Paga</th></tr></thead>
      <tbody>
        {(data ?? []).map((s) => (
          <tr key={s.n}>
            <td>{s.n}</td>
            <td>{s.due_date}</td>
            <td>{brl(s.amount)}</td>
            <td>{s.paid ? <Badge tone="green">Paga</Badge> : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
