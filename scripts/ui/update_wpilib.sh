#!/bin/bash

set -euo pipefail

DEFAULT_GIT_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z.git"
DEFAULT_UI_LIB_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/common/terminal_ui.sh"
DEFAULT_BUILD_VERSION_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/backend/deployment/.build-version"
DEFAULT_BIN_DIR="bin"
DEFAULT_LOCAL_SCRIPT="backend.sh"
UI_LIB_TEMP_DIR=""
CLONED_SOURCE_ROOT=""
DEPLOYMENT_PATH=""

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
        printf '%s\n' "Error: Install curl or wget, then run this updater again." >&2
        exit 1
    fi

    # shellcheck source=/dev/null
    . "${ui_lib_path}"
    rm -rf "${UI_LIB_TEMP_DIR}"
    UI_LIB_TEMP_DIR=""
}

source_terminal_ui

print_header() {
    printf '\n%s\n' "${BOLD}B.L.I.T.Z WPILib Updater${RESET}"
    printf '%s\n\n' "${DIM}This checks and refreshes BLITZ deployment files in a Java WPILib robot project.${RESET}"
}

cleanup() {
    if [ -n "${CLONED_SOURCE_ROOT}" ]; then
        rm -rf "${CLONED_SOURCE_ROOT}"
    fi
    if [ -n "${UI_LIB_TEMP_DIR}" ]; then
        rm -rf "${UI_LIB_TEMP_DIR}"
    fi
}

require_command() {
    local command_name="$1"

    if ! command -v "${command_name}" >/dev/null 2>&1; then
        error "Missing required command: ${command_name}"
        exit 1
    fi
}

absolute_path() {
    local path="$1"

    if [ -d "${path}" ]; then
        (cd "${path}" && pwd)
    else
        (cd "$(dirname "${path}")" && printf '%s/%s\n' "$(pwd)" "$(basename "${path}")")
    fi
}

relative_to_project() {
    local path="$1"

    case "${path}" in
        "${WPILIB_PROJECT}")
            printf '.\n'
            ;;
        "${WPILIB_PROJECT}"/*)
            printf '%s\n' "${path#"${WPILIB_PROJECT}/"}"
            ;;
        *)
            printf '%s\n' "${path}"
            ;;
    esac
}

is_wpilib_java_project() {
    local project_path="$1"

    [ -f "${project_path}/build.gradle" ] ||
        [ -f "${project_path}/build.gradle.kts" ] ||
        return 1
    [ -f "${project_path}/settings.gradle" ] ||
        [ -f "${project_path}/settings.gradle.kts" ] ||
        [ -f "${project_path}/gradlew" ] ||
        [ -d "${project_path}/.wpilib" ] ||
        [ -d "${project_path}/vendordeps" ] ||
        [ -d "${project_path}/src/main/java" ] ||
        return 1

    [ -d "${project_path}/src/main/java" ] ||
        [ "${BLITZ_ALLOW_NON_JAVA:-false}" = "true" ] ||
        return 1
}

discover_wpilib_project() {
    local current
    current="$(pwd)"

    while true; do
        if is_wpilib_java_project "${current}"; then
            printf '%s\n' "${current}"
            return 0
        fi

        if [ "${current}" = "/" ]; then
            return 1
        fi
        current="$(dirname "${current}")"
    done
}

configure_project_path() {
    local discovered_path="${DISCOVERED_WPILIB_PROJECT:-}"

    if [ -n "${WPILIB_PROJECT:-}" ]; then
        WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
        return
    fi

    if [ -n "${discovered_path}" ]; then
        select_menu \
            "WPILib project found: ${discovered_path}" \
            "Use this project" \
            "Choose a different path" \
            "Cancel"

        case "${selected_menu_index}" in
            0)
                WPILIB_PROJECT="${discovered_path}"
                ;;
            1)
                prompt_text "Choose WPILib project" WPILIB_PROJECT "Project path" "${discovered_path}" true
                WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
                ;;
            *)
                printf '%s\n' "Update cancelled."
                exit 0
                ;;
        esac
    else
        prompt_text "Choose WPILib project" WPILIB_PROJECT "Project path" "$(pwd)" true
        WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
    fi
}

configure_non_interactive_settings() {
    if [ -n "${WPILIB_PROJECT:-}" ]; then
        WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
    elif [ -n "${DISCOVERED_WPILIB_PROJECT:-}" ]; then
        WPILIB_PROJECT="${DISCOVERED_WPILIB_PROJECT}"
    else
        error "WPILIB_PROJECT is required when no Java WPILib project is discoverable."
        exit 1
    fi
}

validate_project() {
    if [ ! -d "${WPILIB_PROJECT}" ]; then
        error "Project path does not exist: ${WPILIB_PROJECT}"
        exit 1
    fi

    if ! is_wpilib_java_project "${WPILIB_PROJECT}"; then
        error "This does not look like a Java WPILib project: ${WPILIB_PROJECT}"
        printf '%s\n' "Expected build.gradle or build.gradle.kts and src/main/java. Set BLITZ_ALLOW_NON_JAVA=true to override." >&2
        exit 1
    fi

    case "${BLITZ_BIN_DIR}" in
        "" | /* | *..* | *" "*)
            error "Clone folder must be a simple relative path without spaces: ${BLITZ_BIN_DIR}"
            exit 1
            ;;
    esac
}

detect_deployment_path() {
    local preferred="${WPILIB_PROJECT}/backend/deployment"
    local version_file
    local candidate_count=0
    local first_candidate=""

    if [ -f "${preferred}/.build-version" ]; then
        DEPLOYMENT_PATH="${preferred}"
        return
    fi

    while IFS= read -r version_file; do
        candidate_count=$((candidate_count + 1))
        if [ -z "${first_candidate}" ]; then
            first_candidate="$(dirname "${version_file}")"
        fi
    done < <(
        find "${WPILIB_PROJECT}" \
            -path "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}" -prune -o \
            -path "*/deployment/.build-version" -type f -print
    )

    if [ "${candidate_count}" -eq 0 ]; then
        error "Could not find an installed BLITZ deployment folder in ${WPILIB_PROJECT}."
        printf '%s\n' "Run the WPILib installer before running the updater." >&2
        exit 1
    fi

    DEPLOYMENT_PATH="${first_candidate}"
    if [ "${candidate_count}" -gt 1 ]; then
        warn "Found multiple BLITZ deployment folders; using $(relative_to_project "${DEPLOYMENT_PATH}")."
    fi
}

