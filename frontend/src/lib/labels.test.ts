import { describe, expect, it } from "vitest";
import { accountTypeLabel, billKindLabel, importStatusLabel, labelOf, periodicityLabel, txTypeLabel, verdictLabel } from "../lib/labels";
import { brl } from "../lib/money";

describe("labels", () => {
  it("cobre todos os enums conhecidos", () => {
    expect(labelOf(accountTypeLabel, "CHECKING")).toBe("Corrente");
    expect(labelOf(txTypeLabel, "INCOME")).toBe("Receita");
    expect(labelOf(billKindLabel, "ONE_TIME")).toBe("Única");
    expect(labelOf(periodicityLabel, "WEEKLY")).toBe("Semanal");
    expect(labelOf(importStatusLabel, "FAILED")).toBe("Falhou");
    expect(labelOf(verdictLabel, "FUZZY_CANDIDATE")).toBe("Possível duplicata");
  });

  it("preserva desconhecidos e vazios", () => {
    expect(labelOf(txTypeLabel, "X")).toBe("X");
    expect(labelOf(txTypeLabel, null)).toBe("—");
    expect(labelOf(txTypeLabel, undefined)).toBe("—");
  });
});

describe("brl", () => {
  it("formata pt-BR", () => {
    expect(brl("1000")).toContain("1.000,00");
    expect(brl(0)).toContain("0,00");
    expect(brl(undefined)).toContain("0,00");
  });
});
