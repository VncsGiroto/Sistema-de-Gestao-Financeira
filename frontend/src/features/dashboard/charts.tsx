import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { DashboardData } from "../../lib/api-client";

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

export function CategoryPie({ title, items }: { title: string; items: { name: string; total: string }[] }) {
  const total = items.reduce((a, c) => a + Number(c.total), 0);
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
