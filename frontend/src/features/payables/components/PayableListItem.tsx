import { ApiError } from "../../../lib/api";
import type { Payable, PayableBody } from "../../../lib/api";
import { labelOf, payableKindLabel } from "../../../lib/labels";
import { brl } from "../../../lib/money";
import { Badge, Button, Field, useConfirm } from "../../../components/ui";
import { usePayableMutations } from "../hooks";
import { isPaid, kindTone } from "../lib/utils";
import { PayBox } from "./PayBox";
import { DetailPanel } from "./DetailPanel";
import { SchedTable } from "./SchedTable";

type Props = {
  p: Payable;
  payId: number | null;
  openSched: number | null;
  detailId: number | null;
  editingId: number | null;
  onTogglePay: (id: number) => void;
  onToggleSched: (id: number) => void;
  onToggleDetail: (id: number) => void;
  onToggleEdit: (id: number) => void;
  onDonePay: (msg?: string) => void;
  onError: (msg: string) => void;
  editDesc: string;
  editAmount: string;
  editNextDue: string;
  setEditDesc: (v: string) => void;
  setEditAmount: (v: string) => void;
  setEditNextDue: (v: string) => void;
  setEditingId: (v: number | null) => void;
};

export function PayableListItem({
  p,
  payId,
  openSched,
  detailId,
  editingId,
  onTogglePay,
  onToggleSched,
  onToggleDetail,
  onToggleEdit,
  onDonePay,
  onError,
  editDesc,
  editAmount,
  editNextDue,
  setEditDesc,
  setEditAmount,
  setEditNextDue,
  setEditingId,
}: Props) {
  const m = usePayableMutations();
  const confirm = useConfirm();
  const paid = isPaid(p);

  async function onSaveEdit() {
    onError("");
    try {
      const body: Partial<PayableBody> = {};
      if (editDesc.trim() && editDesc.trim() !== p.description) body.description = editDesc.trim();
      if (p.kind !== "INSTALLMENT" && editAmount.trim()) body.amount = editAmount.trim();
      if (p.kind === "ONE_TIME" && editNextDue) body.next_due = editNextDue;
      if (Object.keys(body).length === 0) {
        setEditingId(null);
        return;
      }
      await m.patch.mutateAsync({ id: p.id, body });
      setEditingId(null);
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao salvar.");
    }
  }

  async function onDelete() {
    onError("");
    const ok = await confirm.ask({
      title: "Excluir conta a pagar?",
      body: `“${p.description}” será excluída. Contas com baixas lançadas são bloqueadas — exclua os lançamentos no extrato antes.`,
      confirmLabel: "Excluir",
    });
    if (!ok) return;
    try {
      await m.remove.mutateAsync(p.id);
    } catch (e) {
      onError(e instanceof ApiError && e.status === 409 ? "Conta possui baixas lançadas e não pode ser excluída." : "Falha ao excluir.");
    }
  }

  return (
    <li className="fw-list-item" key={p.id}>
      {confirm.dialog}
      <span>
        {p.description} <Badge tone={kindTone(p.kind)}>{labelOf(payableKindLabel, p.kind)}</Badge> {p.amount ? brl(p.amount) : ""}
        {p.total_amount ? ` ${brl(p.total_amount)} em ${p.num_installments}x` : ""}
        {p.next_due ? ` · vence ${p.next_due}` : ""} <Badge tone={paid ? "green" : "amber"}>{paid ? "Paga" : "Em aberto"}</Badge>
      </span>
      <span>
        <Button size="sm" variant="ghost" onClick={() => onToggleDetail(p.id)}>
          Detalhar
        </Button>{" "}
        <Button size="sm" onClick={() => onTogglePay(p.id)}>
          Pagar
        </Button>{" "}
        <Button size="sm" variant="ghost" onClick={() => onToggleEdit(p.id)}>
          Editar
        </Button>{" "}
        {p.kind === "INSTALLMENT" && (
          <Button size="sm" variant="ghost" onClick={() => onToggleSched(p.id)}>
            Parcelas
          </Button>
        )}{" "}
        <Button size="sm" variant="danger" onClick={onDelete}>
          Excluir
        </Button>
      </span>
      {payId === p.id && <PayBox p={p} onDone={onDonePay} />}
      {detailId === p.id && <DetailPanel p={p} />}
      {editingId === p.id && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSaveEdit();
          }}
          className="fw-row"
          style={{ marginTop: 8, alignItems: "flex-end", width: "100%" }}
        >
          <Field label="Descrição">
            <input className="fw-input" style={{ width: "auto" }} placeholder="Descrição" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
          </Field>
          {p.kind !== "INSTALLMENT" && (
            <Field label="Valor (R$)">
              <input
                className="fw-input"
                style={{ width: "auto" }}
                placeholder="0,00"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
              />
            </Field>
          )}
          {p.kind === "ONE_TIME" && (
            <Field label="Vencimento">
              <input className="fw-input" style={{ width: "auto" }} type="date" value={editNextDue} onChange={(e) => setEditNextDue(e.target.value)} />
            </Field>
          )}
          <Button size="sm" type="submit">
            Salvar
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
            Cancelar
          </Button>
        </form>
      )}
      {openSched === p.id && <SchedTable id={p.id} />}
    </li>
  );
}
