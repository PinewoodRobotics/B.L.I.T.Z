#!/bin/bash

set -euo pipefail

DEFAULT_GIT_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z.git"
DEFAULT_SETUP_SCRIPT_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/setup.sh"
DEFAULT_TARGET_FOLDER="/opt/blitz/"
DEFAULT_SERVICE_NAME="startup"

if [ -t 1 ]; then
    BOLD="$(printf '\033[1m')"
    DIM="$(printf '\033[2m')"
    GREEN="$(printf '\033[32m')"
    YELLOW="$(printf '\033[33m')"
    RED="$(printf '\033[31m')"
    RESET="$(printf '\033[0m')"
else
    BOLD=""
    DIM=""
    GREEN=""
    YELLOW=""
    RED=""
    RESET=""
fi

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

prompt_default() {
    local var_name="$1"
    local prompt="$2"
    local default_value="$3"
    local value

    if [ -n "${!var_name:-}" ]; then
        printf -v "${var_name}" '%s' "${!var_name}"
        return
    fi

    if [ ! -t 0 ]; then
        printf -v "${var_name}" '%s' "${default_value}"
        return
    fi

    read -r -p "${prompt} [${default_value}]: " value
    printf -v "${var_name}" '%s' "${value:-${default_value}}"
}

prompt_required() {
    local var_name="$1"
    local prompt="$2"
    local value

    if [ -n "${!var_name:-}" ]; then
        printf -v "${var_name}" '%s' "${!var_name}"
        return
    fi

    if [ ! -t 0 ]; then
        error "${var_name} is required in non-interactive mode."
        exit 1
    fi

    while [ -z "${value:-}" ]; do
        read -r -p "${prompt}: " value
        if [ -z "${value}" ]; then
            warn "Please enter a value."
        fi
    done

    printf -v "${var_name}" '%s' "${value}"
}

confirm_install() {
    local answer

    if [ "${BLITZ_ASSUME_YES:-false}" = "true" ] || [ ! -t 0 ]; then
        return
    fi

    printf '\n%s\n' "${BOLD}Install settings${RESET}"
    printf '  System name:    %s\n' "${TARGET_NAME}"
    printf '  Install folder: %s\n' "${TARGET_FOLDER}"
    printf '  Service name:   %s\n' "${SERVICE_NAME}"
    printf '  Git repository: %s\n' "${GIT_URL}"
    printf '\n'

    read -r -p "Continue with installation? [Y/n]: " answer
    case "${answer}" in
        "" | [Yy] | [Yy][Ee][Ss])
            ;;
        *)
            printf '%s\n' "Installation cancelled."
            exit 0
            ;;
    esac
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
    local temp_dir=""

    print_header

    verify_supported_system

    if [ "${EUID}" -eq 0 ]; then
        warn "Running as root is not recommended; setup commands use sudo where needed."
    else
        require_command sudo
    fi

    prompt_required TARGET_NAME "System name for this BLITZ install"
    prompt_default TARGET_FOLDER "Install folder" "${DEFAULT_TARGET_FOLDER}"
    prompt_default SERVICE_NAME "Systemd service name" "${DEFAULT_SERVICE_NAME}"
    prompt_default GIT_URL "Git repository URL" "${DEFAULT_GIT_URL}"
    prompt_default BLITZ_SETUP_SCRIPT_URL "setup.sh URL" "${DEFAULT_SETUP_SCRIPT_URL}"

    confirm_install

    if [ -n "${setup_script}" ]; then
        if [ ! -f "${setup_script}" ]; then
            error "BLITZ_SETUP_SCRIPT does not exist: ${setup_script}"
            exit 1
        fi
    elif setup_script="$(local_setup_script)"; then
        info "Using local setup script: ${setup_script}"
    else
        temp_dir="$(mktemp -d)"
        trap 'rm -rf "${temp_dir}"' EXIT
        setup_script="${temp_dir}/setup.sh"
        info "Downloading setup script..."
        download_file "${BLITZ_SETUP_SCRIPT_URL}" "${setup_script}"
    fi

    chmod +x "${setup_script}"

    info "Starting BLITZ setup. You may be prompted for your sudo password."
    TARGET_NAME="${TARGET_NAME}" \
    TARGET_FOLDER="${TARGET_FOLDER}" \
    SERVICE_NAME="${SERVICE_NAME}" \
    GIT_URL="${GIT_URL}" \
    bash "${setup_script}"

    printf '\n%s\n' "${GREEN}BLITZ installation complete.${RESET}"
    printf '%s\n' "Open a new shell or run: source /etc/profile.d/blitz.sh"
}

main "$@"
