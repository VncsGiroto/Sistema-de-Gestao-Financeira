/** Rótulos PT-BR para os enums da API (que trafegam em EN). */

export const accountTypeLabel: Record<string, string> = {
  CHECKING: "Corrente",
  SAVINGS: "Poupança",
  CASH: "Dinheiro",
  INVESTMENT: "Investimento",
  OTHER: "Outra",
};

export const txTypeLabel: Record<string, string> = {
  INCOME: "Receita",
  EXPENSE: "Despesa",
};

export const txSourceLabel: Record<string, string> = {
  MANUAL: "Manual",
  OFX: "OFX",
  IMPORT: "Importação",
  PAYABLE: "Conta paga",
};

export const billKindLabel: Record<string, string> = {
  FIXED: "Fixa",
  VARIABLE: "Variável",
  ONE_TIME: "Única",
  RECURRING: "Recorrente",
  INSTALLMENT: "Parcelada",
};

export const payableKindLabel: Record<string, string> = {
  FIXED: "Fixa",
  RECURRING: "Recorrente",
  INSTALLMENT: "Parcelada",
  ONE_TIME: "Única",
};

export const periodicityLabel: Record<string, string> = {
  MONTHLY: "Mensal",
  WEEKLY: "Semanal",
  YEARLY: "Anual",
};

export const importStatusLabel: Record<string, string> = {
  RECEIVED: "Recebida",
  PROCESSING: "Processando",
  VALIDATED: "Validada",
  IMPORTED: "Importada",
  FAILED: "Falhou",
};

export const verdictLabel: Record<string, string> = {
  NEW: "Nova",
  EXACT_DUPLICATE: "Duplicada exata",
  FUZZY_CANDIDATE: "Possível duplicata",
  INVALID: "Inválida",
};

export const labelOf = (map: Record<string, string>, value: string | null | undefined) =>
  (value != null && map[value]) || value || "—";
