import { authApi } from "./auth";
import { accountsApi } from "./accounts";
import { categoriesApi } from "./categories";
import { downloadTransactionsCsv, txsApi } from "./transactions";
import { downloadMovementsCsv, movementsApi } from "./movements";
import { transfersApi } from "./transfers";
import { importsApi } from "./imports";
import { dashboardApi } from "./dashboard";
import { assetsApi } from "./investments";
import { payablesApi } from "./payables";
import { healthApi } from "./health";
import { authed, authFetch } from "./http";

/**
 * Facade com a mesma assinatura do antigo `api.ts`
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
  assets: assetsApi,
  payables: payablesApi,
  transfers: transfersApi,
  movements: movementsApi,
  authFetch,
  authed,
  downloadCsv: downloadTransactionsCsv,
  downloadMovementsCsv,
};
