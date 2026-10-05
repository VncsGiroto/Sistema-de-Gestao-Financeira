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

export const payableKindHelp: Record<string, string> = {
  FIXED: "Valor igual todo mês no mesmo dia. A baixa usa sempre o valor cadastrado.",
  RECURRING: "Vence todo período, mas o valor pode variar — a baixa atualiza a estimativa.",
  INSTALLMENT: "Uma compra dividida: cada parcela vence no seu mês e é baixada separadamente.",
  ONE_TIME: "Vence uma única vez em data marcada.",
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

export const assetClassLabel: Record<string, string> = {
  RENDA_FIXA: "Renda fixa",
  RENDA_VARIAVEL: "Renda variável",
  FUNDOS: "Fundos",
  CRIPTO: "Cripto",
  OUTROS: "Outros",
};

export const rateTypeLabel: Record<string, string> = {
  CDI_PCT: "% do CDI",
  PREFIXADO: "Prefixado (a.a.)",
  IPCA_MAIS: "IPCA + (a.a.)",
};

export const rateTypeHelp: Record<string, string> = {
  CDI_PCT: "Percentual do CDI (ex.: 110 = 110% do CDI).",
  PREFIXADO: "Taxa anual fixa contratada (ex.: 12 = 12% a.a.).",
  IPCA_MAIS: "Taxa anual acima do IPCA (ex.: 6 = IPCA + 6% a.a.).",
};

export const opKindLabel: Record<string, string> = {
  APORTE: "Aporte",
  RESGATE: "Resgate",
  RENDIMENTO: "Rendimento",
};

export const opKindHelp: Record<string, string> = {
  APORTE: "Compra: aumenta quantidade e custo médio.",
  RESGATE: "Venda parcial/total: reduz quantidade e baixa a base de custo pelo médio vigente.",
  RENDIMENTO: "Provento: não altera a posição, mas cria uma receita no extrato na conta de destino.",
};

export const priceSourceLabel: Record<string, string> = {
  MANUAL: "manual",
  ACCRUAL: "projeção do contrato",
  BRAPI: "mercado",
};
