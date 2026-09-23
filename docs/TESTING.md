# TESTING — estratégia

## 1. Pirâmide

- **Unit (pytest / Vitest):** normalização, `similarity`, `is_fuzzy`, cálculo parcelas (arredondamento: últimas parcelas absorvem centavos), categorização, validações Pydantic/Zod.
- **Integração (API+DB real via Compose):** register→login→refresh→logout; scoping cruzado (user A não vê B → 403/404); import OFX fixture → review → commit idempotente; dashboard agrega corretamente.
- **E2E (Playwright):** `cadastro → login → criar conta → importar OFX → revisar duplicata → ver dashboard`. Roda contra `docker compose` em CI.

## 2. Comandos

```bash
# backend (workdir backend/)
ruff check . && ruff format --check . && mypy app   # pyproject.toml
pytest -m "not integration"                          # unit, puro
TEST_DATABASE_URL=postgresql+asyncpg://finance:finance@localhost:5432/financeway \
TEST_REDIS_URL=redis://localhost:6379/0 pytest -m integration   # exige PG+Redis (compose)
# frontend (workdir frontend/)
npm run lint && npm run typecheck && npm run test && npm run build
npx playwright test   # exige compose no ar; workers:1 (rate-limit); E2E_BASE_URL
```

## 3. Fixtures

`backend/tests/fixtures/{minimo,duplicado,fuzzy,c6,invalido}.ofx` (`c6` = C6 anonimizado: `UTF - 8`, timezone, sem MEMO).
Int usa `drop_all/create_all` + `flushdb` no Redis — **nunca aponte `TEST_DATABASE_URL` p/ prod**.

## 4. Gates CI

PR bloqueado se lint/type/test falhar ou cobertura core <80%. E2E roda em `e2e.yml` após `tests.yml` verde.
