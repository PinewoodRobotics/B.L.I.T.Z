#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"
: "${TARGET_FOLDER:?TARGET_FOLDER is required}"
: "${TARGET_NAME:?TARGET_NAME is required}"

sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "echo \"${SSH_PASS}\" | sudo -S rm -rf \"${TARGET_FOLDER}\" && \
     echo \"${SSH_PASS}\" | sudo -S mkdir -p \"${TARGET_FOLDER}\""

sshpass -p "${SSH_PASS}" rsync -av --progress \
    --exclude-from=.gitignore \
    -e "ssh -p ${TARGET_PORT}" \
    ./ "${TARGET_USER}@${UBUNTU_TARGET}:${TARGET_FOLDER}"

sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "cd \"${TARGET_FOLDER}\" && make install-service NAME=\"${TARGET_NAME}\""
