#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"
: "${SERVICE_NAME:=startup}"

sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "echo \"${SSH_PASS}\" | sudo -S systemctl restart ${SERVICE_NAME}"
