import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../../lib/api";
import type { Payable } from "../../../lib/api";
import { brl } from "../../../lib/money";
import { Button, useConfirm } from "../../../components/ui";
import { useAccounts } from "../../finance/hooks";
import { usePayableMutations, usePayableSchedule } from "../hooks";
import { grossOf, parseDiscount, targetsForInstallment, unpaidItems } from "../lib/utils";

export function PayBox({ p, onDone }: { p: Payable; onDone: (msg?: string) => void }) {
  const m = usePayableMutations();
  const { data: accounts } = useAccounts();
  const { data: sched } = usePayableSchedule(p.kind === "INSTALLMENT" ? p.id : null);
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [discount, setDiscount] = useState("");
  const [ns, setNs] = useState<number[]>([]);
  const [msg, setMsg] = useState("");
  const confirm = useConfirm();

  const unpaid = unpaidItems(sched);

  function toggleN(n: number) {
    setNs((cur) => (cur.includes(n) ? cur.filter((x) => x !== n) : [...cur, n]));
  }

  const targets = p.kind === "INSTALLMENT" ? targetsForInstallment(unpaid, ns) : [];
  const gross = grossOf(targets);
  const discountNum = parseDiscount(discount);
  const accName = (accounts ?? []).find((a) => String(a.id) === accountId)?.name;

  async function submit(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!accountId) return setMsg("Selecione a conta.");
    const value = p.kind === "INSTALLMENT" ? (ns.length ? `${ns.length} parcela(s)` : "a próxima parcela") : `R$ ${amount.trim() || p.amount}`;
    const detail =
      p.kind === "INSTALLMENT" && targets.length
        ? ` Original ${brl(String(gross))} − desconto ${brl(String(discountNum))} = ${brl(String(gross - discountNum))} em ${targets.length} lançamento(s).`
        : "";
    const ok = await confirm.ask({
      title: "Confirmar baixa?",
      body: `“${p.description}” (${value}) será lançada como despesa em ${accName ?? "conta"}.${detail}`,
      confirmLabel: "Baixar",
    });
    if (!ok) return;
    try {
      const res = await m.pay.mutateAsync({
        id: p.id,
        body: {
          account_id: Number(accountId),
          ...(amount.trim() ? { amount: amount.trim() } : {}),
          ...(date ? { date } : {}),
          ...(p.kind === "INSTALLMENT" ? { ...(ns.length ? { ns } : {}), ...(discount.trim() ? { discount: discount.trim() } : {}) } : {}),
        },
      });
      onDone(`Baixado: ${res.transactions.length} lançamento(s).`);
      setNs([]);
      setDiscount("");
      setAmount("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao baixar.");
    }
  }

  return (
    <form onSubmit={submit} className="fw-row" style={{ marginTop: 8 }}>
      {confirm.dialog}
      <select className="fw-select" aria-label="Conta da baixa" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
        <option value="">Conta...</option>
        {(accounts ?? []).map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      {(p.kind === "RECURRING" || p.kind === "ONE_TIME") && (
        <input
          className="fw-input"
          aria-label="Valor da baixa em R$"
          placeholder={`Valor (padrão ${p.amount})`}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      )}
      <input className="fw-input" aria-label="Data do pagamento" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
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
          <input
            className="fw-input"
            aria-label="Desconto em R$ rateado entre as parcelas"
            placeholder="Desconto"
            value={discount}
            onChange={(e) => setDiscount(e.target.value)}
            style={{ width: 96 }}
          />
        </>
      )}
      <Button size="sm">Baixar</Button>
      {p.kind === "INSTALLMENT" && targets.length > 0 && (
        <span>
          Resumo: original {brl(String(gross))} − desconto {brl(String(discountNum))} = {brl(String(gross - discountNum))} em {targets.length} lançamento(s).
        </span>
      )}
      {msg && <span className="fw-error">{msg}</span>}
    </form>
  );
}
