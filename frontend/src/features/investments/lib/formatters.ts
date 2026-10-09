import { brl } from "../../../lib/money";

export function pct(v: string | null): string {
  if (v == null) return "—";
  return `${(Number(v) * 100).toFixed(2)}%`;
}

export function rescuePreview(gross: number | null, ir: string, parseNum: (s: string) => number): string | null {
  if (gross == null || Number.isNaN(gross) || gross <= 0) return null;
  const t = ir.trim() ? parseNum(ir) : 0;
  if (ir.trim() && (Number.isNaN(t) || t < 0)) return null;
  return `Bruto ${brl(gross)} − IR ${brl(t)} = líquido est. ${brl(gross - t)}`;
}
