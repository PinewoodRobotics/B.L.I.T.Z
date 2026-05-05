#!/bin/bash

set -euo pipefail

: "${BLITZ_PATH:=$(pwd)}"

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_NAME:?TARGET_NAME is required}"

: "${TARGET_USER:=ubuntu}"
: "${TARGET_PORT:=22}"

: "${TARGET_FOLDER:=/opt/blitz/}"
: "${SERVICE_NAME:=startup}"

SSH_OPTIONS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

printf '%s\n' "Wiping target..."
sshpass -p "${SSH_PASS}" ssh ${SSH_OPTIONS} -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "if [ -r /etc/default/blitz ]; then set -a; . /etc/default/blitz; set +a; fi; WIPE_SCRIPT=\"\${BLITZ_PATH:-${TARGET_FOLDER%/}/B.L.I.T.Z}/scripts/wipe.sh\"; if [ -f \"\${WIPE_SCRIPT}\" ]; then SERVICE_NAME=\"${SERVICE_NAME}\" bash \"\${WIPE_SCRIPT}\"; else printf '%s\n' \"No existing BLITZ install found. Skipping wipe...\"; fi"

printf '%s\n' "Rsyncing setup.sh to target..."
sshpass -p "${SSH_PASS}" rsync -av --progress \
    --omit-dir-times \
    --no-perms \
    --no-owner \
    --no-group \
    -e "ssh ${SSH_OPTIONS} -p ${TARGET_PORT}" \
    "${BLITZ_PATH}/scripts/setup.sh" \
    "${TARGET_USER}@${UBUNTU_TARGET}:/tmp/setup.sh"

printf '%s\n' "Running setup.sh on target..."
sshpass -p "${SSH_PASS}" ssh ${SSH_OPTIONS} -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "TARGET_NAME=\"${TARGET_NAME}\" TARGET_FOLDER=\"${TARGET_FOLDER}\" SERVICE_NAME=\"${SERVICE_NAME}\" bash /tmp/setup.sh"
printf '%s\n' "Setup.sh completed..."
