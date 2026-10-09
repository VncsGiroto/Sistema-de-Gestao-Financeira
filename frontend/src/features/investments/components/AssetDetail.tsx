import { useState } from "react";
import type { Asset } from "../../../lib/api";
import { usePosition, useReturns } from "../hooks";
import { PositionCard } from "./PositionCard";
import { ReturnsCard } from "./ReturnsCard";
import { OperationForm } from "./OperationForm";
import { ManualPriceForm } from "./ManualPriceForm";
import { TaxRateForm } from "./TaxRateForm";
import { OpsHistory } from "./OpsHistory";
import { isContracted } from "../lib/validation";

export function AssetDetail({ asset }: { asset: Asset }) {
  const { data: pos, refetch: refetchPos } = usePosition(asset.id);
  const { data: ret, refetch: refetchRet } = useReturns(asset.id);
  const [msg, setMsg] = useState("");

  const contracted = isContracted(asset);

  function onSuccess() {
    refetchPos();
    refetchRet();
  }

  return (
    <div>
      {pos && <PositionCard pos={pos} contracted={contracted} />}
      {!pos && <p>Lance um aporte abaixo para começar — a posição aparece aqui.</p>}
      <ReturnsCard ret={ret} />
      <OperationForm asset={asset} pos={pos} onSuccess={onSuccess} onError={setMsg} />
      <ManualPriceForm asset={asset} pos={pos} onSuccess={onSuccess} onError={setMsg} />
      <TaxRateForm asset={asset} pos={pos} onSuccess={onSuccess} onError={setMsg} />
      <OpsHistory asset={asset} onError={setMsg} />
      {msg && <p className="fw-error">{msg}</p>}
    </div>
  );
}
