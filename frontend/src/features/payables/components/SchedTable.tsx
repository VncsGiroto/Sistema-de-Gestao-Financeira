import { brl } from "../../../lib/money";
import { Badge } from "../../../components/ui";
import { usePayableSchedule } from "../hooks";

export function SchedTable({ id }: { id: number }) {
  const { data } = usePayableSchedule(id);
  return (
    <table className="fw-table">
      <thead>
        <tr>
          <th>Nº</th>
          <th>Vencimento</th>
          <th>Valor</th>
          <th>Paga</th>
        </tr>
      </thead>
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
