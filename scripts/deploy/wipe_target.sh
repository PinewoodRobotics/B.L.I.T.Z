#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${SSH_PASS:?SSH_PASS is required}"

: "${TARGET_USER:=ubuntu}"
: "${TARGET_PORT:=22}"
: "${SERVICE_NAME:=startup}"

SSH_OPTIONS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

sshpass -p "${SSH_PASS}" ssh ${SSH_OPTIONS} -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "if [ -r /etc/default/blitz ]; then set -a; . /etc/default/blitz; set +a; fi; SERVICE_NAME=\"${SERVICE_NAME}\" bash \"\${BLITZ_PATH:?BLITZ_PATH is required}/scripts/wipe.sh\""
