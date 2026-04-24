#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"
: "${TARGET_FOLDER:=none}"

if [ "${TARGET_FOLDER}" == "none" ]; then
    TARGET_FOLDER="$(
        sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
            "if [ -r /etc/default/blitz ]; then
                set -a
                . /etc/default/blitz
                set +a
                printf '%s' \"\${BLITZ_PATH}\"
            else
                none
            fi"
    )"

    if [ "${TARGET_FOLDER}" == "none" ]; then
        echo "Failed to get target folder. There does not seem to be a BLITZ_PATH set on the backend system."
        exit 1
    fi
fi

sshpass -p "${SSH_PASS}" rsync -av --progress \
    --exclude-from=.gitignore \
    -e "ssh -p ${TARGET_PORT}" \
    ./ "${TARGET_USER}@${UBUNTU_TARGET}:${TARGET_FOLDER}"
