# FRONTEND — React + Vite SPA

## 1. Rotas (TanStack Router)

```
/login /register /recover /reset
/app → Painel (guarda: sem access tenta refresh via cookie, senão /login)
/app/accounts /app/categories /app/transactions /app/imports /app/imports/$id
/app/bills /app/installments /app/security
```

## 2. Estrutura

```
frontend/src/
  main.tsx routes/router.tsx
  lib/{api-client.ts, auth-store.tsx, labels.ts, money.ts}
  features/{auth, dashboard, finance, imports, bills, installments}/
  components/BackButton.tsx
```

`api-client.ts`: fetch tipado + `credentials:include`, injeta `Authorization`, tenta refresh (cookie) em 401 uma vez.
`labels.ts`: enums da API em PT-BR. `money.ts`: `brl()`. Botão Voltar sempre p/ `/app` (review p/ lista).

## 3. Telas MVP

- Dashboard: cards saldo/receita/despesa + evolução ECharts + pizza por categoria + filtro período/conta + seção Compromissos (total, saldo projetado, agenda 30/60/90d).
- Transactions: tabela com filtros §18 doc inicial + paginação + edição categoria inline + export CSV.
- Imports: upload OFX (account select + file) → polling status → tela review lado a lado → commit.
- Bills: contas futuras (fixa/variável/única/recorrente) + editar valor auditado.
- Installments: compra + schedule somando o total.

## 4. Estado e formato

TanStack Query p/ servidor (`staleTime 30s`); contexto só p/ auth (access em memória, refresh em cookie HttpOnly).
Dinheiro via `lib/money.ts` (`Intl.NumberFormat pt-BR/BRL`). Sem framework CSS (inline styles); sem `date-fns` (datas ISO).

## 6. Visual (premium clean, tema claro)

- `styles/tokens.css`: paleta (fundo `#F6F8FA`, esmeralda `#059669`), raios, sombras, sidebar 248px.
- `styles/base.css`: reset, layout `.fw-shell`, componentes (`.fw-btn/.fw-card/.fw-input/.fw-table/.fw-badge/.fw-metrics`) e responsivo mobile.
- `components/ui.tsx`: Button/Card/PageHeader/Badge + `verdictTone`; `components/Shell.tsx`: sidebar + topbar (Guard veste o Shell em todas as `/app/*`).
- ECharts com tema próprio (paleta, fonte Inter, tooltips em R$). Textos visíveis intactos (E2E estável).

## 5. Build

`vite build` → `dist/` servido pelo Nginx. Env: `VITE_API_URL=/api`. PWA opcional pós-MVP.
