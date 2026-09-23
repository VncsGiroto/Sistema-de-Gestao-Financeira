import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../lib/api-client";
import { useAccounts } from "../finance/hooks";
import { useInstallmentMutations, useInstallments, useSchedule } from "./hooks";
import { Button, PageHeader } from "../../components/ui";

export function InstallmentsPage() {
  const { data, isLoading } = useInstallments();
  const { data: accounts } = useAccounts();
  const m = useInstallmentMutations();
  const [desc, setDesc] = useState("");
  const [total, setTotal] = useState("");
  const [n, setN] = useState("12");
  const [firstDue, setFirstDue] = useState("2026-10-10");
  const [accountId, setAccountId] = useState("");
  const [msg, setMsg] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const { data: sched } = useSchedule(openId);

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (desc.trim().length < 2) return setMsg("Descrição mínima de 2 caracteres.");
    if (!total.trim()) return setMsg("Informe o valor total.");
    const num = Number(n);
    if (!Number.isInteger(num) || num < 2 || num > 60) return setMsg("Parcelas entre 2 e 60.");
    if (!firstDue) return setMsg("Informe o primeiro vencimento.");
    try {
      await m.create.mutateAsync({
        description: desc.trim(), total_amount: total.trim(), num_installments: num,
        first_due_date: firstDue, account_id: accountId ? Number(accountId) : undefined,
      });
      setDesc(""); setTotal("");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <>
      <PageHeader title="Parcelamentos" sub="Uma compra dividida em parcelas mensais, com cronograma de vencimentos." />
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <input className="fw-input" style={{ width: "auto" }} placeholder="Valor total" value={total} onChange={(e) => setTotal(e.target.value)} />
        <input className="fw-input" placeholder="Nº parcelas" value={n} onChange={(e) => setN(e.target.value)} style={{ width: 110 }} />
        <input className="fw-input" style={{ width: "auto" }} type="date" value={firstDue} onChange={(e) => setFirstDue(e.target.value)} />
        <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Sem conta</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <Button type="submit">Criar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul className="fw-list">
        {(data ?? []).map((p) => (
          <li className="fw-list-item" key={p.id}>
            <span>{p.description} — R$ {p.total_amount} em {p.num_installments}x de ~R$ {p.installment_amount} (1º {p.first_due_date})</span>
            <Button size="sm" variant="ghost" onClick={() => setOpenId(openId === p.id ? null : p.id)}>
              {openId === p.id ? "Ocultar" : "Ver parcelas"}
            </Button>
            <Button size="sm" variant="danger" onClick={() => m.remove.mutateAsync(p.id)}>Excluir</Button>
            {openId === p.id && (
              <table className="fw-table">
                <thead><tr><th>Nº</th><th>Vencimento</th><th>Valor</th></tr></thead>
                <tbody>
                  {(sched ?? []).map((s) => (
                    <tr key={s.n}><td>{s.n}</td><td>{s.due_date}</td><td>R$ {s.amount}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