detect_backend_and_deploy_script() {
    local backend_path
    local candidate

    backend_path="$(dirname "${DEPLOYMENT_PATH}")"
    BLITZ_BACKEND_DIR="$(relative_to_project "${backend_path}")"

    if [ -n "${BLITZ_DEPLOY_SCRIPT:-}" ] && [ -f "${backend_path}/${BLITZ_DEPLOY_SCRIPT}" ]; then
        return
    fi

    if [ -f "${backend_path}/deploy.py" ]; then
        BLITZ_DEPLOY_SCRIPT="deploy.py"
        return
    fi

    while IFS= read -r candidate; do
        if grep -Eq "BlitzNetworkDeployer|backend\.deployment" "${candidate}"; then
            BLITZ_DEPLOY_SCRIPT="$(basename "${candidate}")"
            return
        fi
    done < <(find "${backend_path}" -maxdepth 1 -type f -name "*.py" -print)

    BLITZ_DEPLOY_SCRIPT="deploy.py"
}

read_build_version() {
    local version_path="$1"

    if [ ! -f "${version_path}" ]; then
        error "Missing build version file: ${version_path}"
        exit 1
    fi

    sed -n '1{s/[[:space:]]*$//;p;q;}' "${version_path}"
}

fetch_url() {
    local url="$1"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${url}"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO - "${url}"
    else
        error "Install curl or wget, then run this updater again."
        exit 1
    fi
}

github_slug_from_git_url() {
    local git_url="$1"
    local slug=""

    case "${git_url}" in
        https://github.com/*)
            slug="${git_url#https://github.com/}"
            ;;
        git@github.com:*)
            slug="${git_url#git@github.com:}"
            ;;
        *)
            return 1
            ;;
    esac

    slug="${slug%.git}"
    slug="${slug%%/*}/${slug#*/}"
    if [ "${slug}" = "/" ] || [ -z "${slug%%/*}" ] || [ -z "${slug#*/}" ]; then
        return 1
    fi

    printf '%s\n' "${slug}"
}

