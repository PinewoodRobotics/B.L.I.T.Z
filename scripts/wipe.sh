#!/bin/bash

set -euo pipefail

: "${SERVICE_NAME:=startup}"

if [ -f /etc/default/blitz ]; then
    sudo rm -rf /etc/default/blitz
    printf '%s\n' "Deleted /etc/default/blitz"
els
    printf '%s\n' "/etc/default/blitz does not exist. Skipping deletion..."
fi

if [ -f /etc/profile.d/blitz.sh ]; then
    sudo rm -rf /etc/profile.d/blitz.sh
    printf '%s\n' "Deleted /etc/profile.d/blitz.sh"
else
    printf '%s\n' "/etc/profile.d/blitz.sh does not exist. Skipping deletion..."
fi

printf '%s\n' "Unlinked BLITZ_PATH and project from system..."

if [ -f /etc/systemd/system/${SERVICE_NAME}.service ]; then
    sudo systemctl stop ${SERVICE_NAME}
    sudo systemctl disable ${SERVICE_NAME}
    sudo rm -rf /etc/systemd/system/${SERVICE_NAME}.service
    sudo systemctl daemon-reload
    printf '%s\n' "Deleted /etc/systemd/system/${SERVICE_NAME}.service"
else
    printf '%s\n' "/etc/systemd/system/${SERVICE_NAME}.service does not exist. Skipping deletion..."
fi

if [ -n "${BLITZ_PATH:-}" ]; then
    sudo rm -rf "${BLITZ_PATH}"
    printf '%s\n' "Deleted ${BLITZ_PATH}"
else
    printf '%s\n' "BLITZ_PATH is not set. Skipping deletion..."
fi
