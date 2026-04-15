#!/usr/bin/env bash
# Install nginx site for peace-keeper.app and obtain Let's Encrypt HTTPS.
# Run from project root: sudo ./scripts/setup_peace_keeper_https.sh
#
# Prerequisites:
#   - DNS A records for @ and www point to this server's public IP
#   - Ports 80 and 443 reachable (ufw: allow 'Nginx Full' or 80/tcp + 443/tcp)
#   - NEON COMMAND frontend listening on 127.0.0.1:3900 (make start / make dev)

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts/peace-keeper.app.nginx"
DEST_AVAILABLE="/etc/nginx/sites-available/peace-keeper.app"
DEST_ENABLED="/etc/nginx/sites-enabled/peace-keeper.app"

if [ ! -f "$SRC" ]; then
  echo "Missing $SRC"
  exit 1
fi

echo "Installing nginx site..."
cp -f "$SRC" "$DEST_AVAILABLE"
ln -sf "$DEST_AVAILABLE" "$DEST_ENABLED"

echo "Testing nginx config..."
nginx -t

echo "Reloading nginx..."
systemctl reload nginx

echo ""
echo "Requesting TLS certificate (Let's Encrypt)..."
echo "You will be prompted for email (optional) and ToS agreement."
certbot --nginx \
  -d peace-keeper.app \
  -d www.peace-keeper.app \
  --redirect

echo ""
echo "Done. Open: https://peace-keeper.app"
echo "Renewal is handled by certbot timer (systemctl status certbot.timer)."
