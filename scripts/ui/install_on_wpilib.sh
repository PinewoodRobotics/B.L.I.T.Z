#!/bin/bash

set -euo pipefail

DEFAULT_SOURCE_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z/archive/HEAD.tar.gz"
DEFAULT_BACKEND_DIR="backend"
DEFAULT_DEPLOY_SCRIPT="deploy.py"
DEFAULT_GRADLE_TASK="deployBlitz"
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
    printf '\n%s\n' "${BOLD}B.L.I.T.Z WPILib Installer${RESET}"
    printf '%s\n\n' "${DIM}This will add BLITZ deployment files to a Java WPILib robot project.${RESET}"
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

read_menu_key() {
    local key
    local second
    local third

    IFS= read -rsn1 key || true
    if [ "${key}" = $'\x1b' ]; then
        IFS= read -rsn1 -t 0.5 second || true
        IFS= read -rsn1 -t 0.5 third || true
        key="${key}${second}${third}"
    fi

    printf '%s' "${key}"
}

select_menu() {
    local title="$1"
    shift
    local options=("$@")
    local selected=0
    local key
    local index

    while true; do
        clear_screen
        print_header
        printf '%s\n' "${BOLD}${title}${RESET}"
        printf '%s\n\n' "${DIM}Use arrow keys or j/k to move, then press Enter.${RESET}"

        for index in "${!options[@]}"; do
            if [ "${index}" -eq "${selected}" ]; then
                printf '  %s> %s%s\n' "${BLUE}${BOLD}" "${options[${index}]}" "${RESET}"
            else
                printf '    %s\n' "${options[${index}]}"
            fi
        done

        key="$(read_menu_key)"
        case "${key}" in
            "")
                selected_menu_index="${selected}"
                return
                ;;
            $'\x1b[A' | $'\x1bOA' | k | K)
                if [ "${selected}" -le 0 ]; then
                    selected=$((${#options[@]} - 1))
                else
                    selected=$((selected - 1))
                fi
                ;;
            $'\x1b[B' | $'\x1bOB' | j | J)
                selected=$(((selected + 1) % ${#options[@]}))
                ;;
            q | Q)
                selected_menu_index="$((${#options[@]} - 1))"
                return
                ;;
            [1-9])
                if [ "${key}" -le "${#options[@]}" ]; then
                    selected_menu_index="$((key - 1))"
                    return
                fi
                ;;
        esac
    done
}

absolute_path() {
    local path="$1"

    if [ -d "${path}" ]; then
        (cd "${path}" && pwd)
    else
        (cd "$(dirname "${path}")" && printf '%s/%s\n' "$(pwd)" "$(basename "${path}")")
    fi
}

is_wpilib_java_project() {
    local project_path="$1"

    [ -f "${project_path}/build.gradle" ] || return 1
    [ -f "${project_path}/settings.gradle" ] ||
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

local_source_root() {
    local source_path="${BASH_SOURCE[0]:-}"
    local script_dir
    local repo_root

    if [ -n "${source_path}" ] && [ -f "${source_path}" ]; then
        script_dir="$(cd "$(dirname "${source_path}")" && pwd)"
        repo_root="$(cd "${script_dir}/../.." && pwd)"
        if [ -d "${repo_root}/backend/deployment" ]; then
            printf '%s\n' "${repo_root}"
            return 0
        fi
    fi

    if [ -d "$(pwd)/backend/deployment" ]; then
        pwd
        return 0
    fi

    return 1
}

download_source_root() {
    local archive_path
    local source_root

    TEMP_DIR="$(mktemp -d)"
    trap cleanup EXIT
    archive_path="${TEMP_DIR}/blitz.tar.gz"

    info "Downloading BLITZ source..." >&2
    download_file "${BLITZ_SOURCE_URL}" "${archive_path}"
    require_command tar
    tar -xzf "${archive_path}" -C "${TEMP_DIR}"

    source_root="$(find "${TEMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    if [ -z "${source_root}" ] || [ ! -d "${source_root}/backend/deployment" ]; then
        error "Downloaded source does not contain backend/deployment."
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

    if local_source_root; then
        return
    fi

    download_source_root
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
                printf '%s\n' "Installation cancelled."
                exit 0
                ;;
        esac
    else
        prompt_text "Choose WPILib project" WPILIB_PROJECT "Project path" "$(pwd)" true
        WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
    fi
}

configure_basic_settings() {
    configure_project_path

    select_menu \
        "Install mode" \
        "Install / update BLITZ files" \
        "Update only" \
        "Cancel"
    case "${selected_menu_index}" in
        0)
            BLITZ_UPDATE_ONLY="false"
            ;;
        1)
            BLITZ_UPDATE_ONLY="true"
            ;;
        *)
            printf '%s\n' "Installation cancelled."
            exit 0
            ;;
    esac

    prompt_text "Backend folder" BLITZ_BACKEND_DIR "Backend folder" "${BLITZ_BACKEND_DIR:-${DEFAULT_BACKEND_DIR}}" false
    prompt_text "Deploy script" BLITZ_DEPLOY_SCRIPT "Deploy script" "${BLITZ_DEPLOY_SCRIPT:-${DEFAULT_DEPLOY_SCRIPT}}" false

    select_menu \
        "Gradle integration" \
        "Do not edit Gradle" \
        "Add ${BLITZ_GRADLE_TASK:-${DEFAULT_GRADLE_TASK}} task"
    case "${selected_menu_index}" in
        0)
            BLITZ_GRADLE_INTEGRATION="false"
            ;;
        1)
            BLITZ_GRADLE_INTEGRATION="true"
            prompt_text "Gradle task" BLITZ_GRADLE_TASK "Gradle task name" "${BLITZ_GRADLE_TASK:-${DEFAULT_GRADLE_TASK}}" false
            ;;
    esac
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

    BLITZ_BACKEND_DIR="${BLITZ_BACKEND_DIR:-${DEFAULT_BACKEND_DIR}}"
    BLITZ_DEPLOY_SCRIPT="${BLITZ_DEPLOY_SCRIPT:-${DEFAULT_DEPLOY_SCRIPT}}"
    BLITZ_GRADLE_INTEGRATION="${BLITZ_GRADLE_INTEGRATION:-false}"
    BLITZ_GRADLE_TASK="${BLITZ_GRADLE_TASK:-${DEFAULT_GRADLE_TASK}}"
    BLITZ_UPDATE_ONLY="${BLITZ_UPDATE_ONLY:-false}"
}

