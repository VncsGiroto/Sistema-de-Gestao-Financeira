# FinanceWay — Gestão Financeira Pessoal (MVP)

Centralize contas, importe OFX (com deduplicação revisada), categorize, acompanhe contas futuras/parcelas e veja o painel com agenda de compromissos.

**Stack:** Python 3.13 + FastAPI · React 19 + Vite 6 + TS 5.6 · PostgreSQL 16 · Redis 7 · Nginx 1.27 · Docker Compose · GitHub Actions.

## Quickstart (<10 min)

Pré-requisitos: Docker + Compose plugin.

```bash
cp .env.example .env
# troque JWT_SECRET por 32+ chars aleatórios
docker compose up -d --build
# app:    http://localhost:8080
# Swagger: http://localhost:8080/api/docs
```

Fluxo inicial: registre-se → crie uma conta → lance ou importe um `.ofx` → revise em Importações → confirme → veja o Painel.

## Comandos

```bash
docker compose up -d --build     # sobe tudo (api faz alembic upgrade head no boot)
docker compose logs -f api       # acompanha boot/migrations
docker compose down              # para (mantém dados); down -v APAGA o banco

# backend (ou via CI): ruff check . && ruff format --check . && mypy app
#   unit:  pytest -m "not integration"  (puro, sem infra)
#   int:   TEST_DATABASE_URL=... TEST_REDIS_URL=... pytest -m integration
# frontend: npm run lint && npm run typecheck && npm run test && npm run build
# e2e:      npx playwright test   # exige compose no ar (ver e2e.yml no CI)

./scripts/backup.sh              # pg_dump via compose → backup-*.sql
```

## Variáveis (`.env`)

| Var | Padrão | Notas |
|---|---|---|
| `POSTGRES_USER/PASSWORD/DB` | finance/finance/financeway | volume `pgdata` persiste |
| `JWT_SECRET` | — | **trocar**, 32+ chars |
| `NGINX_PORT` | 8080 | |
| `ENV` | dev | `prod` = Redis fail-closed + cookie Secure |
| `CORS_ORIGINS` | localhost:8080,5173 | csv |
| `COOKIE_SECURE` | false | `true` atrás de HTTPS |

## Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| `FATAL: database "finance" does not exist` no log do db | healthcheck antigo sem `-d` (já corrigido) | `compose up -d` com o compose atual |
| `429 / Muitas tentativas` no login/E2E | rate-limit Redis (10/min) ou Nginx (30r/m) | aguarde a janela ou `exec redis redis-cli flushdb` (dev) |
| `alembic_version` travada / tabelas faltando | volume de outro ciclo | confira `SELECT version_num`; em último caso `down -v` (apaga dados) e `up` |
| E2E falha após `down/up` | dados de teste antigos | os testes de integração fazem `drop_all` — nunca aponte `TEST_DATABASE_URL` p/ prod |

## Estrutura

```
backend/ (FastAPI: auth, users, finance, imports, bills, installments, dashboard)
frontend/ (React SPA: auth, finance, imports, bills, installments, dashboard+commitments)
infrastructure/nginx/  scripts/backup.sh  docs/  .github/workflows/
```

## Docs

`SPEC-MVP.md` (escopo/stack) · `ARCHITECTURE.md` · `DATABASE.md` (DDL, cadeia 0001→0008) · `API.md` · `SECURITY.md` · `OFX-IMPORT.md` · `DEDUP.md` · `FRONTEND.md` · `TESTING.md` · `DEPLOY.md` (staging) · `BACKLOG.md`.

## Roadmap

MVP entregue (Épicos 0–6). Pós-MVP: Pluggy/Belvo, Open Finance, holerites, investimentos, app nativo, categorização inteligente.
