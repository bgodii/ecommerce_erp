#!/usr/bin/env bash
# Restaura o backup do banco UMA ÚNICA VEZ, na primeira subida.
# TRAVA DE SEGURANÇA: se já houver dados, aborta sem sobrescrever nada.
# Uso:  bash deploy/restore-once.sh /caminho/erp-backup.sql
set -euo pipefail

BACKUP="${1:?uso: bash deploy/restore-once.sh /caminho/erp-backup.sql}"
COMPOSE="docker compose --env-file .env.production -f docker-compose.prod.yml"

if [ ! -f "$BACKUP" ]; then
  echo "[restore] arquivo não encontrado: $BACKUP"; exit 1
fi

echo "[restore] subindo apenas o banco..."
$COMPOSE up -d db

echo "[restore] aguardando o Postgres ficar pronto..."
for _ in $(seq 1 30); do
  if $COMPOSE exec -T db pg_isready -U erp -d erp >/dev/null 2>&1; then break; fi
  sleep 1
done

# Já existe dado? (tabela users com linhas)
HAS_TABLE=$($COMPOSE exec -T db psql -U erp -d erp -tAc "SELECT to_regclass('public.users') IS NOT NULL" 2>/dev/null | tr -d '[:space:]' || echo f)
if [ "$HAS_TABLE" = "t" ]; then
  ROWS=$($COMPOSE exec -T db psql -U erp -d erp -tAc "SELECT count(*) FROM users" 2>/dev/null | tr -d '[:space:]' || echo 0)
  if [ "${ROWS:-0}" -gt 0 ]; then
    echo "[restore] ⚠ Já existem $ROWS usuário(s) no banco — ABORTANDO para não sobrescrever seus dados."
    echo "[restore] (Se você REALMENTE quer resetar, faça isso manualmente com cuidado.)"
    exit 0
  fi
fi

echo "[restore] banco vazio — restaurando de $BACKUP ..."
$COMPOSE exec -T db psql -U erp -d erp < "$BACKUP"
echo "[restore] OK. Agora suba o resto:  $COMPOSE up -d --build"