advanced_settings_menu() {
    while true; do
        select_menu \
            "Advanced settings" \
            "Edit BLITZ source URL" \
            "Edit backend folder" \
            "Edit deploy script" \
            "Back"

        case "${selected_menu_index}" in
            0)
                prompt_text "Advanced: BLITZ source" BLITZ_SOURCE_URL "Source URL" "${BLITZ_SOURCE_URL}" false
                ;;
            1)
                prompt_text "Advanced: backend folder" BLITZ_BACKEND_DIR "Backend folder" "${BLITZ_BACKEND_DIR}" false
                ;;
            2)
                prompt_text "Advanced: deploy script" BLITZ_DEPLOY_SCRIPT "Deploy script" "${BLITZ_DEPLOY_SCRIPT}" false
                ;;
            *)
                return
                ;;
        esac
    done
}

review_install_settings() {
    local gradle_label

    while true; do
        if [ "${BLITZ_GRADLE_INTEGRATION}" = "true" ]; then
            gradle_label="Add ${BLITZ_GRADLE_TASK}"
        else
            gradle_label="No Gradle edits"
        fi

        select_menu \
            "Review WPILib install settings" \
            "Start installation" \
            "Edit project path       ${WPILIB_PROJECT}" \
            "Edit backend folder     ${BLITZ_BACKEND_DIR}" \
            "Edit deploy script      ${BLITZ_DEPLOY_SCRIPT}" \
            "Edit Gradle setting     ${gradle_label}" \
            "Advanced settings" \
            "Cancel"

        case "${selected_menu_index}" in
            0)
                return
                ;;
            1)
                prompt_text "Edit project path" WPILIB_PROJECT "Project path" "${WPILIB_PROJECT}" true
                WPILIB_PROJECT="$(absolute_path "${WPILIB_PROJECT}")"
                ;;
            2)
                prompt_text "Edit backend folder" BLITZ_BACKEND_DIR "Backend folder" "${BLITZ_BACKEND_DIR}" false
                ;;
            3)
                prompt_text "Edit deploy script" BLITZ_DEPLOY_SCRIPT "Deploy script" "${BLITZ_DEPLOY_SCRIPT}" false
                ;;
            4)
                if [ "${BLITZ_GRADLE_INTEGRATION}" = "true" ]; then
                    BLITZ_GRADLE_INTEGRATION="false"
                else
                    BLITZ_GRADLE_INTEGRATION="true"
                    prompt_text "Gradle task" BLITZ_GRADLE_TASK "Gradle task name" "${BLITZ_GRADLE_TASK}" false
                fi
                ;;
            5)
                advanced_settings_menu
                ;;
            *)
                printf '%s\n' "Installation cancelled."
                exit 0
                ;;
        esac
    done
}

validate_settings() {
    if [ ! -d "${WPILIB_PROJECT}" ]; then
        error "Project path does not exist: ${WPILIB_PROJECT}"
        exit 1
    fi

    if ! is_wpilib_java_project "${WPILIB_PROJECT}"; then
        error "This does not look like a Java WPILib project: ${WPILIB_PROJECT}"
        printf '%s\n' "Expected build.gradle and src/main/java. Set BLITZ_ALLOW_NON_JAVA=true to override." >&2
        exit 1
    fi

    case "${BLITZ_BACKEND_DIR}" in
        "" | /* | *..* | *" "*)
            error "Backend folder must be a simple relative path without spaces: ${BLITZ_BACKEND_DIR}"
            exit 1
            ;;
    esac

    case "${BLITZ_DEPLOY_SCRIPT}" in
        "" | */* | *..* | *" "*)
            error "Deploy script must be a file name without spaces: ${BLITZ_DEPLOY_SCRIPT}"
            exit 1
            ;;
    esac

    case "${BLITZ_GRADLE_TASK}" in
        "" | *[!A-Za-z0-9_]*)
            error "Gradle task must contain only letters, numbers, and underscores: ${BLITZ_GRADLE_TASK}"
            exit 1
            ;;
    esac
}