build_version_url() {
    local slug

    if [ -n "${BLITZ_BUILD_VERSION_URL:-}" ]; then
        printf '%s\n' "${BLITZ_BUILD_VERSION_URL}"
        return
    fi

    if slug="$(github_slug_from_git_url "${GIT_URL}")"; then
        printf 'https://raw.githubusercontent.com/%s/HEAD/backend/deployment/.build-version\n' "${slug}"
        return
    fi

    printf '%s\n' "${DEFAULT_BUILD_VERSION_URL}"
}

fetch_latest_build_version() {
    if [ -n "${BLITZ_LATEST_BUILD_VERSION:-}" ]; then
        printf '%s\n' "${BLITZ_LATEST_BUILD_VERSION}"
        return
    fi

    if [ -n "${BLITZ_SOURCE_DIR:-}" ]; then
        read_build_version "${BLITZ_SOURCE_DIR}/backend/deployment/.build-version"
        return
    fi

    fetch_url "$(build_version_url)" | sed -n '1{s/[[:space:]]*$//;p;q;}'
}

fetch_github_commit_message() {
    local slug="$1"
    local api_url="https://api.github.com/repos/${slug}/commits/HEAD"

    if command -v python3 >/dev/null 2>&1; then
        fetch_url "${api_url}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["commit"]["message"].splitlines()[0])'
    else
        fetch_url "${api_url}" | sed -n 's/^[[:space:]]*"message":[[:space:]]*"\([^"]*\)".*/\1/p' | sed -n '1p'
    fi
}

fetch_latest_commit_message() {
    local slug

    if [ -n "${BLITZ_LATEST_COMMIT_MESSAGE:-}" ]; then
        printf '%s\n' "${BLITZ_LATEST_COMMIT_MESSAGE}"
        return
    fi

    if [ -n "${BLITZ_SOURCE_DIR:-}" ] &&
        command -v git >/dev/null 2>&1 &&
        git -C "${BLITZ_SOURCE_DIR}" rev-parse --git-dir >/dev/null 2>&1; then
        git -C "${BLITZ_SOURCE_DIR}" log -1 --pretty=%s 2>/dev/null || printf '%s\n' "Unknown latest commit"
        return
    fi

    if slug="$(github_slug_from_git_url "${GIT_URL}")"; then
        fetch_github_commit_message "${slug}" 2>/dev/null || printf '%s\n' "Unknown latest commit"
        return
    fi

    printf '%s\n' "Unknown latest commit"
}

confirm_update() {
    local current_version="$1"
    local latest_version="$2"
    local commit_message="$3"

    if [ "${BLITZ_ASSUME_YES:-false}" = "true" ]; then
        return 0
    fi

    if [ ! -t 0 ]; then
        error "Update available (${current_version} -> ${latest_version}), but confirmation is required in non-interactive mode."
        printf '%s\n' "Set BLITZ_ASSUME_YES=true to update automatically." >&2
        exit 1
    fi

    select_menu \
        "Update available: ${current_version} -> ${latest_version}. Latest commit: ${commit_message}" \
        "Update BLITZ deployment files" \
        "Skip update"

    [ "${selected_menu_index}" -eq 0 ]
}

clone_source_root() {
    local bin_path="${WPILIB_PROJECT}/${BLITZ_BIN_DIR}"
    local source_root

    require_command git

    mkdir -p "${bin_path}"
    rm -rf "${bin_path}/B.L.I.T.Z"
    source_root="${bin_path}/B.L.I.T.Z"

    info "Downloading BLITZ source..." >&2
    git clone --depth 1 --recurse-submodules "${GIT_URL}" "${source_root}"
    if [ ! -d "${source_root}/backend/deployment" ]; then
        error "Cloned source does not contain backend/deployment."
        printf '%s\n' "Source: ${GIT_URL}" >&2
        printf '%s\n' "Clone path: ${source_root}" >&2
        printf '%s\n' "Check that the selected BLITZ repository contains backend/deployment." >&2
        exit 1
    fi

    printf '%s\n' "${source_root}"
}

