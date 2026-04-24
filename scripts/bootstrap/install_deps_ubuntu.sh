#!/bin/bash

set -euo pipefail

sudo_run() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif [ -n "${SUDO_PASS:-}" ]; then
        printf '%s\n' "${SUDO_PASS}" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

sudo_run apt-get update
sudo_run env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    protobuf-compiler thrift-compiler git make build-essential pkg-config rustup \
    python3 python3-dev python3-pip python3-venv python3-opencv libssl-dev libclang-dev \
    libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev libgl1-mesa-dev libglu1-mesa-dev \
    libx11-dev libxext-dev libxrender-dev libxrandr-dev libxi-dev libxcursor-dev libxinerama-dev libxss-dev \
    libatlas-base-dev gfortran libblas-dev liblapack-dev libboost-all-dev libtbb-dev sshpass rsync udev
