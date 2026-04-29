#!/bin/bash

set -euo pipefail

DEFAULT_UPDATE_SCRIPT_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/update_wpilib.sh"
UPDATE_SCRIPT_TEMP_DIR=""
WPILIB_PROJECT=""
DEPLOYMENT_PATH=""
BLITZ_BACKEND_DIR=""
BLITZ_DEPLOY_SCRIPT=""

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

print_header() {
    printf '\n%s\n' "${BOLD}B.L.I.T.Z Backend${RESET}"
    printf '%s\n\n' "${DIM}Manage BLITZ backend settings and updates for this WPILib project.${RESET}"
}

clear_screen() {
    if command -v clear >/dev/null 2>&1; then
        clear
    else
        printf '\033[2J\033[H'
    fi
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

pause() {
    if [ -t 0 ]; then
        read -r -p "Press Enter to continue..." _
    fi
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

    if [ ! -t 0 ]; then
        selected_menu_index=0
        return
    fi

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
                IFS= read -rsn2 -t 1 rest || true
                case "${rest}" in
                    "[A" | "OA")
                        if [ "${selected}" -le 0 ]; then
                            selected=$((${#options[@]} - 1))
                        else
                            selected=$((selected - 1))
                        fi
                        ;;
                    "[B" | "OB")
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
            pause
            continue
        fi

        printf -v "${var_name}" '%s' "${value}"
        break
    done
}

cleanup() {
    if [ -n "${UPDATE_SCRIPT_TEMP_DIR}" ]; then
        rm -rf "${UPDATE_SCRIPT_TEMP_DIR}"
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

discover_wpilib_project_from() {
    local current="$1"

    current="$(absolute_path "${current}")"
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
    local source_path="${BASH_SOURCE[0]:-}"
    local script_dir=""
    local script_project=""
    local cwd_project=""

    if [ -n "${WPILIB_PROJECT:-}" ]; then
        WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
        return
    fi

    if [ -n "${source_path}" ] && [ -f "${source_path}" ]; then
        script_dir="$(cd "$(dirname "${source_path}")" && pwd)"
        if [ "$(basename "${script_dir}")" = "scripts" ] &&
            is_wpilib_java_project "$(dirname "${script_dir}")"; then
            script_project="$(dirname "${script_dir}")"
        elif script_project="$(discover_wpilib_project_from "${script_dir}")"; then
            :
        else
            script_project=""
        fi
    fi

    if cwd_project="$(discover_wpilib_project_from "$(pwd)")"; then
        :
    else
        cwd_project=""
    fi

    WPILIB_PROJECT="${cwd_project:-${script_project}}"
    if [ -z "${WPILIB_PROJECT}" ]; then
        error "Could not find a Java WPILib project from this directory."
        printf '%s\n' "Run this as scripts/backend.sh from the project root or backend.sh from the project scripts folder." >&2
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
        exit 1
    fi
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
            -path "${WPILIB_PROJECT}/bin" -prune -o \
            -path "*/deployment/.build-version" -type f -print
    )

    if [ "${candidate_count}" -eq 0 ]; then
        return 1
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

require_initialized_project() {
    if ! detect_deployment_path; then
        error "This WPILib project has not been initialized with BLITZ."
        printf '%s\n' "Run the BLITZ WPILib installer first." >&2
        exit 1
    fi
    detect_backend_and_deploy_script
}

gradle_settings_file() {
    if [ -f "${WPILIB_PROJECT}/settings.gradle.kts" ]; then
        printf '%s\n' "${WPILIB_PROJECT}/settings.gradle.kts"
    elif [ -f "${WPILIB_PROJECT}/settings.gradle" ]; then
        printf '%s\n' "${WPILIB_PROJECT}/settings.gradle"
    else
        error "Missing settings.gradle or settings.gradle.kts in ${WPILIB_PROJECT}"
        exit 1
    fi
}

gradle_build_file() {
    if [ -f "${WPILIB_PROJECT}/build.gradle.kts" ]; then
        printf '%s\n' "${WPILIB_PROJECT}/build.gradle.kts"
    elif [ -f "${WPILIB_PROJECT}/build.gradle" ]; then
        printf '%s\n' "${WPILIB_PROJECT}/build.gradle"
    else
        error "Missing build.gradle or build.gradle.kts in ${WPILIB_PROJECT}"
        exit 1
    fi
}

append_marked_block() {
    local target_file="$1"
    local start_marker="$2"
    local end_marker="$3"
    local tmp_file
    local block_file

    tmp_file="$(mktemp)"
    block_file="$(mktemp)"
    cat >"${block_file}"

    awk -v start="${start_marker}" -v end="${end_marker}" '
        $0 == start { skipping = 1; next }
        $0 == end { skipping = 0; next }
        skipping != 1 { print }
    ' "${target_file}" >"${tmp_file}"

    {
        cat "${tmp_file}"
        printf '\n%s\n' "${start_marker}"
        cat "${block_file}"
        printf '%s\n' "${end_marker}"
    } >"${target_file}"

    rm -f "${tmp_file}" "${block_file}"
}

install_gradle_integration() {
    local settings_file
    local build_file
    local gradle_script

    settings_file="$(gradle_settings_file)"
    build_file="$(gradle_build_file)"

    case "${settings_file}" in
        *.kts)
            append_marked_block "${settings_file}" "// BEGIN BLITZ BACKEND" "// END BLITZ BACKEND" <<KTS
// B.L.I.T.Z backend path used by the backend Gradle task script.
gradle.extra["backendPath"] = file("${BLITZ_BACKEND_DIR}").absolutePath
KTS
            ;;
        *)
            append_marked_block "${settings_file}" "// BEGIN BLITZ BACKEND" "// END BLITZ BACKEND" <<GRADLE
// B.L.I.T.Z backend path used by the backend Gradle task script.
gradle.ext.backendPath = file("${BLITZ_BACKEND_DIR}").absolutePath
GRADLE
            ;;
    esac

    case "${build_file}" in
        *.kts)
            gradle_script='build.gradle.kts'
            append_marked_block "${build_file}" "// BEGIN BLITZ BACKEND" "// END BLITZ BACKEND" <<KTS
// B.L.I.T.Z backend integration.
// This applies backend/deployment/gradle/${gradle_script}, which adds Gradle tasks
// for the Python backend deployment workflow, including deployBlitz.
// Gradle script plugin docs: https://docs.gradle.org/current/userguide/plugins.html#sec:script_plugins
apply(from = "\${gradle.extra["backendPath"]}/deployment/gradle/${gradle_script}")
KTS
            ;;
        *)
            gradle_script='build.gradle'
            append_marked_block "${build_file}" "// BEGIN BLITZ BACKEND" "// END BLITZ BACKEND" <<GRADLE
