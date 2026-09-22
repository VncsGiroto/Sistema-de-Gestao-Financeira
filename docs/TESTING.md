# TESTING — estratégia

## 1. Pirâmide

- **Unit (pytest / Vitest):** normalização, `similarity`, `is_fuzzy`, cálculo parcelas (arredondamento: últimas parcelas absorvem centavos), categorização, validações Pydantic/Zod.
- **Integração (API+DB real via Compose):** register→login→refresh→logout; scoping cruzado (user A não vê B → 403/404); import OFX fixture → review → commit idempotente; dashboard agrega corretamente.
- **E2E (Playwright):** `cadastro → login → criar conta → importar OFX → revisar duplicata → ver dashboard`. Roda contra `docker compose` em CI.

## 2. Comandos

```bash
# backend
pytest -m "not integration"          # unit
pytest -m integration                # precisa DATABASE_URL+REDIS_URL teste
ruff check . && ruff format --check . && mypy app
# frontend
npm run lint && npm run typecheck && npm run test && npx playwright test
```

## 3. Fixtures

`backend/tests/fixtures/{minimo.ofx, duplicado.ofx, fuzzy.ofx, invalido.ofx}` + massas `factories.py`. Front usa MSW p/ unit, API real p/ E2E.

## 4. Gates CI

PR bloqueado se lint/type/test falhar ou cobertura core <80%. E2E roda em `e2e.yml` após `tests.yml` verde.
