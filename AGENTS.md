# AGENTS.md — FinanceWay

## Docker (WSL + Desktop)
- O daemon `docker` do WSL costuma não existir; use `docker.exe` (Docker Desktop).
- Com `docker.exe`, traduza paths de volume com `wslpath -w` (`$PWD` do WSL ele não entende).
- Rede do compose: `financeway_app`. `docker compose up -d --build` roda `alembic upgrade head` no boot da API.
- Porta padrão 8080 (`NGINX_PORT` no `.env`); se ocupada no host, faça override (ex. `8081`) **junto com `CORS_ORIGINS`**. Diagnóstico: `curl -sI localhost:PORTA` — se `Server:` não for nginx, a porta não é nossa; `docker port financeway-nginx-1` vazio = binding não aplicado (recreate com `compose down` + `up -d`, sem `-v`, que preserva os volumes).

## Backend (`backend/`, Python 3.13 + FastAPI)
- Ordem obrigatória (igual ao CI): `ruff check . && ruff format --check . && mypy app` — ruff `line-length = 120`, isort first-party `app`; lambdas curtas de erro HTTP com `# noqa` são o padrão (E731).
- A imagem **não embarca** `pyproject.toml` — sem ele o `ruff format --check` usa defaults (88 cols) e falha em tudo. Fazer `docker cp backend/pyproject.toml <api>:/code/pyproject.toml` antes dos gates no container.
- Unit: `pytest -m "not integration"`. Integração exige `TEST_DATABASE_URL` + `TEST_REDIS_URL` e `pytest.ini` (`asyncio_mode = auto`). Banco scratch novo precisa de `alembic upgrade head` antes da suite (é o que cria a extensão `citext`; sem ela o `create_all` falha).
- A imagem Docker **não embarca** `tests/` nem `pytest.ini` — monte via volume para rodar a suite no container.
- Dinheiro sempre `Decimal`/`NUMERIC(14,2)`, nunca float. Na API JSON, Decimals serializam como **strings** (testes comparam `"500.00"`, não `500.0`).
- `transactions.amount` sempre > 0 (`CHECK amount > 0`); o `type` (INCOME/EXPENSE) dá o sentido. Normalização OFX usa `abs()` e deriva o tipo do sinal.
- Categoria incompatível com o tipo da transação → 422 (create, PATCH por estado final, baixa de payable e rendimento).
- Models SQLAlchemy devem espelhar as migrations (constraints, FKs, `__table_args__`): os testes usam `Base.metadata.create_all/drop_all`, e divergência quebra a ordem do drop.
- Alembic head atual: `0013_tx_amount_positive`. Nova tabela = nova migration + import do model em `alembic/env.py`.
- Refresh JWT rotativo com reuse-detection; logout usa deny-list no Redis. Login tem rate-limit 10/min/IP (`LOGIN_RATE_LIMIT`, CI usa 60).

## Frontend (`frontend/`, React 19 + Vite + TS)
- Ordem: `npm run lint && npm run typecheck && npm run test && npm run build`.
- `node_modules/` é nativo do WSL — o `npm` do Windows não resolve os bins. Rodar os gates com `wsl npm --prefix <frontend> run <script>`.
- Camada de API: `src/lib/api/*` + facade `api` em `client.ts` (não recriar `api-client.ts` — foi removido).
- UI usa o design system: classes `fw-*`, componentes `components/ui.tsx`, rótulos `lib/labels.ts`, moeda `lib/money.ts` (`brl()`), datas `lib/date.ts` (`todayISO()`), marca `components/Logo.tsx` (`public/logo*.svg`).
- E2E: `npx playwright test` **com `workers: 1` (não alterar)** e compose no ar; `E2E_BASE_URL` sobrescreve o default `http://localhost:8080`. Se a porta do host estiver ocupada, rodar dentro da rede (`E2E_BASE_URL=http://nginx`) com `backend/` montado em `/backend` (a fixture OFX resolve `../../backend`). A suite faz ~11 logins em ~30s: com limite default dá 429 — rode com `LOGIN_RATE_LIMIT=60` ou `redis-cli flushdb` + 60s de espera.

## Testes e dados
- Fixtures de integração fazem `drop_all` — **nunca** aponte `TEST_DATABASE_URL` para o banco de dev/prod.
- Testes externos são todos mockados (`httpx.MockTransport`, `monkeypatch`): BCB/brapi nunca são chamados em CI. Brapi foi removida do projeto — não reintroduzir; benchmarks vêm do BCB (CDI série 12, IPCA série 433).
- Commits em inglês, Conventional Commits; docs e UI em pt-BR.
- `.env` nunca é commitado (está no `.gitignore`); segredos só via ambiente.
