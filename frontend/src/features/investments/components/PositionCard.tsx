import { brl } from "../../../lib/money";
import { labelOf, priceSourceLabel } from "../../../lib/labels";
import { Badge } from "../../../components/ui";
import { pct } from "../lib/formatters";
import type { Position } from "../../../lib/api";

export function PositionCard({ pos, contracted }: { pos: Position; contracted: boolean }) {
  const hasOps =
    Number(pos.aportes) > 0 || Number(pos.resgates) > 0 || Number(pos.rendimentos) > 0 || Number(pos.reinvestimentos) > 0;

  if (!hasOps) {
    return <p>Lance um aporte abaixo para começar — a posição aparece aqui.</p>;
  }

  if (contracted) {
    return (
      <p>
        Aplicado {brl(pos.invested)} · atual {pos.current_value != null ? brl(pos.current_value) : "—"}
        {pos.current_value != null && <> · rendimento {brl(String(Number(pos.current_value) - Number(pos.invested)))}</>}
        {pos.net_value != null && (
          <>
            {" "}· líquido est. {brl(pos.net_value)}{" "}
            <small
              title={`IR estimado ${brl(pos.net_tax)} · alíquota ${pos.net_rate}% (${pos.net_rate_source === "manual" ? "informada" : "automática"}) — estimativa gerencial, não apuração fiscal`}
            >
              ⓘ
            </small>
          </>
        )}
        {pos.current_value != null && (
          <>
            {" "}
            <Badge tone="blue">
              {labelOf(priceSourceLabel, pos.price_source)} {pos.price_as_of}
            </Badge>
          </>
        )}
      </p>
    );
  }

  return (
    <p>
      Qtd {pos.quantity} · médio {brl(pos.average_price)} · investido {brl(pos.invested)}
      {pos.current_value != null && (
        <>
          {" "}
          · atual {brl(pos.current_value)}{" "}
          <Badge tone="blue">
            {labelOf(priceSourceLabel, pos.price_source)} {pos.price_as_of}
          </Badge>{" "}
          · P&L {brl(pos.pnl)} · {pct(pos.profitability)}
          {pos.net_value != null && (
            <>
              {" "}· líquido est. {brl(pos.net_value)}{" "}
              <small
                title={`IR estimado ${brl(pos.net_tax)} · alíquota ${pos.net_rate}% (${pos.net_rate_source === "manual" ? "informada" : "automática"}) — estimativa gerencial, não apuração fiscal`}
              >
                ⓘ
              </small>
            </>
          )}
        </>
      )}
      {pos.current_value == null && (
        <>
          {" "}
          · <Badge tone="amber">Sem preço — informe o preço manual abaixo</Badge>
        </>
      )}
    </p>
  );
}
