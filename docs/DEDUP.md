# DEDUP — algoritmo de detecção de duplicidade

> Princípio: **nunca excluir/mergear automaticamente**. Sistema sugere, humano decide.

## 1. Nível 1 — Exato (bloqueia)

Se `transactions(user_id, source, external_id)` já existe → item `EXACT_DUPLICATE`, `commit` ignora por padrão. Decisão possível: `DISCARD_IMPORTED` (padrão) ou `KEEP_BOTH` (força insert com external_id sufixado — raro, auditado).

## 2. Nível 2 — Fuzzy (fila de revisão)

Candidatos: mesma `account_id`, `|date_diff| ≤ 2 dias` (configurável), `amount` igual no centavo, similaridade descrição ≥ 0.7.

Normalização descrição: UPPER, remove acentos/pontuação, colapsa espaços, remove `*1234`, `LTDA|SA|MEI`.

Similaridade: `token_set_ratio` (RapidFuzz) ou Jaccard trigram se lib indisponível. Score registrado em `payload.score`.

```python
def is_fuzzy(a, b, window_days=2) -> bool:
    return (a.account_id == b.account_id
        and abs((a.date - b.date).days) <= window_days
        and a.amount == b.amount
        and similarity(norm(a.description), norm(b.description)) >= 0.70)
```

## 3. UX revisão

`GET items?verdict=FUZZY_CANDIDATE` mostra lado a lado banco × importado. Ações: `[Manter ambos] [Descartar importado] [Revisar depois]`. `POST review` + `POST commit` só importa `NEW + KEEP_BOTH`. Tudo em `audit_logs`.

## 4. Testes obrigatórios

Fixtures: OFX com `FITID` repetido; mesmo valor/data descrição ligeiramente diferente (`IFOOD *1234` vs `IFOOD 5678`); salário `7850.00` ±1 dia; tolerância de janela configurável.
