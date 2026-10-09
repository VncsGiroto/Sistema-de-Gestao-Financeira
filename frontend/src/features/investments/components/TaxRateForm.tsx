import type { FormEvent } from "react";
import { ApiError } from "../../../lib/api";
import type { Asset, AssetBody } from "../../../lib/api";
import { Button, Field } from "../../../components/ui";
import { useAssetMutations } from "../hooks";
import { parseNum } from "../lib/validation";
import type { Position } from "../../../lib/api";

type Props = {
  asset: Asset;
  pos: Position | undefined;
  onSuccess: () => void;
  onError: (msg: string) => void;
};

export function TaxRateForm({ asset, pos, onSuccess, onError }: Props) {
  const m = useAssetMutations();

  async function onTaxRate(ev: FormEvent) {
    ev.preventDefault();
    onError("");
    const v = String(new FormData(ev.currentTarget as HTMLFormElement).get("taxrate") ?? "").trim();
    if (v && (Number.isNaN(parseNum(v)) || parseNum(v) < 0 || parseNum(v) > 100)) return onError("Alíquota deve estar entre 0 e 100.");
    try {
      await m.patch.mutateAsync({ id: asset.id, body: { tax_rate: v ? v : null } as Partial<AssetBody> });
      onSuccess();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao salvar alíquota.");
    }
  }

  return (
    <form onSubmit={onTaxRate} className="fw-row" style={{ alignItems: "flex-end" }}>
      <Field label="Alíquota IR esperada (%)" title="Usada no líquido estimado do resgate total. Vazio = automática (RF regressiva pelo prazo, demais 15%).">
        <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: 15" name="taxrate" defaultValue={asset.tax_rate ?? ""} />
      </Field>
      <Button size="sm" variant="ghost">
        Salvar alíquota
      </Button>
      {pos?.net_rate != null && (
        <span className="fw-sub">
          em uso: {pos.net_rate}% ({pos.net_rate_source === "manual" ? "informada" : "automática"})
        </span>
      )}
    </form>
  );
}
