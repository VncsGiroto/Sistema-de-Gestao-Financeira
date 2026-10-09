import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import type { DashboardData, PortfolioSnapshot } from "../../lib/api";
import { Button } from "../../components/ui";

const FONT = "Inter, system-ui, sans-serif";
const GREEN = "#059669";
const SLATE = "#64748b";
const RED = "#dc2626";
const PALETTE = ["#059669", "#2563eb", "#d97706", "#7c3aed", "#db2777", "#0891b2", "#65a30d", "#475569"];

const moneyFmt = (v: number | string) =>
  Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function useChart(option: echarts.EChartsCoreOption | null) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !option) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [JSON.stringify(option)]);
  return ref;
}

export function EvolutionChart({ data }: { data: DashboardData }) {
  const ref = useChart({
    textStyle: { fontFamily: FONT },
    tooltip: { trigger: "axis", valueFormatter: (v: unknown) => moneyFmt(Number(v as number)) },
    legend: { data: ["Receitas", "Despesas"], textStyle: { color: SLATE }, bottom: 0 },
    grid: { left: 8, right: 8, top: 24, bottom: 52, containLabel: true },
    xAxis: { type: "category", data: data.evolution.map((e) => e.month), axisLine: { lineStyle: { color: "#e2e8f0" } }, axisLabel: { color: SLATE } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#eef2f0" } }, axisLabel: { color: SLATE } },
    series: [
      { name: "Receitas", type: "bar", data: data.evolution.map((e) => Number(e.income)), itemStyle: { color: GREEN, borderRadius: [6, 6, 0, 0] } },
      { name: "Despesas", type: "bar", data: data.evolution.map((e) => Number(e.expense)), itemStyle: { color: RED, borderRadius: [6, 6, 0, 0] } },
    ],
  });
  return <div ref={ref} style={{ width: "100%", height: 300 }} />;
}

export function CategoryPie({ title, items }: { title: string; items: { name: string; total: string }[] }) {  const total = items.reduce((a, c) => a + Number(c.total), 0);
  const ref = useChart({
    textStyle: { fontFamily: FONT },
    tooltip: { trigger: "item", valueFormatter: (v: unknown) => moneyFmt(Number(v as number)) },
    color: PALETTE,
    legend: {
      bottom: 0,
      textStyle: { color: SLATE },
      formatter: (name: string) => {
        const it = items.find((c) => c.name === name);
        const pct = total > 0 && it ? ((Number(it.total) / total) * 100).toFixed(1).replace(".", ",") : "0,0";
        return `${name} ${pct}%`;
      },
    },
    series: [{
      type: "pie",
      radius: "58%",
      center: ["50%", "46%"],
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
      label: { color: SLATE, formatter: "{b}" },
      labelLine: { length: 12, length2: 8 },
      data: items.map((c) => ({ name: c.name, value: Number(c.total) })),
    }],
  });
  return (
    <>
      <h3 style={{ margin: "0 0 4px", fontSize: 14, textAlign: "center" }}>{title}</h3>
      <div ref={ref} style={{ width: "100%", height: 320 }} />
    </>
  );
}

/** Resumo simples quando há 0–1 categorias (o pie não informa nada nesse caso). */
export function CategorySummary({ title, items }: { title: string; items: { name: string; total: string }[] }) {
  if (items.length === 0) return null;
  return (
    <>
      <h3 style={{ margin: "0 0 4px", fontSize: 14, textAlign: "center" }}>{title}</h3>
      <ul className="fw-list">
        {items.map((c) => (
          <li className="fw-list-item" key={c.name}>
            <span>{c.name} — {moneyFmt(c.total)} (100%)</span>
          </li>
        ))}
      </ul>
    </>
  );
}

/** Conversão pura snapshot → séries: posições/total só entram quando COMPLETE.
 *  Pontos INCOMPLETE/UNKNOWN (mesmo com números legados) viram lacuna, nunca zero. */
export interface ChartSeries {
  cash: number[];
  positions: (number | null)[];
  total: (number | null)[];
  hasGaps: boolean;
}

export function toChartSeries(snapshots: PortfolioSnapshot[]): ChartSeries {
  const priced = (v: string | null) => (v == null ? null : Number(v));
  const complete = (s: PortfolioSnapshot) => s.status === "COMPLETE";
  return {
    cash: snapshots.map((s) => Number(s.cash)),
    positions: snapshots.map((s) => (complete(s) ? priced(s.positions_value) : null)),
    total: snapshots.map((s) => (complete(s) ? priced(s.total) : null)),
    hasGaps: snapshots.some((s) => !complete(s)),
  };
}

/** Tooltip de um ponto: usa a série convertida (mesma fonte das linhas), de modo
 *  que ponto sem avaliação mostra "—" em posições/total, nunca números legados. */
export function formatSnapshotTip(
  s: PortfolioSnapshot,
  positions: number | null,
  total: number | null,
): string {
  const money = (v: number | null) => (v == null ? "—" : moneyFmt(v));
  let html = `${s.date}<br/>Caixa: ${moneyFmt(Number(s.cash))}<br/>Carteira: ${money(positions)}<br/>Total: ${money(total)}`;
  if (s.status !== "COMPLETE") {
    const why = s.status === "UNKNOWN"
      ? "histórico sem avaliação registrada"
      : `sem cotação: ${(s.unpriced ?? []).join(", ")}`;
    html += `<br/>(${why})`;
  }
  return html;
}

const dayMs = (d: string) => new Date(`${d}T00:00:00`).getTime();

/** Ponto exibível. */
export interface ChartPoint {
  date: string;
  cash: number | null;
  positions: number | null;
  total: number | null;
  gain: number | null;
  snap: PortfolioSnapshot;
}

/** Snapshots → pontos (1:1, na ordem). Lacunas reais de cotação continuam
 *  como null nas séries (nunca zero, nunca conectadas). Puro e testável. */
export function toChartPoints(snapshots: PortfolioSnapshot[]): ChartPoint[] {
  const priced = (v: string | null) => (v == null ? null : Number(v));
  const complete = (s: PortfolioSnapshot) => s.status === "COMPLETE";
  return snapshots.map((s) => ({
    date: s.date,
    cash: Number(s.cash),
    positions: complete(s) ? priced(s.positions_value) : null,
    total: complete(s) ? priced(s.total) : null,
    gain: priced(s.gain ?? null),
    snap: s,
  }));
}

/** Indexa a série em base 100 no primeiro valor não-nulo (modo % do gráfico).
 *  Nulos preservados; base ausente/zero → tudo null (sem inventar número). */
export function indexBase100(values: (number | null)[]): (number | null)[] {
  const base = values.find((v) => v != null);
  if (base == null || base === 0) return values.map(() => null);
  return values.map((v) => (v == null ? null : (v / base) * 100));
}

/** Tooltip do modo %: percentual com o R$ ancorado; quebra de segmento vazia. */
export function formatIndexedTip(p: ChartPoint, positionsPct: number | null, totalPct: number | null): string {
  if (p.snap == null) return "";
  const pct = (v: number | null, money: number | null) =>
    v == null ? "—" : `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% (${moneyFmt(money ?? 0)})`;
  return `${p.date}<br/>Carteira: ${pct(positionsPct, p.positions)}<br/>Total: ${pct(totalPct, p.total)}`;
}

/** Anexa o ponto "hoje" (não persistido) com os totais ao vivo do portfolio,
 *  para a série terminar no dia atual. Puro e testável. */
export function withToday(
  snapshots: PortfolioSnapshot[],
  live: { cash: string; positions_value: string | null; total: string | null; status: string; unpriced: string[] },
  today: string,
): PortfolioSnapshot[] {
  if (snapshots.length === 0) return snapshots;
  const last = snapshots[snapshots.length - 1].date;
  if (last >= today || snapshots.some((s) => s.date === today)) return snapshots;
  return [
    ...snapshots,
    {
      date: today,
      cash: live.cash,
      positions_value: live.positions_value,
      total: live.total,
      status: live.status,
      unpriced: live.unpriced,
    },
  ];
}

/** Linha de evolução; null abre lacuna (nunca zero): pontos sem cotação completa
 *  não conectam as linhas de posições/total. Sem 2+ pontos, mensagem honesta. */
export function SnapshotsLine({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const [mode, setMode] = useState<"brl" | "pct" | "gain">("brl");
  const points = toChartPoints(snapshots);
  const series = toChartSeries(snapshots);
  const positionsPct = indexBase100(points.map((p) => p.positions));
  const totalPct = indexBase100(points.map((p) => p.total));
  const isPct = mode === "pct";
  const isGain = mode === "gain";
  const spanDays = snapshots.length >= 2
    ? Math.round((dayMs(snapshots[snapshots.length - 1].date) - dayMs(snapshots[0].date)) / 86_400_000)
    : 0;
  const pctFmt = (v: number) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
  const gainTip = (params: unknown) => {
    const rows = Array.isArray(params) ? params : [params];
    const idx = (rows[0] as { dataIndex?: number })?.dataIndex ?? 0;
    const p = points[idx];
    return `${p.date}<br/>Ganhos acumulados: ${p.gain == null ? "—" : moneyFmt(p.gain)}`;
  };
  const ref = useChart(
    snapshots.length >= 2
      ? {
        textStyle: { fontFamily: FONT },
        tooltip: {
          trigger: "axis",
          formatter: isGain
            ? gainTip
            : isPct
              ? (params: unknown) => {
                const rows = Array.isArray(params) ? params : [params];
                const idx = (rows[0] as { dataIndex?: number })?.dataIndex ?? 0;
                return formatIndexedTip(points[idx], positionsPct[idx] ?? null, totalPct[idx] ?? null);
              }
              : (params: unknown) => {
                const rows = Array.isArray(params) ? params : [params];
                const idx = (rows[0] as { dataIndex?: number })?.dataIndex ?? 0;
                const p = points[idx];
                return formatSnapshotTip(p.snap, p.positions, p.total);
              },
        },
        legend: {
          data: isGain ? ["Ganhos"] : isPct ? ["Carteira", "Total"] : ["Caixa", "Carteira", "Total"],
          textStyle: { color: SLATE },
          bottom: 0,
        },
        grid: { left: 8, right: 8, top: 24, bottom: 52, containLabel: true },
        xAxis: { type: "category", data: points.map((p) => p.date), axisLine: { lineStyle: { color: "#e2e8f0" } }, axisLabel: { color: SLATE } },
        yAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#eef2f0" } },
          axisLabel: isPct ? { color: SLATE, formatter: pctFmt } : { color: SLATE },
        },
        series: isGain
          ? [
            { name: "Ganhos", type: "line", connectNulls: false, data: points.map((p) => p.gain), itemStyle: { color: "#7c3aed" } },
          ]
          : isPct
            ? [
              { name: "Carteira", type: "line", connectNulls: false, data: positionsPct, itemStyle: { color: "#2563eb" } },
              { name: "Total", type: "line", connectNulls: false, data: totalPct, itemStyle: { color: GREEN } },
            ]
            : [
              { name: "Caixa", type: "line", data: points.map((p) => p.cash), itemStyle: { color: SLATE } },
              {
                name: "Carteira",
                type: "line",
                connectNulls: false,
                data: points.map((p) => p.positions),
                itemStyle: { color: "#2563eb" },
              },
              {
                name: "Total",
                type: "line",
                connectNulls: false,
                data: points.map((p) => p.total),
                itemStyle: { color: GREEN },
              },
            ],
      }
      : null,
  );
  if (snapshots.length < 2) {
    return <p>Ainda não há histórico suficiente para o gráfico — ele aparece após movimentações em dias diferentes.</p>;
  }
  return (
    <>
      <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
        <Button size="sm" variant={mode !== "brl" ? "ghost" : undefined} onClick={() => setMode("brl")}>R$</Button>
        <Button size="sm" variant={mode !== "pct" ? "ghost" : undefined} onClick={() => setMode("pct")}>%</Button>
        <Button size="sm" variant={mode !== "gain" ? "ghost" : undefined} onClick={() => setMode("gain")}>Ganhos</Button>
      </div>
      <div ref={ref} style={{ width: "100%", height: 300 }} />
      <p><small>
        {snapshots.length} pontos em {spanDays} dias — segmentos unem eventos.
        {isPct && " Índice base 100 no primeiro ponto (Carteira e Total) — inclui aportes/resgates, não é rentabilidade pura."}
        {isGain && " Ganhos acumulados (total − aportes líquidos): o aporte em si não soma, mas o rendimento dele soma."}
      </small></p>
      {series.hasGaps && <p><small>Lacunas = dias sem cotação completa (posições/total indisponíveis, nunca zero).</small></p>}
    </>
  );
}
