import { brl } from "../../../lib/money";
import { labelOf, opKindLabel } from "../../../lib/labels";
import { Button, useConfirm } from "../../../components/ui";
import { useAssetMutations, useOps } from "../hooks";
import type { Asset } from "../../../lib/api";

type Props = {
  asset: Asset;
  onError: (msg: string) => void;
};

export function OpsHistory({ asset, onError }: Props) {
  const { data: ops } = useOps(asset.id);
  const m = useAssetMutations();
  const confirm = useConfirm();

  async function onDelOp(opId: number, kind: string) {
    onError("");
    const ok = await confirm.ask({
      title: "Excluir operação?",
      body: kind === "RENDIMENTO" ? "A operação e a receita espelhada no extrato serão removidas." : "A operação será removida e a posição recalculada.",
      confirmLabel: "Excluir operação",
    });
    if (!ok) return;
    try {
      await m.delOp.mutateAsync({ id: asset.id, opId });
    } catch {
      onError("Falha ao excluir operação.");
    }
  }

  return (
    <>
      {confirm.dialog}
      <h4>Histórico de operações ({(ops ?? []).length})</h4>
      {(ops ?? []).length === 0 && <p>Nenhuma operação lançada.</p>}
      <ul className="fw-list">
        {(ops ?? []).map((o) => (
          <li className="fw-list-item" key={o.id}>
            <span>
              {o.date} — {labelOf(opKindLabel, o.kind)} — {o.quantity != null ? `${o.quantity} un. × ` : ""}
              {o.price != null ? brl(o.price) : brl(o.amount)}
              {o.fees !== "0" && o.fees !== "0.00" ? ` (taxas ${brl(o.fees)})` : ""}
            </span>
            <Button size="sm" variant="danger" onClick={() => onDelOp(o.id, o.kind)}>
              Excluir
            </Button>
          </li>
        ))}
      </ul>
    </>
  );
}
