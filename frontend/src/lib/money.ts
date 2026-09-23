/** Formatação monetária pt-BR centralizada. */
export function brl(value: string | number | undefined | null): string {
  return Number(value ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
