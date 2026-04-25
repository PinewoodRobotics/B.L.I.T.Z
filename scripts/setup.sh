#!/bin/bash

set -euo pipefail

: "${TARGET_FOLDER:=$(pwd)}"
: "${GIT_URL:=https://github.com/PinewoodRobotics/B.L.I.T.Z.git}"
: "${SERVICE_NAME:=startup}"
: "${DEV_LOCAL_OVERRIDE:="false"}"

: "${TARGET_NAME:?TARGET_NAME is required}"

if [ ! -d "${TARGET_FOLDER}" ]; then
    mkdir -p "${TARGET_FOLDER}"
fi

sudo chmod 777 "${TARGET_FOLDER}"

cd "${TARGET_FOLDER}"
if [ "${DEV_LOCAL_OVERRIDE}" = "false" ]; then
    git clone "${GIT_URL}"
fi

cd "B.L.I.T.Z"

# ensure make is installed
if ! command -v make &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y make
fi

make setup NAME="${TARGET_NAME}"