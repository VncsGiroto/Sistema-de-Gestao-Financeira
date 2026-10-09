import type { Payable } from "../../../lib/api";
import { labelOf, payableKindHelp, payableKindLabel, periodicityLabel } from "../../../lib/labels";
import { brl } from "../../../lib/money";
import { useAccounts, useCategories } from "../../finance/hooks";
import { usePayableHistory } from "../hooks";
import { SchedTable } from "./SchedTable";

export function DetailPanel({ p }: { p: Payable }) {
  const { data: hist } = usePayableHistory(p.id);
  const { data: accounts } = useAccounts();
  const { data: categories } = useCategories();
  const accName = (accounts ?? []).find((a) => a.id === p.account_id)?.name;
  const catName = (categories ?? []).find((c) => c.id === p.category_id)?.name;
  return (
    <div className="fw-card" style={{ marginTop: 8, width: "100%" }}>
      <p style={{ marginTop: 0 }}>
        {labelOf(payableKindLabel, p.kind)} — {payableKindHelp[p.kind] ?? ""}
      </p>
      <p>
        {p.amount ? <>Valor {brl(p.amount)} · </> : null}
        {p.total_amount ? <>Total {brl(p.total_amount)} em {p.num_installments}x · </> : null}
        {p.periodicity ? <>Periodicidade {labelOf(periodicityLabel, p.periodicity)} · </> : null}
        {p.due_day ? <>Dia {p.due_day} · </> : null}
        {p.next_due ? <>Vence {p.next_due} · </> : null}
        {p.first_due_date ? <>1ª parcela {p.first_due_date} · </> : null}
        {accName ? <>Conta {accName} · </> : null}
        {catName ? <>Categoria {catName}</> : null}
      </p>
      <h4>Histórico de baixas ({hist?.meta.total ?? 0})</h4>
      {(hist == null || hist.data.length === 0) && <p>Nenhuma baixa lançada.</p>}
      {(hist?.data ?? []).length > 0 && (
        <ul className="fw-list">
          {(hist?.data ?? []).map((t) => (
            <li className="fw-list-item" key={t.id}>
              {t.date} — {t.description} — {brl(t.amount)}
            </li>
          ))}
        </ul>
      )}
      {p.kind === "INSTALLMENT" && <SchedTable id={p.id} />}
    </div>
  );
}
