#!/usr/bin/env bash
# Executado na Oracle VM pelo GitHub Actions (via ssh 'bash -s').
# Atualiza o código e reconstrói os containers. NÃO toca nos seus dados:
# não roda restore, não roda seed, não usa `down -v` — o volume do Postgres persiste.
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/ecommerce_erp}"
cd "$PROJECT_DIR"

# Escolha do compose (HTTP padrão ou HTTPS) via arquivo local na VM (não versionado):
#   echo 'COMPOSE_FILE=docker-compose.https.yml' > .env.deploy
[ -f .env.deploy ] && set -a && . ./.env.deploy && set +a
COMPOSE="docker compose --env-file .env.production -f ${COMPOSE_FILE:-docker-compose.prod.yml}"

echo "[deploy] atualizando código (origin/main)..."
git fetch --all --prune
git reset --hard origin/main   # .env.production é gitignored -> não é tocado

echo "[deploy] build + up (sem resetar dados)..."
$COMPOSE up -d --build

echo "[deploy] limpando imagens antigas..."
docker image prune -f || true

echo "[deploy] concluído."
