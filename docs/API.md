# API — FinanceWay MVP (REST + OpenAPI)

Base: `/api`. Auth: `Authorization: Bearer <access>` exceto rotas marcadas `público`. Erros formato RFC7807 (`type,title,status,detail,errors[]`). Paginação: `?page=1&per_page=20&order=-date` → `{data,meta:{page,per_page,total}}`.

Swagger: `/api/docs`. ReDoc: `/api/redoc`. Spec: `backend/openapi.yaml` (gerado pelo FastAPI).

## 1. Auth

| Método | Rota | Auth | Body → 2xx |
|---|---|---|---|
| POST | `/api/auth/register` | público, rate-limit | `{name,email,password}` → `201 {id,email}` |
| POST | `/api/auth/login` | público, rate-limit | `{email,password}` → `200 {access_token,refresh_token,expires_in}` |
| POST | `/api/auth/refresh` | refresh token | `{refresh_token}` → `200 {access_token,novo refresh (rotação)}` |
| POST | `/api/auth/logout` | bearer | `{refresh_token}` → `204` (revoga + deny-list Redis) |
| POST | `/api/auth/recover` | público, rate-limit | `{email}` → `202` (sempre, anti-enumeração) |
| POST | `/api/auth/reset` | público | `{token,new_password}` → `204` |
| PATCH | `/api/auth/change` | bearer | `{current_password,new_password}` → `204` |
| GET | `/api/auth/me` | bearer | → `200 User` |

## 2. Accounts / Categories / Transactions

```
GET+POST /api/accounts · GET+PATCH+DELETE /api/accounts/{id}
GET+POST /api/categories?type=EXPENSE · GET+PATCH+DELETE /api/categories/{id}
GET+POST /api/transactions?from=&to=&category_id=&account_id=&type=&source=&payable_id=&q=&min=&max=
GET+PATCH+DELETE /api/transactions/{id}
POST /api/transactions/categorize {ids[], category_id} → {updated, skipped_type, skipped_missing} (pula incompatíveis)

```
POST /api/transfers {from_account_id, to_account_id, amount, date?, description?} → 201 (ledger patrimonial; sem efeito em receita/despesa)
GET /api/transfers?account_id= → lista (origem ou destino)
DELETE /api/transfers/{id} → 204 (reverte os dois lados; só TRANSFER avulsa)
```
POST /api/assets {ticker, asset_class, subtype, account_id? (INVESTMENT), ...} → 201 (409 ticker duplicado na mesma conta)
PATCH /api/assets/{id} {account_id?, ...} → 200 (conta deve ser INVESTMENT)
POST /api/assets/{id}/ops {APORTE|RESGATE (exigem conta vinculada; movem caixa atomicamente)|RENDIMENTO (espelha INCOME)|REINVESTIMENTO (posição/custo, sem receita/caixa)}
GET /api/portfolio → {cash, positions_value, total, patrimonio, aportes, reinvestimentos, resgates, rendimentos, net_invested, resultado, xirr, positions[], unpriced[], by_class[], by_account[], snapshots[], history_since}
```
GET /api/transactions/export?format=csv&... (mesmos filtros)
```

Exemplo `POST /api/transactions`:
```json
{"account_id":1,"category_id":3,"date":"2026-09-22","description":"SUPERMERCADO XYZ","amount":250.50,"type":"EXPENSE"}
```
`amount` usa sinal? Não: `amount` sempre > 0; o `type` (INCOME/EXPENSE) dá o sentido semântico. `CHECK (amount > 0)`.

## 3. Imports OFX

```
POST /api/imports/ofx (multipart: account_id, file .ofx) → 202 {import_id,status:RECEIVED}
GET /api/imports → lista com contadores
GET /api/imports/{id} → status + resumo {total,imported,duplicates,failed}
GET /api/imports/{id}/items → [{id, row_no, verdict, payload, matched_transaction_id, decision}] (`decision` nulo até revisar)
POST /api/imports/{id}/review {decisions:[{item_id,decision:KEEP_BOTH|DISCARD_IMPORTED}]} → 200
POST /api/imports/{id}/commit → 200 {imported_rows} (só após review dos FUZZY)
```

## 4. Payables / Investimentos / Dashboard

```
GET+POST /api/payables?kind= (+ GET /upcoming?days= · GET+PATCH+DELETE /api/payables/{id})
GET /api/payables/{id}/schedule → [{n,due_date,amount,paid}] (só INSTALLMENT; soma == total)
POST /api/payables/{id}/pay {account_id,amount?,date?,category_id?,ns?,discount?}
  → 200 {transactions[], payable} (source=PAYABLE; recorrente avança next_due;
     INSTALLMENT aceita ns múltiplos + discount rateado; 2ª baixa de ONE_TIME → 422)
GET+POST /api/assets?asset_class= (+ GET+PATCH+DELETE /api/assets/{id})
GET+POST /api/assets/{id}/ops (+ DELETE /ops/{op_id}) · kinds APORTE/RESGATE/RENDIMENTO
GET /api/assets/{id}/position → {quantity,average_price,invested,aportes,resgates,rendimentos,current_*}
GET /api/assets/{id}/prices (histórico) + POST (preço manual)
GET /api/assets/{id}/returns → {simple,xirr,twr,twr_annualized,benchmarks{cdi,ipca}}
GET /api/dashboard?from=&to=&account_id= → {balance, income:{total,by_category[]}, expense:{total,by_category[]}, evolution:[{month,income,expense}]}
GET /api/dashboard/commitments?horizon_days=60 → {total, items[{kind,description,due_date,amount,ref_id}]}
GET /api/transactions/export/csv → CSV `;` com BOM (mesmos filtros da listagem)
```

Refresh também via cookie HttpOnly `fw_refresh` (corpo mantido por compat).

Exemplo dashboard:
```json
{"balance":5400.00,"income":{"total":9800.00,"by_category":[{"name":"Salário","total":8000}]},
 "expense":{"total":4400.00,"by_category":[{"name":"Moradia","total":2000}]},
 "evolution":[{"month":"2026-09","income":9800,"expense":4400}]}
```

## 5. Códigos de erro

`400 validação` · `401 token inválido/expirado` · `403 recurso de outro user` · `404` · `409 external_id duplicado` · `422 OFX inválido` · `429 rate-limit`.
