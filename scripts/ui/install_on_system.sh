#!/bin/bash

set -euo pipefail

DEFAULT_GIT_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z.git"
DEFAULT_SETUP_SCRIPT_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/setup.sh"
DEFAULT_TARGET_FOLDER="/opt/blitz/"
DEFAULT_SERVICE_NAME="startup"
TEMP_DIR=""

if [ -t 1 ]; then
    BOLD="$(printf '\033[1m')"
    DIM="$(printf '\033[2m')"
    GREEN="$(printf '\033[32m')"
    YELLOW="$(printf '\033[33m')"
    BLUE="$(printf '\033[34m')"
    RED="$(printf '\033[31m')"
    RESET="$(printf '\033[0m')"
else
    BOLD=""
    DIM=""
    GREEN=""
    YELLOW=""
    BLUE=""
    RED=""
    RESET=""
fi

clear_screen() {
    if command -v clear >/dev/null 2>&1; then
        clear
    else
        printf '\033[2J\033[H'
    fi
}

print_header() {
    printf '\n%s\n' "${BOLD}B.L.I.T.Z System Installer${RESET}"
    printf '%s\n\n' "${DIM}This will install BLITZ on this machine and register the watchdog service.${RESET}"
}

info() {
    printf '%s\n' "${GREEN}==>${RESET} $*"
}

warn() {
    printf '%s\n' "${YELLOW}Warning:${RESET} $*"
}

error() {
    printf '%s\n' "${RED}Error:${RESET} $*" >&2
}

cleanup() {
    if [ -n "${TEMP_DIR}" ]; then
        rm -rf "${TEMP_DIR}"
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

prompt_text() {
    local title="$1"
    local var_name="$2"
    local label="$3"
    local default_value="$4"
    local required="${5:-false}"
    local value
    local current_value="${!var_name:-${default_value}}"

    if [ ! -t 0 ]; then
        if [ "${required}" = "true" ] && [ -z "${current_value}" ]; then
            error "${var_name} is required in non-interactive mode."
            exit 1
        fi
        printf -v "${var_name}" '%s' "${current_value}"
        return
    fi

    while true; do
        clear_screen
        print_header
        printf '%s\n' "${BOLD}${title}${RESET}"
        printf '%s\n\n' "${DIM}Press Enter to accept the value in brackets.${RESET}"
        read -r -p "${label} [${current_value}]: " value
        value="${value:-${current_value}}"

        if [ "${required}" = "true" ] && [ -z "${value}" ]; then
            warn "This value is required."
            read -r -p "Press Enter to try again..." _
            continue
        fi

        printf -v "${var_name}" '%s' "${value}"
        break
    done
}

selected_menu_index=0

select_menu() {
    local title="$1"
    shift
    local options=("$@")
    local selected=0
    local key
    local rest
    local index

    while true; do
        clear_screen
        print_header
        printf '%s\n' "${BOLD}${title}${RESET}"
        printf '%s\n\n' "${DIM}Use arrow keys to move, then press Enter.${RESET}"

        for index in "${!options[@]}"; do
            if [ "${index}" -eq "${selected}" ]; then
                printf '  %s> %s%s\n' "${BLUE}${BOLD}" "${options[${index}]}" "${RESET}"
            else
                printf '    %s\n' "${options[${index}]}"
            fi
        done

        IFS= read -rsn1 key || true
        case "${key}" in
            "")
                selected_menu_index="${selected}"
                return
                ;;
            $'\x1b')
                IFS= read -rsn2 -t 0.1 rest || true
                case "${rest}" in
                    "[A")
                        if [ "${selected}" -le 0 ]; then
                            selected=$((${#options[@]} - 1))
                        else
                            selected=$((selected - 1))
                        fi
                        ;;
                    "[B")
                        selected=$(((selected + 1) % ${#options[@]}))
                        ;;
                esac
                ;;
            q | Q)
                selected_menu_index="$((${#options[@]} - 1))"
                return
                ;;
        esac
    done
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

main "$@"
