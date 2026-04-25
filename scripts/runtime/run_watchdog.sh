#!/bin/bash

set -euo pipefail

: "${VENV_PYTHON:=./.venv/bin/python}"
: "${BLITZ_PATH:=$(BLITZ_PATH)}"

cd "${BLITZ_PATH}"

if [ ! -s "system_data/name.txt" ]; then
    echo "Error: system_data/name.txt is missing. Run 'make set-name NAME=<value>'."
    exit 1
fi

exec ${VENV_PYTHON} -u -m watchdog