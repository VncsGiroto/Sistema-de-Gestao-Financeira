# ARCHITECTURE — FinanceWay MVP

## 1. Visão geral

```
Browser (React SPA)
  │ HTTPS
  ▼
Nginx (:80/:443)
 ├─ /            → estáticos do frontend (build Vite)
 └─ /api/*       → backend FastAPI (:8000)
                    ├─ PostgreSQL 16 (:5432)
                    ├─ Redis 7 (:6379) — refresh deny-list, rate-limit, fila import
                    └─ Storage (volume) — arquivos OFX originais
```

Compose: `web + api + db + redis + nginx`. Ver `docker-compose.yml`.

## 2. Módulos backend (S: uma razão para mudar cada)

```
backend/app/
  main.py              — composição (D: wiring via Depends; CORS via env)
  core/{config,db,redis_client,errors,models}.py
  modules/
    auth/{router,service,tokens,deps,repository,audit_models,recovery_models}.py
    users/{models,passwords,repository}.py
    finance/{router,repository,schemas,models}.py   — accounts, categories, transactions
    imports/{router,service,ofx_parser,normalizer,duplicate_detector,repository,schemas,models}.py
    bills/{router,repository,schemas,models,due_dates}.py        — recurring_bills
    installments/{router,repository,schemas,schedule,models}.py — cronograma mensal
    dashboard/{router,service,schemas,commitments}.py           — agregações + agenda
```

Regra: `router → service → repository`. Router não acessa DB direto. Service não importa FastAPI (testável puro). Repository só SQLAlchemy.

## 3. Camada de conectores (O+L+D)

```python
class NormalizedTx(BaseModel):  # formato interno §5
    date: date; description: str; amount: Decimal
    type: Literal["INCOME","EXPENSE"]; account_id: int
    source: str; external_id: str | None

class BaseImporter(ABC):  # I: interface fina
    source: str
    async def parse(self, raw: bytes) -> list[RawTx]: ...
    def normalize(self, raw: RawTx, account_id: int) -> NormalizedTx: ...

class BaseDuplicateDetector(ABC):
    def check(self, tx: NormalizedTx, existing: list[NormalizedTx]) -> DuplicateVerdict: ...
```

Fluxo (§4): `Upload → parse → normalize → validate → detect duplicates → stage import_items → human review → commit`.

MVP implementa `OfxImporter`. Pluggy/Belvo futuros só adicionam classes, sem alterar pipeline (**O**).

## 4. Frontend

`frontend/src/{routes,features/{auth,dashboard,finance,imports,bills,installments},lib,components}`.
Estado servidor via TanStack Query; auth via contexto + access em memória + refresh em cookie HttpOnly. Ver `FRONTEND.md`.

## 5. Decisões

- REST (não GraphQL/tRPC): contrato estável p/ app nativo futuro.
- Async SQLAlchemy: imports e dashboard concorrentes sem bloquear loop.
- Redis: rate-limit + deny-list por jti (fail-closed em `ENV=prod`). OFX processa em BackgroundTasks inline (worker separado só se o volume justificar).
- Nginx na frente: TLS, gzip, headers (HSTS/CSP), `limit_req` em login/recover.
- Tolerância a bancos: `normalize_headers()` antes do ofxparse (ex.: C6 com `UTF - 8`) + fallback com headers padrão.
