#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"
: "${SERVICE_NAME:=startup}"

SSH_OPTIONS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

sshpass -p "${SSH_PASS}" ssh ${SSH_OPTIONS} -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "echo \"${SSH_PASS}\" | sudo -S systemctl restart \"${SERVICE_NAME}\""
