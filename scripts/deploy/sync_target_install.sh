#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"

TARGET_FOLDER=$(sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" 'echo "${BLITZ_PATH}"')

if [ -z "${TARGET_FOLDER}" ]; then
    echo "Failed to get target folder. There does not seem to be a BLITZ_PATH set on the backend system."
    exit 1
fi

printf '%s\n' "Syncing target..."
sshpass -p "${SSH_PASS}" rsync -av --progress \
    --exclude-from=.gitignore \
    -e "ssh -p ${TARGET_PORT}" \
    ./ "${TARGET_USER}@${UBUNTU_TARGET}:${TARGET_FOLDER}"
printf '%s\n' "Sync completed..."

printf '%s\n' "Running setup.sh on target..."
sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" "bash ${TARGET_FOLDER}/scripts/setup.sh"
printf '%s\n' "Setup.sh completed..."