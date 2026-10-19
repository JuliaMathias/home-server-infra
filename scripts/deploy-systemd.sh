#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SCRIPT_SOURCE="$REPO_ROOT/scripts/renew-certificate.sh"
SERVICE_SOURCE="$REPO_ROOT/systemd/cert-renew.service"
TIMER_SOURCE="$REPO_ROOT/systemd/cert-renew.timer"

echo "Validating certificate renewal configuration..."

bash -n "$SCRIPT_SOURCE"

if ! grep -qF \
    'ExecStart=/usr/local/sbin/lara-renew-cert' \
    "$SERVICE_SOURCE"; then
    echo "Unexpected certificate renewal service command." >&2
    exit 1
fi

echo "Installing certificate renewal configuration..."

sudo install -o root -g root -m 750 \
    "$SCRIPT_SOURCE" \
    /usr/local/sbin/lara-renew-cert

sudo install -o root -g root -m 644 \
    "$SERVICE_SOURCE" \
    /etc/systemd/system/lara-cert-renew.service

sudo install -o root -g root -m 644 \
    "$TIMER_SOURCE" \
    /etc/systemd/system/lara-cert-renew.timer

echo "Reloading systemd..."

sudo systemctl daemon-reload

echo "Enabling certificate renewal timer..."

sudo systemctl enable --now lara-cert-renew.timer

echo "Deployment completed successfully."
