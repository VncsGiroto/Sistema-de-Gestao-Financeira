# SECURITY — JWT access + refresh (travado)

## 1. Fluxo

```
register → hash Argon2 → users
login (rate-limit 10/min/IP) → access 15min + refresh 30d
  refresh = JWT opaco? Não: JWT assinado HS256 + cópia hash SHA256 em refresh_tokens
refresh → valida assinatura + consulta refresh_tokens (não revogado, não expirado)
         → ROTACIONA: revoga antigo, emite par novo (reuse-detection: se antigo reutilizado, revoga cadeia toda + audit)
logout → revoga refresh + põe access em deny-list Redis até expirar
recover → token único 1h via e-mail (log em dev) → reset troca senha + revoga todos refreshes
```

Access em memória no front (nunca em storage). Refresh em cookie `fw_refresh` com
`HttpOnly; SameSite=Lax; Path=/api/auth` (+ `Secure` atrás de HTTPS). O corpo JSON
ainda aceita/devolve o refresh (compat + testes), mas o front usa o cookie.

## 2. Controles obrigatórios

- Senhas: Argon2id, mínimo 8 chars; nunca logar.
- Scoping: todo query filtra `user_id = current_user.id`; teste `403` cruzado obrigatório.
- Headers Nginx: `HSTS, X-Content-Type-Options, X-Frame-Options DENY, Referrer-Policy, CSP básica`.
- Validação: Pydantic em tudo; CORS allowlist via env; `SQL Injection` mitigado por ORM + parâmetros.
- Rate-limit Redis: login/recover 10/min, refresh 30/min, OFX 10/hora/user.
  Nginx também limita `login/recover` (10r/m). Redis fora: **fail-closed em prod**
  (`ENV=prod` → 503/401), fail-open só em dev.
- Deny-list por `jti` do JWT (não por sufixo do token), TTL = `ACCESS_TTL`.
- Logs: `audit_logs` p/ login, refresh-reuse, import.commit, dedup.decide, bill.amount_changed. Sem PII além de user_id.
- Secrets: só via env/Secrets GHA; `.env` nunca commitado.
- HTTPS: obrigatório em staging/prod (Nginx termina TLS; `COOKIE_SECURE=true`).
- Backup: `./scripts/backup.sh` (pg_dump via compose); restore com `psql` (ver README).

## 3. Variáveis

`JWT_SECRET (32+ chars), JWT_ALG=HS256, ACCESS_TTL=900, REFRESH_TTL=2592000, REDIS_URL, DATABASE_URL,
ENV=dev|prod, CORS_ORIGINS (csv), COOKIE_SECURE=false|true`.
