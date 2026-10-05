# DATABASE — FinanceWay MVP (PostgreSQL 16)

## 1. Convenções

- PK `id BIGSERIAL`; FK com `ON DELETE RESTRICT` (exceto `import_items CASCADE` de `imports`); `created_at/updated_at TIMESTAMPTZ DEFAULT now()`.
- Dinheiro: `NUMERIC(14,2)` + `Decimal` no Python. Nunca float.
- Todo registro financeiro tem `user_id` (scoping obrigatório).

## 2. DDL

```sql
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(120) NOT NULL,
  bank VARCHAR(120),
  account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('CHECKING','SAVINGS','CASH','INVESTMENT','OTHER')),
  initial_balance NUMERIC(14,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(80) NOT NULL,
  type VARCHAR(10) NOT NULL CHECK (type IN ('INCOME','EXPENSE')),
  UNIQUE (user_id, name, type)
);

CREATE TABLE transactions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
  category_id BIGINT REFERENCES categories(id) ON DELETE SET NULL,
  date DATE NOT NULL,
  description TEXT NOT NULL,
  amount NUMERIC(14,2) NOT NULL,
  type VARCHAR(10) NOT NULL CHECK (type IN ('INCOME','EXPENSE')),
  source VARCHAR(20) NOT NULL DEFAULT 'MANUAL'
    CHECK (source IN ('MANUAL','OFX','IMPORT')),
  external_id VARCHAR(255),
  import_id BIGINT REFERENCES imports(id) ON DELETE SET NULL,   -- Épico 3 (migration 0005)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, source, external_id),
  CHECK (amount > 0)
);
CREATE INDEX ix_tx_user_date ON transactions (user_id, date DESC);
CREATE INDEX ix_tx_acct_date_amt ON transactions (account_id, date, amount);
CREATE INDEX ix_tx_category ON transactions (category_id);

CREATE TABLE ledger_movements (   -- migration 0014: ledger canônico patrimonial
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  from_account_id BIGINT REFERENCES accounts(id) ON DELETE RESTRICT,  -- NULL = fora da posição / interno
  to_account_id BIGINT REFERENCES accounts(id) ON DELETE RESTRICT,    -- NULL = para a posição / interno
  kind VARCHAR(20) NOT NULL CHECK (kind IN ('TRANSFER','APORTE','RESGATE','REINVESTIMENTO')),
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
  date DATE NOT NULL,
  description VARCHAR(500) NOT NULL DEFAULT 'Transferência',
  op_id BIGINT UNIQUE REFERENCES investment_ops(id) ON DELETE CASCADE, -- 1 movimento por operação
  asset_id BIGINT REFERENCES assets(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- TRANSFER: origem+destino, sem op. APORTE: conta→posição. RESGATE: posição→conta.
-- REINVESTIMENTO: interno. Nunca toca income/expense; saldos derivam daqui + transactions.

CREATE TABLE imports (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
  source VARCHAR(20) NOT NULL DEFAULT 'OFX',
  file_name VARCHAR(255) NOT NULL,
  file_path TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED'
    CHECK (status IN ('RECEIVED','PROCESSING','VALIDATED','IMPORTED','FAILED')),
  total_rows INT NOT NULL DEFAULT 0,
  imported_rows INT NOT NULL DEFAULT 0,
  duplicate_rows INT NOT NULL DEFAULT 0,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE TABLE import_items (
  id BIGSERIAL PRIMARY KEY,
  import_id BIGINT NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
  row_no INT NOT NULL,
  payload JSONB NOT NULL,               -- NormalizedTx
  verdict VARCHAR(20) NOT NULL DEFAULT 'NEW'
    CHECK (verdict IN ('NEW','EXACT_DUPLICATE','FUZZY_CANDIDATE','INVALID')),
  matched_transaction_id BIGINT REFERENCES transactions(id) ON DELETE SET NULL,
  decision VARCHAR(20) CHECK (decision IN ('KEEP_BOTH','DISCARD_IMPORTED','MERGED')),
  decided_at TIMESTAMPTZ
);

CREATE TABLE payables (   -- migration 0009: une recurring_bills + installments
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  description VARCHAR(200) NOT NULL,
  kind VARCHAR(20) NOT NULL CHECK (kind IN ('FIXED','RECURRING','INSTALLMENT','ONE_TIME')),
  amount NUMERIC(14,2),                    -- FIXED/RECURRING (fixo) / ONE_TIME
  periodicity VARCHAR(10),                 -- FIXED/RECURRING
  due_day INT,
  next_due DATE,                           -- FIXED/RECURRING (calculado) / ONE_TIME (informado)
  total_amount NUMERIC(14,2),              -- INSTALLMENT
  num_installments INT,
  installment_amount NUMERIC(14,2),        -- referência (truncada); exato via schedule
  first_due_date DATE,                     -- INSTALLMENT
  paid_ns JSONB NOT NULL DEFAULT '[]',     -- INSTALLMENT: nºs pagos
  paid_at TIMESTAMPTZ,                     -- ONE_TIME quitada
  account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,    -- INSTALLMENT/default da baixa
  category_id BIGINT REFERENCES categories(id) ON DELETE SET NULL, -- default da baixa
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- + ck_pay_shape (colunas obrigatórias por kind), ck_pay_due_day, ck_pay_num
);

-- transactions.payable_id BIGINT REFERENCES payables(id) ON DELETE SET NULL
-- transactions.source += 'PAYABLE' (baixas geram lançamentos rastreáveis)

CREATE TABLE refresh_tokens (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT UNIQUE NOT NULL,      -- SHA256 do refresh, nunca o token puro
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_user ON refresh_tokens (user_id);

CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action VARCHAR(80) NOT NULL,          -- import.commit, dedup.decide, auth.login...
  entity VARCHAR(40), entity_id BIGINT,
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> `CITEXT` exige `CREATE EXTENSION IF NOT EXISTS citext;` na migration 0001.

## 3. ER (resumo)

`users 1—N accounts, categories, transactions, imports, payables, assets, refresh_tokens, audit_logs · accounts 1—N transactions · imports 1—N import_items · payables 1—N transactions (via payable_id) · assets 1—N investment_ops + asset_prices`.

## 4. Migrations

Cadeia validada em banco fresco: `0001_auth_core → 0002_password_resets → 0003_accounts_categories → 0004_transactions → 0005_imports → 0006_recurring_bills → 0007_installments → 0008_installments_timestamps → 0009_payables → 0010_investments → 0011_prices → 0012_account_types → 0013_tx_amount_positive → 0014_ledger_movements → 0015_asset_account` (0009 migra bills/installments e dropa as tabelas; 0012 converte `CREDIT_CARD` legado para `OTHER` e troca o `CHECK` para `CHECKING/SAVINGS/CASH/INVESTMENT/OTHER`; 0013 normaliza `transactions.amount` legado via `abs()` e aperta o `CHECK` para `amount > 0`; 0014 cria `ledger_movements` (ledger patrimonial, sem dados a migrar); 0015 vincula `assets.account_id`, troca a unicidade para `(user, ticker, conta)`, adiciona kind `REINVESTIMENTO` e cria `portfolio_snapshots`; drift model×banco = zero).

Tabelas auxiliares: `password_resets` (recovery 1h, uso único) e `audit_logs(action,entity,entity_id,meta)`; `asset_prices(asset_id,date,price,source)` guarda histórico MANUAL/ACCRUAL (base do TWR).

Tabelas auxiliares: `password_resets` (recovery 1h, uso único) e `audit_logs(action,entity,entity_id,meta)`.

Sem seed automático (testes usam `drop_all/create_all`; dev cria via UI).
