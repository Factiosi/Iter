#!/usr/bin/env bash
# Apply CORP VPN runtime update (archive at ~/corpvpn-deploy.tar.gz).
set -euo pipefail

RUNTIME="/opt/corpvpn-runtime"
ARCHIVE="${1:-$HOME/corpvpn-deploy.tar.gz}"

if [[ ! -f "$ARCHIVE" ]]; then
  echo "Archive not found: $ARCHIVE" >&2
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
tar -xzf "$ARCHIVE" -C "$TMP"

install -m 0644 "$TMP/corpvpn_proxy.py" "$RUNTIME/corpvpn_proxy.py"
install -d -m 0755 "$RUNTIME/app/subscription"
install -m 0644 "$TMP/app/subscription/"*.py "$RUNTIME/app/subscription/"

systemctl daemon-reload
systemctl restart corpvpn-proxy.service
sleep 2
systemctl is-active --quiet corpvpn-proxy.service
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS -H "User-Agent: Happ/1.0" http://127.0.0.1:8080/CorpVpnSubscription1_ | head -c 200
echo ""
echo "CORP VPN deploy OK"
