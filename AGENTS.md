# AGENTS.md — FinanceWay

## Docker (WSL + Desktop)
- O daemon `docker` do WSL costuma não existir; use `docker.exe` (Docker Desktop).
- Com `docker.exe`, traduza paths de volume com `wslpath -w` (`$PWD` do WSL ele não entende).
- Rede do compose: `financeway_app`. `docker compose up -d --build` roda `alembic upgrade head` no boot da API.
- Se a porta 8080 não responder com containers saudáveis, cheque `netsh interface portproxy show all` no Windows (regra stale já derrubou a porta uma vez).

## Backend (`backend/`, Python 3.13 + FastAPI)
- Ordem obrigatória (igual ao CI): `ruff check . && ruff format --check . && mypy app` — ruff `line-length = 120`, isort first-party `app`; lambdas curtas de erro HTTP com `# noqa` são o padrão (E731).
- Unit: `pytest -m "not integration"`. Integração exige `TEST_DATABASE_URL` + `TEST_REDIS_URL` (Postgres **com extensão `citext`**, senão `create_all` falha) e `pytest.ini` (`asyncio_mode = auto`).
- A imagem Docker **não embarca** `tests/` nem `pytest.ini` — monte via volume para rodar a suite no container.
- Dinheiro sempre `Decimal`/`NUMERIC(14,2)`, nunca float. Na API JSON, Decimals serializam como **strings** (testes comparam `"500.00"`, não `500.0`).
- Models SQLAlchemy devem espelhar as migrations (constraints, FKs, `__table_args__`): os testes usam `Base.metadata.create_all/drop_all`, e divergência quebra a ordem do drop.
- Alembic head atual: `0011_prices`. Nova tabela = nova migration + import do model em `alembic/env.py`.
- Refresh JWT rotativo com reuse-detection; logout usa deny-list no Redis. Login tem rate-limit 10/min/IP (`LOGIN_RATE_LIMIT`, CI usa 60).

## Frontend (`frontend/`, React 19 + Vite + TS)
- Ordem: `npm run lint && npm run typecheck && npm run test && npm run build`.
- Camada de API: `src/lib/api/*` + facade `api` em `client.ts` (não recriar `api-client.ts` — foi removido).
- UI usa o design system: classes `fw-*`, componentes `components/ui.tsx`, rótulos `lib/labels.ts`, moeda `lib/money.ts` (`brl()`).
- E2E: `npx playwright test` **com `workers: 1` (não alterar)** e compose no ar. A suite faz ~11 logins em ~30s: com limite default dá 429 — rode com `LOGIN_RATE_LIMIT=60` ou `redis-cli flushdb` + 60s de espera.

## Testes e dados
- Fixtures de integração fazem `drop_all` — **nunca** aponte `TEST_DATABASE_URL` para o banco de dev/prod.
- Testes externos são todos mockados (`httpx.MockTransport`, `monkeypatch`): BCB/brapi nunca são chamados em CI. Brapi foi removida do projeto — não reintroduzir; benchmarks vêm do BCB (CDI série 12, IPCA série 433).
- Commits em inglês, Conventional Commits; docs e UI em pt-BR.
- `.env` nunca é commitado (está no `.gitignore`); segredos só via ambiente.
