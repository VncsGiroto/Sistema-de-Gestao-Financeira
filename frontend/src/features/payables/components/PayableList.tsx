import type { Payable } from "../../../lib/api";
import { PayableListItem } from "./PayableListItem";

type Props = {
  data: Payable[] | undefined;
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

export function PayableList(props: Props) {
  if (!props.data || props.data.length === 0) return null;
  return (
    <ul className="fw-list">
      {props.data.map((p) => (
        <PayableListItem key={p.id} p={p} {...props} />
      ))}
    </ul>
  );
}
