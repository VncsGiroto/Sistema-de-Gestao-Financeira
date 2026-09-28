# BACKLOG — MVP (ordenado, com DoD)

## Épico 0 — Repositório e ambiente
- [x] 0.1 Scaffolding backend FastAPI + frontend Vite + Compose (DoD: `up -d` verde + `/api/docs` abre)
- [x] 0.2 CI `tests.yml` + lint/format/type (DoD: PR fake falha se quebrar)
- [x] 0.3 `.env.example`, README quickstart (DoD: clone→up em <10min)

## Épico 1 — Auth (JWT)
- [x] 1.1 register/login/refresh/logout/me (DoD: testes int + rate-limit)
- [x] 1.2 recover/reset/change + revogação em cadeia (DoD: reuse-detection testado)
- [x] 1.3 Telas login/register + guard rotas (DoD: E2E login)

## Épico 2 — Base financeira
- [x] 2.1 CRUD accounts/categories (DoD: scoping 403 testado)
- [x] 2.2 CRUD transactions + filtros + export CSV (DoD: filtro período/categoria)
- [x] 2.3 Telas contas/transações (DoD: editar categoria inline)

## Épico 3 — OFX + dedup (coração)
- [x] 3.1 Upload async + parse + import_items (DoD: fixture 5k linhas <10s)
- [x] 3.2 Exato + fuzzy ±2d + revisão + commit idempotente (DoD: testes DEDUP.md)
- [x] 3.3 Tela review lado a lado (DoD: E2E import→review→commit)

## Épico 4 — Futuro e parcelas
- [x] 4.1 recurring_bills CRUD + próximas vencidas (DoD: cálculo next_due)
- [x] 4.2 installments + schedule com arredondamento (DoD: soma parcelas == total)
- [x] 4.3 payables: une bills+installments em contas a pagar + baixa com lançamento + antecipação com desconto (DoD: E2E payables)

## Épico 5 — Dashboard
- [x] 5.1 `GET /dashboard` agregações (DoD: teste com massa conhecida)
- [x] 5.2 Tela dashboard + gráficos (DoD: filtro mês/conta reativo)

## Épico 6 — Hardening
- [x] 6.1 Headers, CORS, HSTS, backups PG documentados
- [x] 6.2 E2E completo + docs finais + staging

Commits: Conventional Commits EN (`feat:`, `fix:`, ...). Issues em PT.
