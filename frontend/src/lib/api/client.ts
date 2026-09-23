import { authApi } from "./auth";
import { accountsApi } from "./accounts";
import { categoriesApi } from "./categories";
import { downloadTransactionsCsv, txsApi } from "./transactions";
import { importsApi } from "./imports";
import { dashboardApi } from "./dashboard";
import { billsApi } from "./bills";
import { installmentsApi } from "./installments";
import { healthApi } from "./health";
import { authed, authFetch } from "./http";

/**
 * Facade com a mesma assinatura do antigo `api-client.ts`
 * para migração incremental. Código novo pode importar
 * os módulos (`./auth`, `./accounts`, ...) diretamente.
 */
export const api = {
  ...authApi,
  health: healthApi.check,
  accounts: accountsApi,
  categories: categoriesApi,
  txs: txsApi,
  imports: importsApi,
  dashboard: dashboardApi,
  bills: billsApi,
  installments: installmentsApi,
  authFetch,
  authed,
  downloadCsv: downloadTransactionsCsv,
};
