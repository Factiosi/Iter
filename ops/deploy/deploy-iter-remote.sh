#!/usr/bin/env bash
# Серверная часть деплоя (если архив уже лежит в ~/iter-docker-upload.tar.gz).
set -euo pipefail
cd ~/iter-portal
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p ~/iter-backups
cp -a apps/api/data/iter.db ~/iter-backups/iter.db."$TS"
tar -xzf ~/iter-docker-upload.tar.gz -C ~/iter-portal --overwrite
docker compose build
docker compose up -d
sleep 3
curl -fsS https://iter.factiosi.com/health
docker compose ps
rm -f ~/iter-docker-upload.tar.gz
echo "Deploy OK"
