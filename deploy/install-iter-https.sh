#!/bin/bash
# Запускать на сервере с правами root:
#   sudo bash ~/iter-portal/deploy/install-iter-https.sh
#
# Делает: webroot для certbot, vhost в sites-available/iter.factiosi (server_name iter.factiosi.com) → 127.0.0.1:8010,
# выпускает сертификат Let's Encrypt, включает HTTPS.

set -euo pipefail

EMAIL="${CERTBOT_EMAIL:-factiosi@gmail.com}"
UPSTREAM="${ITER_UPSTREAM:-127.0.0.1:8010}"
WEBROOT="/var/www/certbot"
CONF="/etc/nginx/sites-available/iter.factiosi"

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Запустите: sudo bash $0"
  exit 1
fi

mkdir -p "$WEBROOT/.well-known/acme-challenge"
chown -R www-data:www-data "$WEBROOT"

# Фаза A: HTTP — сайт открывается по http, выпуск сертификата
cat >"$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name iter.factiosi.com;

    location /.well-known/acme-challenge/ {
        root $WEBROOT;
    }

    location / {
        proxy_pass http://$UPSTREAM;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf "$CONF" /etc/nginx/sites-enabled/iter.factiosi
nginx -t
systemctl reload nginx

echo "Фаза A: http://iter.factiosi.com/ должен открывать приложение (без редиректа на https)."

certbot certonly --webroot -w "$WEBROOT" -d iter.factiosi.com \
  --agree-tos --no-eff-email -m "$EMAIL" --non-interactive

# Фаза B: редирект HTTP→HTTPS и TLS
cat >"$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name iter.factiosi.com;

    location /.well-known/acme-challenge/ {
        root $WEBROOT;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name iter.factiosi.com;

    ssl_certificate /etc/letsencrypt/live/iter.factiosi.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iter.factiosi.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "upgrade-insecure-requests" always;

    location / {
        proxy_pass http://$UPSTREAM;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

nginx -t
systemctl reload nginx

echo "Готово: https://iter.factiosi.com/"
echo "Проверка обновления сертификата уже в таймере certbot (systemctl list-timers | grep certbot)."
