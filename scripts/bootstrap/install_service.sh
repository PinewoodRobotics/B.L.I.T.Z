#!/bin/bash

set -euo pipefail

: "${SERVICE_NAME:=startup}"
: "${SERVICE_UNIT_SOURCE:?SERVICE_UNIT_SOURCE is required}"
: "${SERVICE_UNIT_PATH:=/etc/systemd/system/${SERVICE_NAME}.service}"

sudo install -m 0644 "${SERVICE_UNIT_SOURCE}" "${SERVICE_UNIT_PATH}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"
