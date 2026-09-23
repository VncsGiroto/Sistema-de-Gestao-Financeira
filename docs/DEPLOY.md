# DEPLOY — staging

## Subir

```bash
cp .env.example .env   # preencha JWT_SECRET (32+), CORS_ORIGINS=https://staging.seu-dominio, COOKIE_SECURE=true
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build
curl -sf https://staging.seu-dominio/api/health
```

A API roda `alembic upgrade head` no boot (0001→0008). Confira `alembic_version`.

## TLS

O Nginx do repo serve HTTP; termine TLS à frente (proxy do provedor, Caddy/Traefik ou certbot no host)
e aponte para `NGINX_PORT`. Com HTTPS ativo, HSTS/CSP já saem configurados e `COOKIE_SECURE=true`
faz o navegador só enviar o refresh em conexão segura.

## Checklist

- [ ] `.env` sem valores de exemplo (`JWT_SECRET` forte, `POSTGRES_PASSWORD` forte)
- [ ] `ENV=prod` (Redis fail-closed) e `COOKIE_SECURE=true`
- [ ] `CORS_ORIGINS` só com o domínio real
- [ ] Backup testado: `./scripts/backup.sh` + restore numa base vazia
- [ ] `/api/docs` acessível (ou bloqueado no proxy, se preferir)
- [ ] Logs sem `FATAL` recorrente no db

## Produção

Mesmo compose de staging + TLS + backup agendado (cron chamando `backup.sh`) + monitoramento
do `/api/health`. Sem estado local além dos volumes `pgdata/redisdata/ofxdata`.
