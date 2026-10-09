import type { Payable, PayableScheduleItem } from "../../../lib/api";

export function kindTone(kind: string): "green" | "red" | "amber" | "blue" | "" {
  if (kind === "FIXED") return "blue";
  if (kind === "RECURRING") return "amber";
  if (kind === "INSTALLMENT") return "";
  return "green";
}

export function isPaid(p: Payable): boolean {
  return (p.kind === "ONE_TIME" && !!p.paid_at) || (p.kind === "INSTALLMENT" && p.num_installments != null && (p.paid_ns ?? []).length >= p.num_installments);
}

export function unpaidItems(sched: PayableScheduleItem[] | undefined): PayableScheduleItem[] {
  return (sched ?? []).filter((s) => !s.paid);
}

export function targetsForInstallment(unpaid: PayableScheduleItem[], ns: number[]): PayableScheduleItem[] {
  return ns.length ? unpaid.filter((s) => ns.includes(s.n)) : unpaid.slice(0, 1);
}

export function grossOf(items: PayableScheduleItem[]): number {
  return items.reduce((acc, s) => acc + Number(s.amount), 0);
}

export function parseDiscount(s: string): number {
  return Number(s.replace(",", ".")) || 0;
}
