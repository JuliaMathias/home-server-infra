#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="/srv/lara/infrastructure/caddy/certs"
COMPOSE_DIR="/srv/lara/infrastructure/caddy"
DOMAIN="lara.taila21247.ts.net"
CERT="$CERT_DIR/lara.crt"
KEY="$CERT_DIR/lara.key"

# Skip renewal when the certificate has at least 30 days left.
if openssl x509 -in "$CERT" \
    -checkend 2592000 -noout >/dev/null 2>&1; then
    echo "Certificate is valid for at least 30 more days."
    exit 0
fi

echo "Renewing certificate for $DOMAIN"

TMP_DIR=$(mktemp -d "$CERT_DIR/.renewal.XXXXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT

tailscale cert \
    --min-validity=720h \
    --cert-file "$TMP_DIR/lara.crt" \
    --key-file "$TMP_DIR/lara.key" \
    "$DOMAIN"

# Validate the new certificate and its hostname.
openssl x509 -in "$TMP_DIR/lara.crt" \
    -checkend 2592000 -noout

openssl x509 -in "$TMP_DIR/lara.crt" \
    -noout -checkhost "$DOMAIN"

# Verify that the certificate and private key match.
CERT_PUB=$(openssl x509 -in "$TMP_DIR/lara.crt" \
    -pubkey -noout | openssl pkey -pubin -outform DER \
    | sha256sum | awk '{print $1}')

KEY_PUB=$(openssl pkey -in "$TMP_DIR/lara.key" \
    -pubout -outform DER \
    | sha256sum | awk '{print $1}')

if [[ "$CERT_PUB" != "$KEY_PUB" ]]; then
    echo "ERROR: Certificate and private key do not match." >&2
    exit 1
fi

chmod 600 "$TMP_DIR/lara.crt" "$TMP_DIR/lara.key"

# Replace the existing files only after validation.
cp "$TMP_DIR/lara.crt" "$CERT"
cp "$TMP_DIR/lara.key" "$KEY"

docker compose \
    --project-directory "$COMPOSE_DIR" \
    exec -T caddy \
    caddy reload --config /etc/caddy/Caddyfile

echo "Certificate renewed and Caddy reloaded."
