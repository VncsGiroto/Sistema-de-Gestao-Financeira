# FRONTEND — React + Vite SPA

## 1. Rotas (TanStack Router)

```
/login /register /recover /reset
/app → layout autenticado (guarda: sem access válido redireciona /login)
/app/dashboard /app/transactions /app/accounts /app/categories /app/imports /app/imports/:id /app/bills
```

## 2. Estrutura

```
frontend/src/
  main.tsx routes/__root.tsx
  lib/{api-client.ts, auth-store.tsx, query-client.ts, money.ts}
  features/{auth, dashboard, transactions, accounts, categories, imports, bills}/
    {page.tsx, components/, hooks.ts}
  components/ui/ (shadcn)
```

`api-client.ts`: fetch tipado gerado do OpenAPI, injeta `Authorization`, tenta refresh em 401 uma vez.

## 3. Telas MVP

- Dashboard: cards saldo/receita/despesa + evolução ECharts + pizza por categoria + filtro período/conta.
- Transactions: tabela com filtros §18 doc inicial + paginação + edição categoria inline + export CSV.
- Imports: upload OFX (account select + drag-drop) → polling status → tela review lado a lado → commit.
- Bills: contas futuras + parcelas com calendário mensal.

## 4. Estado e formato

TanStack Query p/ servidor (`staleTime 30s` dashboard); contexto só p/ auth. Dinheiro via `Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'})`. Datas `date-fns` + timezone America/Sao_Paulo.

## 5. Build

`vite build` → `dist/` servido pelo Nginx. Env: `VITE_API_URL=/api`. PWA opcional pós-MVP.
