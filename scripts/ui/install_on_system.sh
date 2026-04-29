#!/bin/bash

set -euo pipefail

DEFAULT_GIT_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z.git"
DEFAULT_SETUP_SCRIPT_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/setup.sh"
DEFAULT_UI_LIB_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/common/terminal_ui.sh"
DEFAULT_TARGET_FOLDER="/opt/blitz/"
DEFAULT_SERVICE_NAME="startup"
TEMP_DIR=""
UI_LIB_TEMP_DIR=""

source_terminal_ui() {
    local source_path="${BASH_SOURCE[0]:-}"
    local script_dir
    local ui_lib_path

    if [ -n "${source_path}" ] && [ -f "${source_path}" ]; then
        script_dir="$(cd "$(dirname "${source_path}")" && pwd)"
        ui_lib_path="${script_dir}/common/terminal_ui.sh"
        if [ -f "${ui_lib_path}" ]; then
            # shellcheck source=/dev/null
            . "${ui_lib_path}"
            return
        fi
    fi

    UI_LIB_TEMP_DIR="$(mktemp -d)"
    ui_lib_path="${UI_LIB_TEMP_DIR}/terminal_ui.sh"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${BLITZ_UI_LIB_URL:-${DEFAULT_UI_LIB_URL}}" -o "${ui_lib_path}"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${ui_lib_path}" "${BLITZ_UI_LIB_URL:-${DEFAULT_UI_LIB_URL}}"
    else
        printf '%s\n' "Error: Install curl or wget, then run this installer again." >&2
        exit 1
    fi

    # shellcheck source=/dev/null
    . "${ui_lib_path}"
    rm -rf "${UI_LIB_TEMP_DIR}"
    UI_LIB_TEMP_DIR=""
}

source_terminal_ui

print_header() {
    printf '\n%s\n' "${BOLD}B.L.I.T.Z System Installer${RESET}"
    printf '%s\n\n' "${DIM}This will install BLITZ on this machine and register the watchdog service.${RESET}"
}

cleanup() {
    if [ -n "${TEMP_DIR}" ]; then
        rm -rf "${TEMP_DIR}"
    fi
    if [ -n "${UI_LIB_TEMP_DIR}" ]; then
        rm -rf "${UI_LIB_TEMP_DIR}"
    fi
}

verify_supported_system() {
    local kernel_name
    local kernel_release

    kernel_name="$(uname -s 2>/dev/null || printf 'unknown')"
    kernel_release="$(uname -r 2>/dev/null || printf 'unknown')"

    case "${kernel_name}" in
        Linux)
            case "${kernel_release}" in
                *[Mm]icrosoft* | *WSL*)
                    error "Windows/WSL is not supported by this installer."
                    printf '%s\n' "BLITZ setup expects a native Linux system with Linux paths, apt, sudo, and systemd." >&2
                    exit 1
                    ;;
            esac
            ;;
        Darwin)
            warn "macOS detected. This installer is intended for native Linux systems only."
            printf '%s\n' "BLITZ setup uses Linux paths, apt, sudo, and systemd, so it cannot safely install on macOS." >&2
            exit 1
            ;;
        CYGWIN* | MINGW* | MSYS*)
            error "Windows is not supported by this installer."
            printf '%s\n' "Run the installer on a native Linux system instead." >&2
            exit 1
            ;;
        *)
            error "Unsupported operating system: ${kernel_name}"
            printf '%s\n' "BLITZ setup is only supported on native Linux systems." >&2
            exit 1
            ;;
    esac
}

configure_basic_settings() {
    prompt_text "Step 1 of 3: Name this system" TARGET_NAME "System name" "${TARGET_NAME:-}" true
    prompt_text "Step 2 of 3: Choose install folder" TARGET_FOLDER "Install folder" "${TARGET_FOLDER:-${DEFAULT_TARGET_FOLDER}}" false
    prompt_text "Step 3 of 3: Choose service name" SERVICE_NAME "Systemd service name" "${SERVICE_NAME:-${DEFAULT_SERVICE_NAME}}" false
}

configure_non_interactive_settings() {
    : "${TARGET_NAME:?TARGET_NAME is required}"
    TARGET_FOLDER="${TARGET_FOLDER:-${DEFAULT_TARGET_FOLDER}}"
    SERVICE_NAME="${SERVICE_NAME:-${DEFAULT_SERVICE_NAME}}"
    GIT_URL="${GIT_URL:-${DEFAULT_GIT_URL}}"
    BLITZ_SETUP_SCRIPT_URL="${BLITZ_SETUP_SCRIPT_URL:-${DEFAULT_SETUP_SCRIPT_URL}}"
}

