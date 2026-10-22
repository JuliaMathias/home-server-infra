#!/bin/bash
# Install a reviewed merged infrastructure revision; never start app services/timers.
set -euo pipefail
[[ $# == 1 && $1 =~ ^[0-9a-f]{40}$ ]] || { echo 'Supply one full merged infrastructure SHA' >&2; exit 2; }
revision=$1
repository=$(git rev-parse --show-toplevel)
git -C "$repository" merge-base --is-ancestor "$revision" origin/main
[[ $(git -C "$repository" remote get-url origin) == https://github.com/JuliaMathias/home-server-infra.git ]]
destination="/srv/lara/app-delivery/$revision"
[[ ! -e "$destination" ]]
mkdir -p /srv/lara/app-delivery
mkdir -m 755 "$destination"
git -C "$repository" archive "$revision" delivery/v1 systemd/lara-app-check@.service systemd/lara-app-check@.timer systemd/lara-app-backup@.service systemd/lara-app-backup@.timer | tar -x -C "$destination"
/usr/bin/python3 "$destination/delivery/v1/control.py" --help >/dev/null
printf 'Installed reviewed mechanism at %s; no timers enabled.\n' "$destination"
