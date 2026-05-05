#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"
: "${TARGET_NAME:?TARGET_NAME is required}"
: "${SERVICE_NAME:=startup}"

SSH_OPTIONS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

TARGET_FOLDER=$(sshpass -p "${SSH_PASS}" ssh ${SSH_OPTIONS} -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" 'if [ -r /etc/default/blitz ]; then . /etc/default/blitz; fi; printf "%s" "${BLITZ_PATH:-}"' | tr -d '\r')

if [ -z "${TARGET_FOLDER}" ]; then
    echo "Failed to get target folder. There does not seem to be a BLITZ_PATH set on the backend system."
    exit 1
fi

printf '%s\n' "Syncing target..."
sshpass -p "${SSH_PASS}" rsync -av --progress \
    --omit-dir-times \
    --no-perms \
    --no-owner \
    --no-group \
    --exclude-from=.gitignore \
    -e "ssh ${SSH_OPTIONS} -p ${TARGET_PORT}" \
    ./ "${TARGET_USER}@${UBUNTU_TARGET}:${TARGET_FOLDER}"
printf '%s\n' "Sync completed..."

printf '%s\n' "Running setup.sh on target..."
sshpass -p "${SSH_PASS}" ssh ${SSH_OPTIONS} -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "TARGET_NAME=\"${TARGET_NAME}\" TARGET_FOLDER=\"$(dirname "${TARGET_FOLDER}")/\" SERVICE_NAME=\"${SERVICE_NAME}\" DEV_LOCAL_OVERRIDE=true bash \"${TARGET_FOLDER}/scripts/setup.sh\""
printf '%s\n' "Setup.sh completed..."
