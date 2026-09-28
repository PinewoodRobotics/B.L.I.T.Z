#!/bin/bash

set -euo pipefail

# Keep the old entry point working for installed WPILib projects.
if [ -n "${BLITZ_SOURCE_DIR:-}" ] &&
    [ -f "${BLITZ_SOURCE_DIR}/scripts/ui/update_backend.sh" ]; then
    exec bash "${BLITZ_SOURCE_DIR}/scripts/ui/update_backend.sh" "$@"
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${script_dir}/update_backend.sh" ]; then
    exec bash "${script_dir}/update_backend.sh" "$@"
fi

temp_script="$(mktemp)"
trap 'rm -f "${temp_script}"' EXIT
url="${BLITZ_BACKEND_UPDATE_URL:-https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/update_backend.sh}"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${temp_script}"
else
    wget -qO "${temp_script}" "${url}"
fi
bash "${temp_script}" "$@"
