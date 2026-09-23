# SPEC-MVP — FinanceWay

> Origem: `Documentação Inicial — Sistema de Gestão Financeira.md` §§32,37.
> Status: **travada** em 2026-09-22.

## 1. Objetivo do MVP

Entregar gestão financeira pessoal funcional com: cadastro/login, contas, receitas/despesas, categorias, importação OFX com deduplicação revisada por humano, dashboard, contas futuras e parcelamentos. Tudo rodando via `docker compose up -d`, com Swagger, testes e CI.

Fora do MVP (pós-MVP): Pluggy/Belvo, APIs bancárias/Open Finance, holerites, investimentos automatizados, app mobile nativo, regras inteligentes de categorização.

## 2. Stack definitiva

| Camada | Decisão | Versão base |
|---|---|---|
| Backend | Python + FastAPI + SQLAlchemy 2 async + Alembic + Pydantic v2 | Python 3.13 |
| Frontend Web | React + Vite + TypeScript + TanStack Router/Query + ECharts | React 19, Vite 6, TS 5.6, Node 22 |
| Banco | PostgreSQL | 16 |
| Cache/Fila/Rate-limit | Redis | 7 |
| Proxy | Nginx (reverse proxy + estáticos do front + headers segurança) | 1.27 |
| Auth | JWT access 15min + refresh 30d rotativo com reuse-detection; refresh em cookie HttpOnly `fw_refresh` | — |
| Hash senha | Argon2id (fallback bcrypt) | — |
| API | REST + OpenAPI 3.1 em `/api/docs` (Swagger) + `/api/redoc` | — |
| Testes | pytest + httpx (unit/int API), Vitest + Playwright (front/e2e) | — |
| Qualidade | ruff + mypy (backend, `pyproject.toml`), eslint + tsc (front) | — |
| Containers | Docker + Docker Compose | — |
| CI/CD | GitHub Actions | — |

Decisões descartadas e motivo:

- NestJS: excelente DI, mas boilerplate alto e libs OFX mais fracas que Python.
- Next.js: overkill p/ SPA autenticada sem SEO; self-host mais pesado.
- Django/Spring/.NET/Go: ou pesados p/ MVP solo ou pouco produtivos p/ CRUD+OFX.
- Mobile híbrido: futuro será nativo, front web não precisa reusar código.

## 3. Princípios (vêm do §33)

1. Dados pertencem ao usuário → exportação CSV em `GET /api/transactions/export`.
2. Nada se exclui/mergeia automaticamente → deduplicação sempre gera fila de revisão.
3. Segurança desde o início → ver `SECURITY.md`.
4. Fonte-independente → pipeline `Importer → Normalizer → Validator → DuplicateDetector → Persist` (ver `ARCHITECTURE.md`).
5. Extensível → `O`: novo conector implementa `BaseImporter` sem alterar core.
6. Testável → regras financeiras isoladas de I/O, injetadas via `Depends`.

## 4. Escopo funcional MVP

- Auth: register, login, refresh, logout, recover, reset, change, me.
- Accounts: CRUD (corrente, poupança, cartão, carteira).
- Categories: CRUD + tipo `INCOME|EXPENSE`.
- Transactions: CRUD manual + listagem com filtros (período, categoria, conta, tipo, origem, valor, descrição) + export.
- Imports OFX: upload, processamento assíncrono, revisão, confirmação.
- RecurringBills: fixas/variáveis/únicas/recorrentes.
- Installments: gera parcelas futuras como compromissos.
- Dashboard: saldos, receitas/despesas por período, por categoria, evolução.

## 5. Requisitos não-funcionais

- `docker compose up -d` sobe tudo com healthchecks.
- p95 API < 300ms local sem carga; import OFX 5k linhas < 10s.
- Cobertura mínima: 80% backend core (auth, imports, dedup, parcelas).
- Valores monetários sempre `NUMERIC(14,2)` + `Decimal`, nunca float.
- Todos os endpoints (exceto auth públicos) exigem `Authorization: Bearer <access>`.
- Auditoria: `audit_logs` para importações e decisões de duplicidade.

## 6. Documentos do MVP

```
docs/SPEC-MVP.md  (este)
docs/ARCHITECTURE.md
docs/DATABASE.md
docs/API.md (+ backend/openapi.yaml)
docs/SECURITY.md
docs/OFX-IMPORT.md
docs/DEDUP.md
docs/FRONTEND.md
docs/TESTING.md
docs/BACKLOG.md
```

Infra executável: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `infrastructure/nginx/nginx.conf`, `.env.example`, `.github/workflows/*`.
