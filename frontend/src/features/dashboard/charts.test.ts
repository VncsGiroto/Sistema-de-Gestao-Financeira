import { describe, expect, it } from "vitest";
import { formatSnapshotTip, toChartSeries } from "./charts";
import type { PortfolioSnapshot } from "../../lib/api";

function snap(over: Partial<PortfolioSnapshot> & { date: string }): PortfolioSnapshot {
  return {
    cash: "100.00",
    positions_value: "50.00",
    total: "150.00",
    status: "COMPLETE",
    unpriced: [],
    ...over,
  };
}

describe("toChartSeries", () => {
  it("ponto UNKNOWN com números vira lacuna (nunca desenha o legado)", () => {
    const out = toChartSeries([
      snap({ date: "2020-01-01", status: "UNKNOWN" }),
      snap({ date: "2026-10-07", status: "COMPLETE" }),
    ]);
    expect(out.positions).toEqual([null, 50]);
    expect(out.total).toEqual([null, 150]);
    expect(out.cash).toEqual([100, 100]);
    expect(out.hasGaps).toBe(true);
  });

  it("INCOMPLETE com null segue null; COMPLETE passa os números", () => {
    const out = toChartSeries([
      snap({ date: "2026-10-06", status: "INCOMPLETE", positions_value: null, total: null, unpriced: ["X"] }),
      snap({ date: "2026-10-07", status: "COMPLETE" }),
    ]);
    expect(out.positions).toEqual([null, 50]);
    expect(out.total).toEqual([null, 150]);
    expect(out.hasGaps).toBe(true);
  });

  it("série toda COMPLETE não tem lacuna", () => {
    const out = toChartSeries([snap({ date: "2026-10-06" }), snap({ date: "2026-10-07" })]);
    expect(out.positions).toEqual([50, 50]);
    expect(out.hasGaps).toBe(false);
  });
});

describe("formatSnapshotTip", () => {
  it("COMPLETE mostra os valores", () => {
    const html = formatSnapshotTip(snap({ date: "2026-10-07" }), 50, 150);
    expect(html).toMatch(/Posições: R\$\s50,00/);
    expect(html).toMatch(/Total: R\$\s150,00/);
    expect(html).not.toContain("sem cotação");
  });

  it("INCOMPLETE mostra — com o motivo, mesmo recebendo números", () => {
    const s = snap({ date: "2026-10-06", status: "INCOMPLETE", unpriced: ["X"] });
    const html = formatSnapshotTip(s, null, null);
    expect(html).toContain("Posições: —");
    expect(html).toContain("Total: —");
    expect(html).toContain("sem cotação: X");
    expect(html).toMatch(/Caixa: R\$\s100,00/);
  });

  it("UNKNOWN com números legados não vaza valores", () => {
    const s = snap({ date: "2020-01-01", status: "UNKNOWN" });
    const html = formatSnapshotTip(s, null, null);
    expect(html).toContain("Posições: —");
    expect(html).toContain("histórico sem avaliação registrada");
  });
});
