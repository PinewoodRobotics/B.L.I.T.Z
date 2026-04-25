#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${SSH_PASS:?SSH_PASS is required}"

: "${TARGET_USER:=ubuntu}"
: "${TARGET_PORT:=22}"
: "${SERVICE_NAME:=startup}"

sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" "bash $(BLITZ_PATH)/scripts/wipe.sh SERVICE_NAME=\"${SERVICE_NAME}\" "