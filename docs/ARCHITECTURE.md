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
  main.py              — composição (D: wiring via Depends)
  core/{config,security,db,redis,errors}.py
  modules/
    auth/{router,service,tokens}.py
    users/{router,service,schemas}.py
    accounts/{router,service,repository}.py
    categories/{router,service,repository}.py
    transactions/{router,service,repository,schemas}.py
    imports/{router,service,ofx_parser,normalizer,duplicate_detector,repository}.py
    bills/{router,service}.py        — recurring_bills + installments
    dashboard/{router,service}.py
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

`frontend/src/{routes,features/{auth,dashboard,transactions,accounts,imports,bills},lib/api,components/ui}`.
Estado servidor via TanStack Query; estado auth via contexto + access em memória. Ver `FRONTEND.md`.

## 5. Decisões

- REST (não GraphQL/tRPC): contrato estável p/ app nativo futuro.
- Async SQLAlchemy: imports e dashboard concorrentes sem bloquear loop.
- Redis obrigatório: rate-limit auth + deny-list logout + fila de imports (evita timeout HTTP em OFX grande).
- Nginx na frente: um ponto p/ TLS, gzip, cache estático e headers.