write_deploy_template() {
    local deploy_path="$1"

    cat >"${deploy_path}" <<PY
from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.misc import output
from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import ProcessPlan, WeightedProcess


class ProcessType(WeightedProcess):
    # Example:
    # APRILTAG = "apriltag", 1.0
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        # .add(ProcessType.APRILTAG)
        # .pin(ProcessType.APRILTAG, "pi-name")
        .assign(pi_names)
    )


def get_modules() -> list[SupportedModules.Generic]:
    return [
        # SupportedModules.PythonModule(
        #     name="example",
        #     extra_run_args=[],
        #     equivalent_run_definition=ProcessType.APRILTAG,
        #     module_folder_path="${BLITZ_BACKEND_DIR}/python/example",
        # ),
    ]


if __name__ == "__main__":
    output.set_verbosity(False)

    config = (
        BlitzNetworkDeployer.Options()
        .set_local_backend_path("${BLITZ_BACKEND_DIR}")
        .should_bundle_dependencies(True)
        .set_discovery_timeout(2)
        .build()
    )

    BlitzNetworkDeployer.deploy(
        get_modules(),
        pi_name_to_process_types,
        config=config,
    )
PY
}

install_gradle_task() {
    local build_gradle="$1"
    local tmp_file

    tmp_file="$(mktemp)"
    awk '
        /^\/\/ BEGIN BLITZ DEPLOY TASK$/ { skipping = 1; next }
        /^\/\/ END BLITZ DEPLOY TASK$/ { skipping = 0; next }
        skipping != 1 { print }
    ' "${build_gradle}" >"${tmp_file}"

    cat >>"${tmp_file}" <<GRADLE

// BEGIN BLITZ DEPLOY TASK
tasks.register('${BLITZ_GRADLE_TASK}', Exec) {
    workingDir = projectDir
    commandLine 'python3', '${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}'
}
// END BLITZ DEPLOY TASK
GRADLE

    mv "${tmp_file}" "${build_gradle}"
}

install_files() {
    local source_root="$1"
    local backend_path="${WPILIB_PROJECT}/${BLITZ_BACKEND_DIR}"
    local deployment_path="${backend_path}/deployment"
    local deploy_path="${backend_path}/${BLITZ_DEPLOY_SCRIPT}"

    if [ "${BLITZ_UPDATE_ONLY}" = "true" ] && [ ! -d "${deployment_path}" ]; then
        error "Update only was selected, but ${deployment_path} does not exist."
        exit 1
    fi

    mkdir -p "${backend_path}"
    rm -rf "${deployment_path}"
    cp -R "${source_root}/backend/deployment" "${deployment_path}"
    find "${deployment_path}" \( -name "__pycache__" -o -name ".DS_Store" \) -prune -exec rm -rf {} +

    if [ ! -f "${backend_path}/__init__.py" ]; then
        : >"${backend_path}/__init__.py"
    fi

    if [ ! -f "${deploy_path}" ]; then
        write_deploy_template "${deploy_path}"
        info "Created ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}"
    else
        info "Kept existing ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}"
    fi

    if [ "${BLITZ_GRADLE_INTEGRATION}" = "true" ]; then
        install_gradle_task "${WPILIB_PROJECT}/build.gradle"
        info "Updated build.gradle with ${BLITZ_GRADLE_TASK}"
    fi
}

main() {
    local source_root

    print_header

    BLITZ_SOURCE_URL="${BLITZ_SOURCE_URL:-${DEFAULT_SOURCE_URL}}"
    BLITZ_BACKEND_DIR="${BLITZ_BACKEND_DIR:-${DEFAULT_BACKEND_DIR}}"
    BLITZ_DEPLOY_SCRIPT="${BLITZ_DEPLOY_SCRIPT:-${DEFAULT_DEPLOY_SCRIPT}}"
    BLITZ_GRADLE_TASK="${BLITZ_GRADLE_TASK:-${DEFAULT_GRADLE_TASK}}"

    if DISCOVERED_WPILIB_PROJECT="$(discover_wpilib_project)"; then
        :
    else
        DISCOVERED_WPILIB_PROJECT=""
    fi

    if [ "${BLITZ_ASSUME_YES:-false}" = "true" ] || [ ! -t 0 ]; then
        configure_non_interactive_settings
    else
        configure_basic_settings
        review_install_settings
    fi

    validate_settings
    source_root="$(resolve_source_root)"

    info "Installing BLITZ deployment files..."
    install_files "${source_root}"

    printf '\n%s\n' "${GREEN}BLITZ WPILib setup complete.${RESET}"
    printf '%s\n' "Edit ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}, then run it from your robot project."
}

main "$@"
