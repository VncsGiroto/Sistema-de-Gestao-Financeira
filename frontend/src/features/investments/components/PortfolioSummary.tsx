import { CategoryPie, SnapshotsLine, withToday } from "../../dashboard/charts";
import { brl } from "../../../lib/money";
import { todayISO } from "../../../lib/date";
import { assetClassLabel, labelOf } from "../../../lib/labels";
import { Badge } from "../../../components/ui";
import type { Portfolio } from "../../../lib/api";

export function PortfolioSummary({ pf }: { pf: Portfolio }) {
  return (
    <section className="fw-card" style={{ marginBottom: 12 }}>
      <h2 style={{ marginTop: 0 }}>Resumo da carteira</h2>
      <p style={{ marginTop: 0 }}>
        <small>Escopo global e atual: ignora os filtros de conta/período do Painel.</small>
      </p>
      <div className="fw-metrics">
        <div className="fw-metric">
          <strong>Caixa nas corretoras</strong>
          <p>{brl(pf.cash)}</p>
          <small>dinheiro disponível para investir</small>
        </div>
        <div className="fw-metric">
          <strong>Posições</strong>
          <p>{pf.positions_value != null ? brl(pf.positions_value) : "—"}</p>
          <small>quantidade × preço atual</small>
        </div>
        <div className="fw-metric">
          <strong>Total</strong>
          <p>{pf.total != null ? brl(pf.total) : "—"}</p>
          <small>caixa + posições</small>
          {pf.status === "INCOMPLETE" && (
            <small title={`Sem cotação: ${pf.unpriced.join(", ")}`}>
              <Badge tone="amber">parcial</Badge>
            </small>
          )}
        </div>
        <div className="fw-metric">
          <strong>Resultado</strong>
          <p>{pf.resultado != null ? brl(pf.resultado) : "—"}</p>
          <small title="Taxa interna de retorno anualizada dos aportes, resgates e rendimentos (reinvestimento é fluxo interno e não entra)">
            XIRR {pf.xirr != null ? `${(Number(pf.xirr) * 100).toFixed(2)}% a.a.` : "—"} ⓘ
          </small>
          <small title="Apreciação da cotação da carteira; exclui proventos reinvestidos">
            {" "}
            · TWR de preço {pf.twr != null ? `${(Number(pf.twr) * 100).toFixed(2)}%` : "—"}
          </small>
        </div>
      </div>
      <p>
        Aportes {brl(pf.aportes)} · reinvestido {brl(pf.reinvestimentos)} · resgates {brl(pf.resgates)} · rendimentos {brl(pf.rendimentos)} · investido
        líquido {brl(pf.net_invested)}
      </p>
      {pf.unpriced.length > 0 && <p>Sem cotação: {pf.unpriced.join(", ")} — informe o preço manual no ativo.</p>}
      {pf.by_class.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <CategoryPie title="Por classe" items={pf.by_class.map((s) => ({ name: labelOf(assetClassLabel, s.name), total: s.total }))} />
        </div>
      )}
      <h3>Evolução {pf.history_since ? `(desde ${pf.history_since})` : ""}</h3>
      <SnapshotsLine snapshots={withToday(pf.snapshots, pf, todayISO())} />
    </section>
  );
}
