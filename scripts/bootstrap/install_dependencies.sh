#!/bin/bash

set -euo pipefail

sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git \
    make \
    build-essential \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    sshpass \
    rsync \
    udev \
    thrift-compiler \
    protobuf-compiler
