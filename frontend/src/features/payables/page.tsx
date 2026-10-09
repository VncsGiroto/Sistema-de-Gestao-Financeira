import { useState } from "react";
import { labelOf, payableKindLabel } from "../../lib/labels";
import { Field, PageHeader } from "../../components/ui";
import { usePayables } from "./hooks";
import { PayableCreateForm } from "./components/PayableCreateForm";
import { PayableList } from "./components/PayableList";

const KINDS = ["FIXED", "RECURRING", "INSTALLMENT", "ONE_TIME"] as const;

export function PayablesPage() {
  const [kind, setKind] = useState("");
  const [onlyUpcoming, setOnlyUpcoming] = useState(false);
  const { data, isLoading } = usePayables(kind || undefined, onlyUpcoming ? 30 : undefined);
  const [msg, setMsg] = useState("");
  const [payId, setPayId] = useState<number | null>(null);
  const [openSched, setOpenSched] = useState<number | null>(null);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDesc, setEditDesc] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editNextDue, setEditNextDue] = useState("");

  return (
    <>
      <PageHeader title="Contas a pagar" sub="Fixas, recorrentes, parceladas e únicas — com baixa em movimentações." />
      {msg && <p className="fw-error">{msg}</p>}
      <PayableCreateForm onError={setMsg} />
      {isLoading && <p>Carregando...</p>}
      <PayableList
        data={data}
        payId={payId}
        openSched={openSched}
        detailId={detailId}
        editingId={editingId}
        onTogglePay={(id) => setPayId(payId === id ? null : id)}
        onToggleSched={(id) => setOpenSched(openSched === id ? null : id)}
        onToggleDetail={(id) => setDetailId(detailId === id ? null : id)}
        onToggleEdit={(id) => {
          if (editingId === id) {
            setEditingId(null);
          } else {
            const p = (data ?? []).find((x) => x.id === id);
            if (p) {
              setEditingId(p.id);
              setEditDesc(p.description);
              setEditAmount(p.amount ?? "");
              setEditNextDue(p.next_due ?? "");
            }
          }
        }}
        onDonePay={(m) => {
          setPayId(null);
          if (m) setMsg(m);
        }}
        onError={setMsg}
        editDesc={editDesc}
        editAmount={editAmount}
        editNextDue={editNextDue}
        setEditDesc={setEditDesc}
        setEditAmount={setEditAmount}
        setEditNextDue={setEditNextDue}
        setEditingId={setEditingId}
      />
      <div className="fw-row" style={{ marginTop: 16, alignItems: "flex-end" }}>
        <Field label="Filtrar por tipo">
          <select className="fw-select" style={{ width: "auto" }} value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">Todas</option>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {labelOf(payableKindLabel, k)}
              </option>
            ))}
          </select>
        </Field>
        <label>
          <input type="checkbox" checked={onlyUpcoming} onChange={(e) => setOnlyUpcoming(e.target.checked)} /> Próximas 30d
        </label>
      </div>
    </>
  );
}
