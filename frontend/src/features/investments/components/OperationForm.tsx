import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../../lib/api";
import type { Asset } from "../../../lib/api";
import { opKindHelp } from "../../../lib/labels";
import { brl } from "../../../lib/money";
import { todayISO } from "../../../lib/date";
import { Button, Field, useConfirm } from "../../../components/ui";
import { useAccounts } from "../../finance/hooks";
import { useAssetMutations } from "../hooks";
import { isContracted, parseNum } from "../lib/validation";
import { rescuePreview } from "../lib/formatters";
import type { Position } from "../../../lib/api";

type Props = {
  asset: Asset;
  pos: Position | undefined;
  onSuccess: () => void;
  onError: (msg: string) => void;
};

export function OperationForm({ asset, pos, onSuccess, onError }: Props) {
  const { data: accounts } = useAccounts();
  const m = useAssetMutations();
  const confirm = useConfirm();
  const [kind, setKind] = useState("APORTE");
  const [date, setDate] = useState(todayISO);
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [amount, setAmount] = useState("");
  const [fees, setFees] = useState("");
  const [accountId, setAccountId] = useState("");
  const [showFull, setShowFull] = useState(false);
  const [fullDate, setFullDate] = useState(todayISO);
  const [fullFees, setFullFees] = useState("");

  const contracted = isContracted(asset);
  const isRendimento = kind === "RENDIMENTO";
  const isRescue = kind === "RESGATE";

  async function onOp(ev: FormEvent) {
    ev.preventDefault();
    onError("");
    if (contracted && (kind === "APORTE" || kind === "RESGATE" || kind === "REINVESTIMENTO") && !amount.trim())
      return onError("Informe o valor em reais.");
    if (!isRendimento && !contracted && (!qty.trim() || !price.trim())) return onError("Aporte/resgate exige quantidade e preço.");
    if (isRendimento && !amount.trim()) return onError("Rendimento exige valor.");
    if (isRendimento && !accountId) return onError("Rendimento exige a conta de destino.");
    if (isRescue && fees.trim() && (Number.isNaN(parseNum(fees)) || parseNum(fees) < 0)) return onError("IR/taxas inválido.");
    try {
      await m.addOp.mutateAsync({
        id: asset.id,
        body: {
          kind,
          date,
          ...(!isRendimento && !contracted ? { quantity: qty.trim(), price: price.trim() } : {}),
          ...(isRendimento || contracted ? { amount: amount.trim() } : {}),
          ...(isRescue && fees.trim() ? { fees: fees.trim() } : {}),
          ...(isRendimento ? { account_id: Number(accountId) } : {}),
        },
      });
      setQty("");
      setPrice("");
      setAmount("");
      setFees("");
      onSuccess();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao lançar.");
    }
  }

  const partialPreview = isRescue
    ? rescuePreview(contracted ? (amount.trim() ? parseNum(amount) : null) : qty.trim() && price.trim() ? parseNum(qty) * parseNum(price) : null, fees, parseNum)
    : null;

  async function onFullRescue(ev: FormEvent) {
    ev.preventDefault();
    onError("");
    if (!fullDate) return onError("Informe a data.");
    if (fullFees.trim() && (Number.isNaN(parseNum(fullFees)) || parseNum(fullFees) < 0)) return onError("IR inválido.");
    const gross = pos?.current_value != null ? Number(pos.current_value) : null;
    const ir = fullFees.trim() ? parseNum(fullFees) : 0;
    const net = gross != null && !Number.isNaN(gross) ? gross - ir : null;
    const dateBR = fullDate.split("-").reverse().join("/");
    const ok = await confirm.ask({
      title: "Resgatar tudo?",
      body:
        `Toda a posição de ${asset.ticker} será liquidada em ${dateBR}` +
        (gross != null && !Number.isNaN(gross) ? ` por ~${brl(gross)} bruto` : " pelo valor atual do contrato") +
        (fullFees.trim() ? ` − IR ${brl(ir)} = líquido est. ${brl(net ?? 0)}` : "") +
        ". O IR é retido na fonte; o líquido cai na conta da corretora.",
      confirmLabel: "Resgatar tudo",
    });
    if (!ok) return;
    try {
      await m.addOp.mutateAsync({
        id: asset.id,
        body: { kind: "RESGATE", date: fullDate, full: true, ...(fullFees.trim() ? { fees: fullFees.trim() } : {}) },
      });
      setShowFull(false);
      setFullFees("");
      setFullDate(todayISO());
      onSuccess();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Falha ao resgatar.");
    }
  }

  return (
    <>
      {confirm.dialog}
      <form onSubmit={onOp} className="fw-row" style={{ alignItems: "flex-end" }}>
        <Field label="Operação" title={opKindHelp[kind]}>
          <select className="fw-select" style={{ width: "auto" }} value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="APORTE">Aporte (compra)</option>
            <option value="RESGATE">Resgate (venda)</option>
            <option value="RENDIMENTO">Rendimento (vira receita)</option>
            <option value="REINVESTIMENTO">Reinvestimento (compõe posição)</option>
          </select>
        </Field>
        <Field label="Data">
          <input className="fw-input" style={{ width: "auto" }} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
        {!isRendimento && !contracted ? (
          <>
            <Field label="Quantidade de cotas">
              <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: 10" value={qty} onChange={(e) => setQty(e.target.value)} />
            </Field>
            <Field label="Preço por cota (R$)">
              <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={price} onChange={(e) => setPrice(e.target.value)} />
            </Field>
          </>
        ) : !isRendimento ? (
          <Field label="Valor (R$)">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
        ) : (
          <>
            <Field label="Valor do rendimento (R$)">
              <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </Field>
            <Field label="Conta de destino">
              <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                <option value="">Conta (rendimento)...</option>
                {(accounts ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
          </>
        )}
        <Button size="sm">Lançar</Button>
        {isRescue && (
          <Field label="IR retido (R$)" title="Imposto retido na fonte no resgate; o líquido (bruto − IR) cai na conta da corretora.">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={fees} onChange={(e) => setFees(e.target.value)} />
          </Field>
        )}
        {!contracted && isRescue && pos != null && Number(pos.quantity) > 0 && (
          <Button size="sm" variant="ghost" type="button" onClick={() => setQty(String(pos.quantity))}>
            Resgatar tudo
          </Button>
        )}
        {contracted && isRescue && (
          <Button size="sm" variant="danger" type="button" onClick={() => { setShowFull(!showFull); setFullDate(todayISO()); }}>
            Resgatar tudo
          </Button>
        )}
      </form>
      {partialPreview != null && <p>{partialPreview}</p>}
      {showFull && contracted && isRescue && (
        <form onSubmit={onFullRescue} className="fw-row" style={{ alignItems: "flex-end" }}>
          <Field label="Data do resgate total">
            <input className="fw-input" style={{ width: "auto" }} type="date" value={fullDate} onChange={(e) => setFullDate(e.target.value)} />
          </Field>
          <Field label="IR retido (R$)" title="Imposto retido na fonte; o líquido cai na conta da corretora.">
            <input className="fw-input" style={{ width: "auto" }} placeholder="0,00" value={fullFees} onChange={(e) => setFullFees(e.target.value)} />
          </Field>
          <Button size="sm" variant="danger" type="submit">
            Confirmar resgate total
          </Button>
          {pos?.current_value != null && (
            <span className="fw-sub">
              Bruto est. {brl(pos.current_value)}
              {rescuePreview(Number(pos.current_value), fullFees, parseNum) != null ? ` · ${rescuePreview(Number(pos.current_value), fullFees, parseNum)}` : ""}
            </span>
          )}
        </form>
      )}
    </>
  );
}
