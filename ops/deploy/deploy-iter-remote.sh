#!/usr/bin/env bash
# Серверная часть деплоя (если архив уже лежит в ~/iter-docker-upload.tar.gz).
# BUILD_SCOPE=full|api|web (по умолчанию full)
set -euo pipefail
cd ~/iter-portal
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p ~/iter-backups
cp -a apps/api/data/iter.db ~/iter-backups/iter.db."$TS"
tar -xzf ~/iter-docker-upload.tar.gz -C ~/iter-portal --overwrite
SCOPE="${BUILD_SCOPE:-full}"
case "$SCOPE" in
  api)
    docker compose build api
    docker compose up -d api
    ;;
  web)
    docker compose build web
    docker compose up -d web
    ;;
  *)
    docker compose build
    docker compose up -d
    ;;
esac
sleep 3
curl -fsS https://iter.factiosi.com/health
docker compose ps
rm -f ~/iter-docker-upload.tar.gz
echo "Deploy OK"
