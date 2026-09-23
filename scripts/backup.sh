#!/bin/sh
# Backup do Postgres via compose. Uso:
#   ./scripts/backup.sh [arquivo_saida]
# Restore:
#   cat backup.sql | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
set -e
cd "$(dirname "$0")/.."
OUT="${1:-backup-$(date +%Y%m%d-%H%M%S).sql}"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-finance}" "${POSTGRES_DB:-financeway}" > "$OUT"
echo "Backup salvo em $OUT"
