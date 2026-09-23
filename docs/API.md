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
GET+POST /api/transactions?from=&to=&category_id=&account_id=&type=&source=&q=&min=&max=
GET+PATCH+DELETE /api/transactions/{id}
GET /api/transactions/export?format=csv&... (mesmos filtros)
```

Exemplo `POST /api/transactions`:
```json
{"account_id":1,"category_id":3,"date":"2026-09-22","description":"SUPERMERCADO XYZ","amount":-250.50,"type":"EXPENSE"}
```
`amount` usa sinal? Não: `amount` sempre >0 no MVP? **Não** — decisão: `amount` pode ser negativo p/ compat OFX, mas `type` é autoritativo. `CHECK (amount <> 0)`.

## 3. Imports OFX

```
POST /api/imports/ofx (multipart: account_id, file .ofx) → 202 {import_id,status:RECEIVED}
GET /api/imports → lista com contadores
GET /api/imports/{id} → status + resumo {total,imported,duplicates,failed}
GET /api/imports/{id}/items?verdict=FUZZY_CANDIDATE → itens p/ revisão
POST /api/imports/{id}/review {decisions:[{item_id,decision:KEEP_BOTH|DISCARD_IMPORTED}]} → 200
POST /api/imports/{id}/commit → 200 {imported_rows} (só após review dos FUZZY)
```

## 4. Bills / Installments / Dashboard

```
GET+POST /api/bills (+ GET /upcoming?days= · GET+PATCH+DELETE /api/bills/{id})
GET+POST /api/installments (+ GET+PATCH+DELETE /{id})
GET /api/installments/{id}/schedule → [{n,due_date,amount}] (soma == total)
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
