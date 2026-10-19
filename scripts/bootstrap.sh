#!/usr/bin/env bash
set -euo pipefail

SERVER_ROOT="/srv/lara"

echo "Bootstrapping home server infrastructure..."

# Verify required commands are available.
for command in docker install id; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Missing required command: $command" >&2
        exit 1
    fi
done

# Require execution as a regular user with sudo access.
if [[ "$EUID" -eq 0 ]]; then
    echo "Run this script as your regular user, not root." >&2
    exit 1
fi

OWNER="$USER"
GROUP="$(id -gn)"

# Create deployment directories.
directories=(
    "$SERVER_ROOT/infrastructure/caddy"
    "$SERVER_ROOT/infrastructure/postgres"
    "$SERVER_ROOT/ai/models"
    "$SERVER_ROOT/ai/data"
    "$SERVER_ROOT/ai/data/transcription"
    "$SERVER_ROOT/apps"
    "$SERVER_ROOT/backups"
)

for directory in "${directories[@]}"; do
    if [[ ! -d "$directory" ]]; then
        echo "Creating directory: $directory"

        sudo install -d \
            -m 750 \
            -o "$OWNER" \
            -g "$GROUP" \
            "$directory"
    else
        echo "Directory exists: $directory"
    fi
done

# Create shared Docker networks if they do not exist.
networks=(
    lara-proxy
    lara-backend
)

for network in "${networks[@]}"; do
    if sudo docker network inspect "$network" >/dev/null 2>&1; then
        echo "Docker network exists: $network"
    else
        echo "Creating Docker network: $network"
        sudo docker network create "$network"
    fi
done

echo "Bootstrap completed successfully."
