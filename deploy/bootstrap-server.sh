#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$HOME/iter-portal}"
API="$ROOT/api"
SK=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
PEPPER=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
mkdir -p "$API/data"
chmod -R u+rwX "$ROOT"
cd "$API"
if python3 -m venv .venv 2>/dev/null; then
  :
elif command -v virtualenv >/dev/null 2>&1; then
  virtualenv .venv
elif [ -x "$HOME/.local/bin/virtualenv" ]; then
  "$HOME/.local/bin/virtualenv" .venv
else
  python3 -m pip install --user virtualenv
  "$HOME/.local/bin/virtualenv" .venv
fi
. .venv/bin/activate
pip install -U pip -q
pip install -r requirements.txt -q
cat > .env << EOF
SECRET_KEY=$SK
OTP_PEPPER=$PEPPER
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080
ADMIN_EMAIL=factiosi@gmail.com
DATABASE_URL=sqlite:///./data/iter.db
FRONTEND_ORIGINS=https://iter.factiosi.com
PUBLIC_PORTAL_URL=https://iter.factiosi.com
STATIC_DIST_DIR=$ROOT/web/dist
SMTP_HOST=smtp.mail.ru
SMTP_PORT=465
SMTP_USE_TLS=true
SMTP_USER=noreply@factiosi.com
SMTP_PASSWORD=
SMTP_FROM=noreply@factiosi.com
SMTP_FROM_DISPLAY_AUTH=Authorization Iter.Factiosi
SMTP_FROM_DISPLAY_NOTIFICATION=Notification Iter.Factiosi
DEV_RELAXED_AUTH=false
INITIAL_WHITELIST_EMAILS=
EOF
chmod 600 .env
echo "Bootstrap OK: $API/.env (допишите SMTP_PASSWORD при необходимости)"