resolve_source_root() {
    if [ -n "${BLITZ_SOURCE_DIR:-}" ]; then
        if [ ! -d "${BLITZ_SOURCE_DIR}/backend/deployment" ]; then
            error "BLITZ_SOURCE_DIR must contain backend/deployment: ${BLITZ_SOURCE_DIR}"
            exit 1
        fi
        absolute_path "${BLITZ_SOURCE_DIR}"
        return
    fi

    clone_source_root
}

update_deployment_files() {
    local source_root="$1"
    local deploy_path="${WPILIB_PROJECT}/${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}"
    local scripts_path="${WPILIB_PROJECT}/scripts"
    local local_script_path="${scripts_path}/${DEFAULT_LOCAL_SCRIPT}"

    rm -rf "${DEPLOYMENT_PATH}"
    cp -R "${source_root}/backend/deployment" "${DEPLOYMENT_PATH}"
    find "${DEPLOYMENT_PATH}" \( -name "__pycache__" -o -name ".DS_Store" \) -prune -exec rm -rf {} +

    if [ -f "${source_root}/scripts/wpi-local/${DEFAULT_LOCAL_SCRIPT}" ]; then
        mkdir -p "${scripts_path}"
        cp "${source_root}/scripts/wpi-local/${DEFAULT_LOCAL_SCRIPT}" "${local_script_path}"
        chmod +x "${local_script_path}"
        info "Updated scripts/${DEFAULT_LOCAL_SCRIPT}"
    fi

    if [ -f "${deploy_path}" ]; then
        info "Kept existing ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}"
    else
        warn "Could not identify a deploy script to preserve; only $(relative_to_project "${DEPLOYMENT_PATH}") was refreshed."
    fi

    rm -rf "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}/B.L.I.T.Z"
    rmdir "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}" 2>/dev/null || true
    CLONED_SOURCE_ROOT=""
}

main() {
    local source_root
    local local_version
    local latest_version
    local commit_message

    print_header

    GIT_URL="${GIT_URL:-${DEFAULT_GIT_URL}}"
    BLITZ_BIN_DIR="${BLITZ_BIN_DIR:-${DEFAULT_BIN_DIR}}"

    if DISCOVERED_WPILIB_PROJECT="$(discover_wpilib_project)"; then
        :
    else
        DISCOVERED_WPILIB_PROJECT=""
    fi

    if [ "${BLITZ_ASSUME_YES:-false}" = "true" ] || [ ! -t 0 ]; then
        configure_non_interactive_settings
    else
        configure_project_path
    fi

    validate_project
    detect_deployment_path
    detect_backend_and_deploy_script

    local_version="$(read_build_version "${DEPLOYMENT_PATH}/.build-version")"
    latest_version="$(fetch_latest_build_version)"
    commit_message="$(fetch_latest_commit_message)"

    if [ "${local_version}" = "${latest_version}" ]; then
        printf '\n%s\n' "${GREEN}BLITZ WPILib deployment is already up to date (${local_version}).${RESET}"
        printf '%s\n' "Detected deployment folder: $(relative_to_project "${DEPLOYMENT_PATH}")"
        return
    fi

    printf '%s\n' "Detected deployment folder: $(relative_to_project "${DEPLOYMENT_PATH}")"
    printf '%s\n' "Detected deploy script:      ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}"
    printf '%s\n' "Current version:             ${local_version}"
    printf '%s\n' "Latest version:              ${latest_version}"
    printf '%s\n' "Latest commit:               ${commit_message}"

    if ! confirm_update "${local_version}" "${latest_version}" "${commit_message}"; then
        printf '%s\n' "Update skipped."
        return
    fi

    source_root="$(resolve_source_root)"
    if [ "${source_root}" = "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}/B.L.I.T.Z" ]; then
        CLONED_SOURCE_ROOT="${source_root}"
        trap cleanup EXIT
    fi

    info "Updating BLITZ deployment files..."
    update_deployment_files "${source_root}"

    printf '\n%s\n' "${GREEN}BLITZ WPILib deployment updated to ${latest_version}.${RESET}"
    printf '%s\n' "Your ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT} file was preserved."
}

if [ "${BLITZ_SOURCE_ONLY:-false}" != "true" ] && [ "${BLITZ_UI_SOURCE_ONLY:-false}" != "true" ]; then
    main "$@"
fi
