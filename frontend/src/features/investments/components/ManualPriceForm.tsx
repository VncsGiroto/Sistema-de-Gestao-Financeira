import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../../lib/api";
import type { Asset } from "../../../lib/api";
import { todayISO } from "../../../lib/date";
import { Button, Field } from "../../../components/ui";
import { useAssetMutations } from "../hooks";
import { isContracted } from "../lib/validation";
import type { Position } from "../../../lib/api";

type Props = {
  asset: Asset;
  pos: Position | undefined;
  onSuccess: () => void;
  onError: (msg: string) => void;
};

export function ManualPriceForm({ asset, pos, onSuccess, onError }: Props) {
  const m = useAssetMutations();
  const [mdate, setMdate] = useState(todayISO);
  const [mprice, setMprice] = useState("");

  const contracted = isContracted(asset);
  const shouldShow = !contracted || (pos != null && pos.current_price == null);
  if (!shouldShow) return null;

  async function onPrice(ev: FormEvent, override = false) {
    ev.preventDefault();
    onError("");
    if (!mprice.trim()) return onError("Informe o preço.");
    try {
      await m.setPrice.mutateAsync({
        id: asset.id,
        date: mdate,
        price: mprice.trim(),
        ...(override ? { override: true } : {}),
      });
      setMprice("");
      onSuccess();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao precificar.");
    }
  }

  return (
    <form onSubmit={(e) => onPrice(e, contracted)} className="fw-row" style={{ alignItems: "flex-end" }}>
      {contracted && <span>Contrato sem cotação — preço manual como exceção explícita.</span>}
      <Field label="Data de referência">
        <input className="fw-input" style={{ width: "auto" }} type="date" value={mdate} onChange={(e) => setMdate(e.target.value)} />
      </Field>
      <Field label={contracted ? "Preço de exceção (R$)" : "Preço manual (R$)"}>
        <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={mprice} onChange={(e) => setMprice(e.target.value)} />
      </Field>
      <Button size="sm" variant="ghost">
        Precificar
      </Button>
    </form>
  );
}
