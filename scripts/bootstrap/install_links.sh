#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Repo root: Makefile passes BLITZ_PATH; otherwise infer from this script’s location
: "${BLITZ_PATH:=$(cd -- "${SCRIPT_DIR}/../.." && pwd)}"

printf 'BLITZ_PATH=%s\n' "${BLITZ_PATH}" | sudo tee /etc/default/blitz >/dev/null
sudo tee /etc/profile.d/blitz.sh >/dev/null <<'PROFILE'
# Expose BLITZ_PATH in login / interactive shells (see /etc/default/blitz)
if [ -r /etc/default/blitz ]; then
  set -a
  # shellcheck source=/dev/null
  . /etc/default/blitz
  set +a
fi
PROFILE

sudo chmod 0644 /etc/default/blitz /etc/profile.d/blitz.sh

# links the BLITZ_PATH to the /etc/default/blitz file, essentially making it an env variable
