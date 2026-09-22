# BACKLOG — MVP (ordenado, com DoD)

## Épico 0 — Repositório e ambiente
- [ ] 0.1 Scaffolding backend FastAPI + frontend Vite + Compose (DoD: `up -d` verde + `/api/docs` abre)
- [ ] 0.2 CI `tests.yml` + lint/format/type (DoD: PR fake falha se quebrar)
- [ ] 0.3 `.env.example`, README quickstart (DoD: clone→up em <10min)

## Épico 1 — Auth (JWT)
- [ ] 1.1 register/login/refresh/logout/me (DoD: testes int + rate-limit)
- [ ] 1.2 recover/reset/change + revogação em cadeia (DoD: reuse-detection testado)
- [ ] 1.3 Telas login/register + guard rotas (DoD: E2E login)

## Épico 2 — Base financeira
- [ ] 2.1 CRUD accounts/categories (DoD: scoping 403 testado)
- [ ] 2.2 CRUD transactions + filtros + export CSV (DoD: filtro período/categoria)
- [ ] 2.3 Telas contas/transações (DoD: editar categoria inline)

## Épico 3 — OFX + dedup (coração)
- [ ] 3.1 Upload async + parse + import_items (DoD: fixture 5k linhas <10s)
- [ ] 3.2 Exato + fuzzy ±2d + revisão + commit idempotente (DoD: testes DEDUP.md)
- [ ] 3.3 Tela review lado a lado (DoD: E2E import→review→commit)

## Épico 4 — Futuro e parcelas
- [ ] 4.1 recurring_bills CRUD + próximas vencidas (DoD: cálculo next_due)
- [ ] 4.2 installments + schedule com arredondamento (DoD: soma parcelas == total)

## Épico 5 — Dashboard
- [ ] 5.1 `GET /dashboard` agregações (DoD: teste com massa conhecida)
- [ ] 5.2 Tela dashboard + gráficos (DoD: filtro mês/conta reativo)

## Épico 6 — Hardening
- [ ] 6.1 Headers, CORS, HSTS, backups PG documentados
- [ ] 6.2 E2E completo + docs finais + staging

Commits: Conventional Commits EN (`feat:`, `fix:`, ...). Issues em PT.
