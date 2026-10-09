import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../../lib/api";
import type { PayableBody } from "../../../lib/api";
import { labelOf, payableKindLabel, periodicityLabel } from "../../../lib/labels";
import { Button, Field } from "../../../components/ui";
import { useCategories } from "../../finance/hooks";
import { usePayableMutations } from "../hooks";

const KINDS = ["FIXED", "RECURRING", "INSTALLMENT", "ONE_TIME"] as const;
const PERIODS = ["MONTHLY", "WEEKLY", "YEARLY"] as const;

type Props = {
  onError: (msg: string) => void;
};

export function PayableCreateForm({ onError }: Props) {
  const m = usePayableMutations();
  const { data: categories } = useCategories("EXPENSE");
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
    onError("");
    if (desc.trim().length < 2) return onError("Descrição mínima de 2 caracteres.");
    const body: PayableBody = { description: desc.trim(), kind: ckind };
    try {
      if (ckind === "ONE_TIME") {
        if (!amount.trim()) return onError("Informe o valor.");
        if (!nextDue) return onError("Informe o vencimento.");
        body.amount = amount.trim();
        body.next_due = nextDue;
      } else if (ckind === "INSTALLMENT") {
        if (!total.trim()) return onError("Informe o valor total.");
        const num = Number(n);
        if (!Number.isInteger(num) || num < 2 || num > 60) return onError("Parcelas entre 2 e 60.");
        if (!firstDue) return onError("Informe o primeiro vencimento.");
        body.total_amount = total.trim();
        body.num_installments = num;
        body.first_due_date = firstDue;
      } else {
        if (!amount.trim()) return onError("Informe o valor.");
        if (!dueDay) return onError("Informe o dia.");
        body.amount = amount.trim();
        body.periodicity = periodicity;
        body.due_day = Number(dueDay);
      }
      if (categoryId) body.category_id = Number(categoryId);
      await m.create.mutateAsync(body);
      setDesc("");
      setAmount("");
      setTotal("");
      setNextDue("");
      setFirstDue("");
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <form onSubmit={onCreate} className="fw-row" style={{ alignItems: "flex-end" }}>
      <Field label="Descrição">
        <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: Internet" value={desc} onChange={(e) => setDesc(e.target.value)} />
      </Field>
      <Field label="Tipo de conta">
        <select className="fw-select" style={{ width: "auto" }} value={ckind} onChange={(e) => setCkind(e.target.value)}>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {labelOf(payableKindLabel, k)}
            </option>
          ))}
        </select>
      </Field>
      {(ckind === "FIXED" || ckind === "RECURRING") && (
        <>
          <Field label="Valor mensal (R$)">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
          <Field label="Periodicidade">
            <select className="fw-select" style={{ width: "auto" }} value={periodicity} onChange={(e) => setPeriodicity(e.target.value)}>
              {PERIODS.map((p) => (
                <option key={p} value={p}>
                  {labelOf(periodicityLabel, p)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Dia do vencimento">
            <input className="fw-input" style={{ width: 64 }} placeholder="10" value={dueDay} onChange={(e) => setDueDay(e.target.value)} />
          </Field>
        </>
      )}
      {ckind === "ONE_TIME" && (
        <>
          <Field label="Valor (R$)">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
          <Field label="Vencimento">
            <input className="fw-input" style={{ width: "auto" }} type="date" value={nextDue} onChange={(e) => setNextDue(e.target.value)} />
          </Field>
        </>
      )}
      {ckind === "INSTALLMENT" && (
        <>
          <Field label="Valor total (R$)">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={total} onChange={(e) => setTotal(e.target.value)} />
          </Field>
          <Field label="Parcelas">
            <input className="fw-input" style={{ width: 64 }} placeholder="12" value={n} onChange={(e) => setN(e.target.value)} />
          </Field>
          <Field label="Primeiro vencimento">
            <input className="fw-input" style={{ width: "auto" }} type="date" value={firstDue} onChange={(e) => setFirstDue(e.target.value)} />
          </Field>
        </>
      )}
      <Field label="Categoria (despesa)">
        <select className="fw-select" style={{ width: "auto" }} value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Categoria...</option>
          {(categories ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Button>Criar</Button>
    </form>
  );
}
