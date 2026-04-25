#!/bin/bash

set -euo pipefail

: "${SERVICE_NAME:=startup}"
: "${SERVICE_UNIT_SOURCE:?SERVICE_UNIT_SOURCE is required}"
: "${SERVICE_UNIT_PATH:=/etc/systemd/system/${SERVICE_NAME}.service}"

sudo install -m 0644 "${SERVICE_UNIT_SOURCE}" "${SERVICE_UNIT_PATH}"

if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
    # real computer with systemd running
    sudo systemctl daemon-reload
    sudo systemctl enable "${SERVICE_NAME}"
    sudo systemctl restart "${SERVICE_NAME}"
else
    # This means docker is running
    sudo mkdir -p /etc/systemd/system/multi-user.target.wants
    sudo ln -sf "${SERVICE_UNIT_PATH}" \
        "/etc/systemd/system/multi-user.target.wants/${SERVICE_NAME}.service"
fi
