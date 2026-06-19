#!/usr/bin/env bash
# Server-side deploy (archive must be at ~/iter-docker-upload.tar.gz unless SKIP_EXTRACT=1).
# BUILD_SCOPE=full|api|web (default full)
set -euo pipefail
cd ~/iter-portal

if [[ "${SKIP_EXTRACT:-0}" != "1" ]]; then
  TS=$(date +%Y%m%d-%H%M%S)
  mkdir -p ~/iter-backups
  cp -a apps/api/data/iter.db ~/iter-backups/iter.db."$TS"
  tar -xzf ~/iter-docker-upload.tar.gz -C ~/iter-portal --overwrite
fi

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
