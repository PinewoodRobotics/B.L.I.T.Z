#!/bin/bash

set -euo pipefail

: "${UBUNTU_TARGET:?UBUNTU_TARGET is required}"
: "${TARGET_USER:=ubuntu}"
: "${SSH_PASS:?SSH_PASS is required}"
: "${TARGET_PORT:=22}"
: "${TARGET_FOLDER:=/home/${TARGET_USER}/BLITZ}"
: "${TARGET_NAME:?TARGET_NAME is required}"
: "${SERVICE_NAME:=startup}"
: "${SERVICE_UNIT_PATH:=/etc/systemd/system/${SERVICE_NAME}.service}"

sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" \
    "echo \"${SSH_PASS}\" | sudo -S rm -rf \"${TARGET_FOLDER}\" && \
     echo \"${SSH_PASS}\" | sudo -S mkdir -p \"${TARGET_FOLDER}\" && \
     echo \"${SSH_PASS}\" | sudo -S chown -R \"${TARGET_USER}:${TARGET_USER}\" \"${TARGET_FOLDER}\""

sshpass -p "${SSH_PASS}" rsync -av --progress \
    --exclude-from=.gitignore \
    -e "ssh -p ${TARGET_PORT}" \
    ./ "${TARGET_USER}@${UBUNTU_TARGET}:${TARGET_FOLDER}"

sshpass -p "${SSH_PASS}" ssh -tt -p "${TARGET_PORT}" "${TARGET_USER}@${UBUNTU_TARGET}" "
    set -euo pipefail

    cd \"${TARGET_FOLDER}\"
    SUDO_PASS=\"${SSH_PASS}\" ./scripts/bootstrap/install_deps_ubuntu.sh

    if [ ! -d .venv ]; then
        python3 -m venv .venv
    fi

    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e .

    mkdir -p watchdog/generated
    .venv/bin/python -m grpc_tools.protoc -I=proto \
        --python_out=watchdog/generated \
        --pyi_out=watchdog/generated \
        proto/StateLogging.proto proto/PiStatus.proto

    mkdir -p system_data
    printf '%s\n' \"${TARGET_NAME}\" > system_data/name.txt

    echo \"${SSH_PASS}\" | sudo -S -v

    BLITZ_PATH=\"${TARGET_FOLDER}\" \
    SERVICE_NAME=\"${SERVICE_NAME}\" \
    SERVICE_UNIT_SOURCE=\"${TARGET_FOLDER}/ops/systemd/watchdog.service\" \
    SERVICE_UNIT_PATH=\"${SERVICE_UNIT_PATH}\" \
    ./scripts/bootstrap/install_service.sh
"
