#!/bin/bash

set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui"
TEMP_SCRIPT=""

cleanup() {
    if [ -n "${TEMP_SCRIPT}" ]; then
        rm -f "${TEMP_SCRIPT}"
    fi
}
trap cleanup EXIT

choose_target() {
    if [ -n "${BLITZ_INSTALL_TARGET:-}" ]; then
        return
    fi

    if [ ! -t 0 ]; then
        printf '%s\n' "Set BLITZ_INSTALL_TARGET=coprocessor or development for non-interactive installation." >&2
        return 1
    fi

    printf '%s\n' \
        "Which part of BLITZ are you installing?" \
        "  1) Coprocessor" \
        "  2) Development computer (project backend)" \
        "  3) Cancel"
    read -r -p "Choose 1, 2, or 3: " choice
    case "${choice}" in
        1) BLITZ_INSTALL_TARGET="coprocessor" ;;
        2) BLITZ_INSTALL_TARGET="development" ;;
        3) printf '%s\n' "Installation cancelled."; exit 0 ;;
        *) printf 'Invalid selection: %s\n' "${choice}" >&2; return 1 ;;
    esac
}

selected_installer() {
    case "${BLITZ_INSTALL_TARGET}" in
        coprocessor | raspberrypi | system | pi)
            INSTALLER_NAME="install_on_system.sh"
            INSTALLER_URL="${BLITZ_SYSTEM_INSTALLER_URL:-${BASE_URL}/install_on_system.sh}"
            ;;
        development | backend)
            INSTALLER_NAME="install_backend.sh"
            INSTALLER_URL="${BLITZ_BACKEND_INSTALLER_URL:-${BASE_URL}/install_backend.sh}"
            ;;
        *)
            printf 'Unknown BLITZ_INSTALL_TARGET: %s\n' "${BLITZ_INSTALL_TARGET}" >&2
            return 1
            ;;
    esac
}

run_installer() {
    local script_dir=""

    if [ -n "${BLITZ_SOURCE_DIR:-}" ]; then
        script_dir="${BLITZ_SOURCE_DIR}/scripts/ui"
    elif [ -f "${BASH_SOURCE[0]:-}" ]; then
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    fi

    if [ -n "${script_dir}" ] && [ -f "${script_dir}/${INSTALLER_NAME}" ]; then
        bash "${script_dir}/${INSTALLER_NAME}" "$@"
        return
    fi

    TEMP_SCRIPT="$(mktemp)"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${INSTALLER_URL}" -o "${TEMP_SCRIPT}"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${TEMP_SCRIPT}" "${INSTALLER_URL}"
    else
        printf '%s\n' "Install curl or wget, then try again." >&2
        return 1
    fi
    bash "${TEMP_SCRIPT}" "$@"
}

main() {
    choose_target
    selected_installer
    run_installer "$@"
}

main "$@"
