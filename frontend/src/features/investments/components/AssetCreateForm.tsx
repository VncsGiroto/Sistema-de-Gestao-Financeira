import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../../lib/api";
import type { AssetBody } from "../../../lib/api";
import { assetClassLabel, labelOf, rateTypeHelp, rateTypeLabel } from "../../../lib/labels";
import { Button, Field } from "../../../components/ui";
import { useAccounts } from "../../finance/hooks";
import { useAssetMutations } from "../hooks";

const CLASSES = ["RENDA_FIXA", "RENDA_VARIAVEL", "FUNDOS", "CRIPTO", "OUTROS"] as const;
const RATE_TYPES = ["CDI_PCT", "PREFIXADO", "IPCA_MAIS"] as const;

type Props = {
  onError: (msg: string) => void;
};

export function AssetCreateForm({ onError }: Props) {
  const m = useAssetMutations();
  const { data: accounts } = useAccounts();
  const [ticker, setTicker] = useState("");
  const [aclass, setAclass] = useState("RENDA_VARIAVEL");
  const [subtype, setSubtype] = useState("ACAO");
  const [accountId, setAccountId] = useState("");
  const [rateType, setRateType] = useState("");
  const [rate, setRate] = useState("");
  const [maturity, setMaturity] = useState("");
  const [taxRate, setTaxRate] = useState("");

  const isRF = aclass === "RENDA_FIXA";

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    onError("");
    if (!ticker.trim()) return onError("Informe o ticker.");
    try {
      const body: AssetBody = {
        ticker: ticker.trim(),
        asset_class: aclass,
        subtype,
      };
      if (accountId) body.account_id = Number(accountId);
      if (isRF && rateType) {
        if (!rate.trim()) return onError("Contrato exige a taxa.");
        body.rate_type = rateType;
        body.rate = rate.trim();
        if (maturity) body.maturity_date = maturity;
      }
      if (taxRate.trim()) {
        const t = Number(taxRate.trim().replace(",", "."));
        if (Number.isNaN(t) || t < 0 || t > 100) return onError("Alíquota deve estar entre 0 e 100.");
        body.tax_rate = taxRate.trim();
      }
      await m.create.mutateAsync(body);
      setTicker("");
      setAccountId("");
      setRateType("");
      setRate("");
      setMaturity("");
      setTaxRate("");
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao criar.");
    }
  }

  return (
    <form onSubmit={onCreate} className="fw-row" style={{ alignItems: "flex-end" }}>
      <Field label="Ticker">
        <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: PETR4" value={ticker} onChange={(e) => setTicker(e.target.value)} />
      </Field>
      <Field label="Classe do ativo">
        <select className="fw-select" style={{ width: "auto" }} value={aclass} onChange={(e) => setAclass(e.target.value)}>
          {CLASSES.map((c) => (
            <option key={c} value={c}>
              {labelOf(assetClassLabel, c)}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Subtipo">
        <input
          className="fw-input"
          style={{ width: "auto" }}
          aria-label="Subtipo do ativo"
          placeholder="Ex.: ACAO"
          value={subtype}
          onChange={(e) => setSubtype(e.target.value)}
        />
      </Field>
      <Field label="Conta da corretora">
        <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Sem conta vinculada</option>
          {(accounts ?? [])
            .filter((a) => a.account_type === "INVESTMENT")
            .map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
        </select>
      </Field>
      {isRF && (
        <>
          <Field label="Contrato" title={rateType ? rateTypeHelp[rateType] : undefined}>
            <select className="fw-select" style={{ width: "auto" }} value={rateType} onChange={(e) => setRateType(e.target.value)}>
              <option value="">Sem contrato (preço manual)</option>
              {RATE_TYPES.map((r) => (
                <option key={r} value={r}>
                  {labelOf(rateTypeLabel, r)}
                </option>
              ))}
            </select>
          </Field>
          {rateType && (
            <>
              <Field label={rateType === "CDI_PCT" ? "Percentual do CDI" : "Taxa anual (%)"}>
                <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: 110" value={rate} onChange={(e) => setRate(e.target.value)} />
              </Field>
              <Field label="Vencimento do contrato">
                <input className="fw-input" style={{ width: "auto" }} type="date" value={maturity} onChange={(e) => setMaturity(e.target.value)} />
              </Field>
            </>
          )}
        </>
      )}
      <Field
        label="Alíquota IR esperada (%)"
        title="Usada no líquido estimado do resgate total. Vazio = automática (RF regressiva pelo prazo, demais 15%)."
      >
        <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: 15" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} />
      </Field>
      <Button>Criar</Button>
    </form>
  );
}