// B.L.I.T.Z backend integration.
// This applies backend/deployment/gradle/${gradle_script}, which adds Gradle tasks
// for the Python backend deployment workflow, including deployBlitz.
// Gradle script plugin docs: https://docs.gradle.org/current/userguide/plugins.html#sec:script_plugins
apply from: "\${gradle.ext.backendPath}/deployment/gradle/${gradle_script}"
GRADLE
            ;;
    esac
}

validate_backend_dir() {
    local backend_dir="$1"

    case "${backend_dir}" in
        "" | /* | *..* | *" "*)
            error "Backend folder must be a simple relative path without spaces: ${backend_dir}"
            exit 1
            ;;
    esac
}

update_deploy_py_backend_path() {
    local deploy_path="${WPILIB_PROJECT}/${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}"
    local new_backend_dir="$1"

    if [ ! -f "${deploy_path}" ] || ! command -v python3 >/dev/null 2>&1; then
        return
    fi

    python3 - "$deploy_path" "$new_backend_dir" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
new_backend_dir = sys.argv[2]
text = path.read_text()
updated = re.sub(
    r'(\.set_local_backend_path\()\s*(["\'])(.*?)(\2)\s*(\))',
    lambda match: f'{match.group(1)}{match.group(2)}{new_backend_dir}{match.group(4)}{match.group(5)}',
    text,
    count=1,
)
if updated != text:
    path.write_text(updated)
PY
}

change_backend_folder() {
    local old_backend_dir="${BLITZ_BACKEND_DIR}"
    local old_backend_path="${WPILIB_PROJECT}/${old_backend_dir}"
    local new_backend_dir="$1"
    local new_backend_path="${WPILIB_PROJECT}/${new_backend_dir}"

    validate_backend_dir "${new_backend_dir}"

    if [ "${new_backend_dir}" = "${old_backend_dir}" ]; then
        info "Backend folder is already ${new_backend_dir}."
        return
    fi

    if [ ! -d "${old_backend_path}" ]; then
        error "Current backend folder does not exist: ${old_backend_dir}"
        exit 1
    fi

    if [ -e "${new_backend_path}" ]; then
        error "Target backend folder already exists: ${new_backend_dir}"
        exit 1
    fi

    mkdir -p "$(dirname "${new_backend_path}")"
    mv "${old_backend_path}" "${new_backend_path}"
    BLITZ_BACKEND_DIR="${new_backend_dir}"
    DEPLOYMENT_PATH="${new_backend_path}/deployment"

    update_deploy_py_backend_path "${new_backend_dir}"
    install_gradle_integration

    info "Backend folder moved from ${old_backend_dir} to ${new_backend_dir}."
    info "Updated Gradle backend integration."
}

fetch_update_script() {
    local script_path

    UPDATE_SCRIPT_TEMP_DIR="$(mktemp -d)"
    script_path="${UPDATE_SCRIPT_TEMP_DIR}/update_wpilib.sh"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${BLITZ_UPDATE_SCRIPT_URL:-${DEFAULT_UPDATE_SCRIPT_URL}}" -o "${script_path}"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${script_path}" "${BLITZ_UPDATE_SCRIPT_URL:-${DEFAULT_UPDATE_SCRIPT_URL}}"
    else
        error "Install curl or wget, then try checking for updates again."
        exit 1
    fi

    printf '%s\n' "${script_path}"
}

check_updates() {
    local update_script

    update_script="$(fetch_update_script)"
    WPILIB_PROJECT="${WPILIB_PROJECT}" bash "${update_script}"
    cleanup
}

settings_menu() {
    local new_backend_dir

    while true; do
        select_menu \
            "Backend settings" \
            "Change backend folder    ${BLITZ_BACKEND_DIR}" \
            "Back"

        case "${selected_menu_index}" in
            0)
                new_backend_dir="${BLITZ_BACKEND_DIR}"
                prompt_text "Backend folder" new_backend_dir "Backend folder" "${BLITZ_BACKEND_DIR}" true
                change_backend_folder "${new_backend_dir}"
                pause
                ;;
            *)
                return
                ;;
        esac
    done
}

main_menu() {
    while true; do
        select_menu \
            "Detected BLITZ backend: ${BLITZ_BACKEND_DIR}" \
            "Check for updates" \
            "Settings" \
            "Exit"

        case "${selected_menu_index}" in
            0)
                check_updates
                pause
                require_initialized_project
                ;;
            1)
                settings_menu
                require_initialized_project
                ;;
            *)
                return
                ;;
        esac
    done
}

run_non_interactive_action() {
    case "${BLITZ_BACKEND_ACTION:-}" in
        check-updates)
            check_updates
            ;;
        set-backend-dir)
            if [ -z "${BLITZ_BACKEND_DIR_VALUE:-}" ]; then
                error "BLITZ_BACKEND_DIR_VALUE is required for set-backend-dir."
                exit 1
            fi
            change_backend_folder "${BLITZ_BACKEND_DIR_VALUE}"
            ;;
        "" | status)
            printf '%s\n' "WPILib project: ${WPILIB_PROJECT}"
            printf '%s\n' "Backend folder: ${BLITZ_BACKEND_DIR}"
            printf '%s\n' "Deployment:     $(relative_to_project "${DEPLOYMENT_PATH}")"
            printf '%s\n' "Deploy script:  ${BLITZ_DEPLOY_SCRIPT}"
            ;;
        *)
            error "Unknown BLITZ_BACKEND_ACTION: ${BLITZ_BACKEND_ACTION}"
            exit 1
            ;;
    esac
}

main() {
    trap cleanup EXIT

    configure_project_path
    validate_project
    require_initialized_project

    if [ ! -t 0 ] || [ -n "${BLITZ_BACKEND_ACTION:-}" ]; then
        run_non_interactive_action
        return
    fi

    main_menu
}

main "$@"
