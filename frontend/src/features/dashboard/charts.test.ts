import { describe, expect, it } from "vitest";
import { formatIndexedTip, formatSnapshotTip, formatTwrTip, indexBase100, toChartPoints, toChartSeries, withToday } from "./charts";
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

describe("toChartPoints", () => {
  it("pontos distantes seguem conectados (1:1, sem quebra)", () => {
    const pts = toChartPoints([snap({ date: "2026-03-01" }), snap({ date: "2026-10-08" })]);
    expect(pts.map((p) => p.date)).toEqual(["2026-03-01", "2026-10-08"]);
    expect(pts[0].total).toBe(150);
  });

  it("INCOMPLETE vira null", () => {
    const pts = toChartPoints([
      snap({ date: "2026-10-06", status: "INCOMPLETE", positions_value: null, total: null }),
      snap({ date: "2026-10-07" }),
    ]);
    expect(pts.map((p) => p.date)).toEqual(["2026-10-06", "2026-10-07"]);
    expect(pts[0].positions).toBeNull();
  });

  it("repasse do ganho (null quando ausente)", () => {
    const pts = toChartPoints([
      snap({ date: "2026-10-06", gain: "0.00" }),
      snap({ date: "2026-10-07", gain: "25.50" }),
      snap({ date: "2026-10-08" }),
    ]);
    expect(pts.map((p) => p.gain)).toEqual([0, 25.5, null]);
  });

  it("repasse do TWR (null quando ausente)", () => {
    const pts = toChartPoints([
      snap({ date: "2026-10-06", twr: "0" }),
      snap({ date: "2026-10-07", twr: "0.0909" }),
      snap({ date: "2026-10-08" }),
    ]);
    expect(pts.map((p) => p.twr)).toEqual([0, 0.0909, null]);
  });
});

describe("indexBase100", () => {
  it("indexa no primeiro não-nulo e preserva nulos", () => {
    expect(indexBase100([50, 60, null, 75])).toEqual([100, 120, null, 150]);
  });

  it("base ausente ou zero → tudo null", () => {
    expect(indexBase100([null, null])).toEqual([null, null]);
    expect(indexBase100([0, 10])).toEqual([null, null]);
  });
});

describe("withToday", () => {
  const live = { cash: "10.00", positions_value: "20.00", total: "30.00", status: "COMPLETE", unpriced: [] as string[] };

  it("anexa hoje quando a série termina antes", () => {
    const out = withToday([snap({ date: "2026-10-07" })], live, "2026-10-09");
    expect(out.map((s) => s.date)).toEqual(["2026-10-07", "2026-10-09"]);
    expect(out[1].total).toBe("30.00");
  });

  it("não duplica quando hoje já existe; vazio segue vazio", () => {
    expect(withToday([snap({ date: "2026-10-09" })], live, "2026-10-09")).toHaveLength(1);
    expect(withToday([], live, "2026-10-09")).toEqual([]);
  });
});

describe("formatTwrTip", () => {
  it("mostra % puro com total ancorado; sem TWR mostra —", () => {
    const pts = toChartPoints([
      snap({ date: "2026-10-06", twr: "0", total: "1000.00" }),
      snap({ date: "2026-10-07", twr: "0.0909", total: "1100.00" }),
      snap({ date: "2026-10-08" }),
    ]);
    expect(formatTwrTip(pts[1])).toContain("9,09%");
    expect(formatTwrTip(pts[1])).toContain("R$");
    expect(formatTwrTip(pts[2])).toContain("TWR acumulado: —");
  });
});
describe("formatIndexedTip", () => {
  it("mostra % com R$ ancorado", () => {
    const pts = toChartPoints([snap({ date: "2026-10-06" }), snap({ date: "2026-10-07" })]);
    const html = formatIndexedTip(pts[1], 120, 110);
    expect(html).toContain("120%");
    expect(html).toContain("110%");
    expect(html).toContain("R$");
  });
});
describe("formatSnapshotTip", () => {
  it("COMPLETE mostra os valores", () => {
    const html = formatSnapshotTip(snap({ date: "2026-10-07" }), 50, 150);
    expect(html).toMatch(/Carteira: R\$\s50,00/);
    expect(html).toMatch(/Total: R\$\s150,00/);
    expect(html).not.toContain("sem cotação");
  });

  it("INCOMPLETE mostra — com o motivo, mesmo recebendo números", () => {
    const s = snap({ date: "2026-10-06", status: "INCOMPLETE", unpriced: ["X"] });
    const html = formatSnapshotTip(s, null, null);
    expect(html).toContain("Carteira: —");
    expect(html).toContain("Total: —");
    expect(html).toContain("sem cotação: X");
    expect(html).toMatch(/Caixa: R\$\s100,00/);
  });

  it("UNKNOWN com números legados não vaza valores", () => {
    const s = snap({ date: "2020-01-01", status: "UNKNOWN" });
    const html = formatSnapshotTip(s, null, null);
    expect(html).toContain("Carteira: —");
    expect(html).toContain("histórico sem avaliação registrada");
  });
});