advanced_settings_menu() {
    while true; do
        select_menu \
            "Advanced settings" \
            "Edit Git repository URL" \
            "Edit setup.sh URL" \
            "Back"

        case "${selected_menu_index}" in
            0)
                prompt_text "Advanced: Git repository" GIT_URL "Git repository URL" "${GIT_URL}" false
                ;;
            1)
                prompt_text "Advanced: setup.sh source" BLITZ_SETUP_SCRIPT_URL "setup.sh URL" "${BLITZ_SETUP_SCRIPT_URL}" false
                ;;
            *)
                return
                ;;
        esac
    done
}

review_install_settings() {
    while true; do
        select_menu \
            "Review install settings" \
            "Start installation" \
            "Edit system name        ${TARGET_NAME}" \
            "Edit install folder     ${TARGET_FOLDER}" \
            "Edit service name       ${SERVICE_NAME}" \
            "Advanced settings" \
            "Cancel"

        case "${selected_menu_index}" in
            0)
                return
                ;;
            1)
                prompt_text "Edit system name" TARGET_NAME "System name" "${TARGET_NAME}" true
                ;;
            2)
                prompt_text "Edit install folder" TARGET_FOLDER "Install folder" "${TARGET_FOLDER}" false
                ;;
            3)
                prompt_text "Edit service name" SERVICE_NAME "Systemd service name" "${SERVICE_NAME}" false
                ;;
            4)
                advanced_settings_menu
                ;;
            *)
                printf '%s\n' "Installation cancelled."
                exit 0
                ;;
        esac
    done
}

require_command() {
    local command_name="$1"

    if ! command -v "${command_name}" >/dev/null 2>&1; then
        error "Missing required command: ${command_name}"
        exit 1
    fi
}

download_file() {
    local url="$1"
    local output="$2"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${url}" -o "${output}"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${output}" "${url}"
    else
        error "Install curl or wget, then run this installer again."
        exit 1
    fi
}

local_setup_script() {
    local source_path="${BASH_SOURCE[0]:-}"
    local script_dir

    if [ -n "${source_path}" ] && [ -f "${source_path}" ]; then
        script_dir="$(cd "$(dirname "${source_path}")" && pwd)"
        if [ -f "${script_dir}/../setup.sh" ]; then
            printf '%s\n' "${script_dir}/../setup.sh"
            return 0
        fi
    fi

    return 1
}

main() {
    local setup_script="${BLITZ_SETUP_SCRIPT:-}"

    print_header

    verify_supported_system

    if [ "${EUID}" -ne 0 ]; then
        require_command sudo
    fi

    GIT_URL="${GIT_URL:-${DEFAULT_GIT_URL}}"
    BLITZ_SETUP_SCRIPT_URL="${BLITZ_SETUP_SCRIPT_URL:-${DEFAULT_SETUP_SCRIPT_URL}}"

    if [ "${BLITZ_ASSUME_YES:-false}" = "true" ] || [ ! -t 0 ]; then
        configure_non_interactive_settings
    else
        configure_basic_settings
        review_install_settings
    fi

    if [ -n "${setup_script}" ]; then
        if [ ! -f "${setup_script}" ]; then
            error "BLITZ_SETUP_SCRIPT does not exist: ${setup_script}"
            exit 1
        fi
    elif setup_script="$(local_setup_script)"; then
        info "Using local setup script: ${setup_script}"
    else
        TEMP_DIR="$(mktemp -d)"
        trap cleanup EXIT
        setup_script="${TEMP_DIR}/setup.sh"
        info "Downloading setup script..."
        download_file "${BLITZ_SETUP_SCRIPT_URL}" "${setup_script}"
    fi

    chmod +x "${setup_script}"

    if [ "${EUID}" -eq 0 ]; then
        info "Starting BLITZ setup as root."
    else
        info "Starting BLITZ setup. You may be prompted for your sudo password."
    fi
    TARGET_NAME="${TARGET_NAME}" \
    TARGET_FOLDER="${TARGET_FOLDER}" \
    SERVICE_NAME="${SERVICE_NAME}" \
    GIT_URL="${GIT_URL}" \
    bash "${setup_script}"

    printf '\n%s\n' "${GREEN}BLITZ installation complete.${RESET}"
    printf '%s\n' "Open a new shell or run: source /etc/profile.d/blitz.sh"
}

if [ "${BLITZ_SOURCE_ONLY:-false}" != "true" ] && [ "${BLITZ_UI_SOURCE_ONLY:-false}" != "true" ]; then
    main "$@"
fi
