#!/bin/bash

set -euo pipefail

: "${SERVICE_NAME:=startup}"
: "${SERVICE_UNIT_SOURCE:?SERVICE_UNIT_SOURCE is required}"
: "${SERVICE_UNIT_PATH:=/etc/systemd/system/${SERVICE_NAME}.service}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Repo root: Makefile passes BLITZ_PATH; otherwise infer from this script’s location
: "${BLITZ_PATH:=$(cd -- "${SCRIPT_DIR}/../.." && pwd)}"

if [ ! -f "${SERVICE_UNIT_SOURCE}" ]; then
    echo "Service unit not found: ${SERVICE_UNIT_SOURCE}"
    exit 1
fi

printf 'BLITZ_PATH=%s\n' "${BLITZ_PATH}" | sudo tee /etc/default/blitz >/dev/null
sudo tee /etc/profile.d/blitz.sh >/dev/null <<'PROFILE'
# Expose BLITZ_PATH in login / interactive shells (see /etc/default/blitz)
if [ -r /etc/default/blitz ]; then
  set -a
  # shellcheck source=/dev/null
  . /etc/default/blitz
  set +a
fi
PROFILE

sudo chmod 0644 /etc/default/blitz /etc/profile.d/blitz.sh

sudo install -m 0644 "${SERVICE_UNIT_SOURCE}" "${SERVICE_UNIT_PATH}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"
