# OFX-IMPORT — fluxo de importação

## 1. Pipeline (status)

```
RECEIVED (upload salvo em volume, <10MB, .ofx/.qfx)
  → PROCESSING (worker lê Redis queue; parse OFX 1.x SGML / 2.x XML)
  → VALIDATED (normalizado + deduplicação executada, import_items preenchidos)
  → IMPORTED (após review + commit) | FAILED (erro + audit)
```

Assíncrono desde o dia 1: `POST` retorna `202` imediato; front faz polling em `GET /api/imports/{id}`.

## 2. Parse → Normalização (§5 doc inicial)

Extrair por `STMTTRN`: `FITID → external_id`, `DTPOSTED → date`, `TRNAMT → amount`, `MEMO/NAME → description`, sinal do `TRNAMT` → `type` (`INCOME` se >0 senão `EXPENSE`), com `amount = abs(TRNAMT)` (confirmável na revisão).

```json
{"date":"2026-09-22","description":"SUPERMERCADO XYZ","amount":250.50,"type":"EXPENSE","account_id":1,"source":"OFX","external_id":"202609220001"}
```

Regras: trim + UPPER descrição preservando original em `payload.raw`; `amount > 0`; data válida; `external_id` estável (`FITID` ou hash `date|amount|memo` se ausente).

## 3. Validação e idempotência

- Re-upload do mesmo arquivo → novo `import_id`, mas itens com `external_id` já importado caem em `EXACT_DUPLICATE` (não duplica).
- `commit` idempotente por `import_id` (segunda chamada retorna contadores sem reinserir).
- Arquivo original preservado em volume p/ auditoria; `file_path` nunca exposto publicamente.

## 4. Fluxo em etapas (UI)

Upload → Processamento (polling de status; ações bloqueadas até `VALIDATED`) → Resumo
(NEW/exatos/possíveis/inválidos/pendentes) → Duplicatas (item a item ou "manter/descartar
todas") → Confirmação (`Confirmar importação: N lançamentos · M descartadas`, bloqueado
enquanto houver pendência) → Categorização em massa pós-commit (lote via
`GET /transactions?import_id=`, `POST /transactions/categorize`; incompatíveis por tipo
são pulados e contados).

## 4. Erros

OFX malformado → `FAILED + error` legível; linha inválida isolada marca item `INVALID` sem abortar lote.
