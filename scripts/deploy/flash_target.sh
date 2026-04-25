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

printf '%s\n' "Wiping target..."
sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" "bash $(BLITZ_PATH)/scripts/wipe.sh"

printf '%s\n' "Rsyncing setup.sh to target..."
sshpass -p "${SSH_PASS}" rsync -av --progress \
    -e "ssh -p ${TARGET_PORT}" \
    "${BLITZ_PATH}/scripts/setup.sh" \
    "${TARGET_USER}@${UBUNTU_TARGET}:/tmp/setup.sh"

printf '%s\n' "Running setup.sh on target..."
sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" "bash /tmp/setup.sh TARGET_NAME=\"${TARGET_NAME}\" TARGET_FOLDER=\"${TARGET_FOLDER}\" SERVICE_NAME=\"${SERVICE_NAME}\""
printf '%s\n' "Setup.sh completed..."
