# FinanceWay — Gestão Financeira Pessoal (MVP)

Stack: Python 3.13 + FastAPI · React 19 + Vite + TS · PostgreSQL 16 · Redis 7 · Nginx · Docker Compose · GitHub Actions.

## Como executar

```bash
cp .env.example .env
docker compose up -d --build
# app: http://localhost:8080
# api docs: http://localhost:8080/api/docs
```

## Docs

- `docs/SPEC-MVP.md` — escopo e stack travada
- `docs/ARCHITECTURE.md` — módulos e conectores (SOLID)
- `docs/DATABASE.md` — DDL + ER
- `docs/API.md` — endpoints
- `docs/SECURITY.md` — JWT access 15min + refresh 30d
- `docs/OFX-IMPORT.md` — pipeline
- `docs/DEDUP.md` — exato + fuzzy ±2d
- `docs/FRONTEND.md`, `docs/TESTING.md`, `docs/BACKLOG.md`

## Roadmap

MVP → Épicos 0-6 em `docs/BACKLOG.md`. Pós-MVP: agregadores, Open Finance, holerites, mobile nativo.
