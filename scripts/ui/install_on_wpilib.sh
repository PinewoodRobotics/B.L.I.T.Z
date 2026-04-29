#!/bin/bash

set -euo pipefail

DEFAULT_GIT_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z.git"
DEFAULT_UI_LIB_URL="https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/common/terminal_ui.sh"
DEFAULT_BACKEND_DIR="backend"
DEFAULT_BIN_DIR="bin"
DEFAULT_DEPLOY_SCRIPT="deploy.py"
UI_LIB_TEMP_DIR=""
CLONED_SOURCE_ROOT=""

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
    printf '\n%s\n' "${BOLD}B.L.I.T.Z WPILib Installer${RESET}"
    printf '%s\n\n' "${DIM}This will add BLITZ deployment files to a Java WPILib robot project.${RESET}"
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

clone_source_root() {
    local bin_path="${WPILIB_PROJECT}/${BLITZ_BIN_DIR}"
    local source_root

    require_command git

    mkdir -p "${bin_path}"
    rm -rf "${bin_path}/B.L.I.T.Z"
    source_root="${bin_path}/B.L.I.T.Z"

    info "Cloning BLITZ source..." >&2
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
    prompt_text "Clone folder" BLITZ_BIN_DIR "Clone folder" "${BLITZ_BIN_DIR:-${DEFAULT_BIN_DIR}}" false
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
    BLITZ_BIN_DIR="${BLITZ_BIN_DIR:-${DEFAULT_BIN_DIR}}"
    BLITZ_DEPLOY_SCRIPT="${BLITZ_DEPLOY_SCRIPT:-${DEFAULT_DEPLOY_SCRIPT}}"
    BLITZ_UPDATE_ONLY="${BLITZ_UPDATE_ONLY:-false}"
    GIT_URL="${GIT_URL:-${DEFAULT_GIT_URL}}"
}

advanced_settings_menu() {
    while true; do
        select_menu \
            "Advanced settings" \
            "Edit BLITZ Git URL" \
            "Edit backend folder" \
            "Edit clone folder" \
            "Edit deploy script" \
            "Back"

        case "${selected_menu_index}" in
            0)
                prompt_text "Advanced: BLITZ Git source" GIT_URL "Git URL" "${GIT_URL}" false
                ;;
            1)
                prompt_text "Advanced: backend folder" BLITZ_BACKEND_DIR "Backend folder" "${BLITZ_BACKEND_DIR}" false
                ;;
            2)
                prompt_text "Advanced: clone folder" BLITZ_BIN_DIR "Clone folder" "${BLITZ_BIN_DIR}" false
                ;;
            3)
                prompt_text "Advanced: deploy script" BLITZ_DEPLOY_SCRIPT "Deploy script" "${BLITZ_DEPLOY_SCRIPT}" false
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
            "Review WPILib install settings" \
            "Start installation" \
            "Edit project path       ${WPILIB_PROJECT}" \
            "Edit backend folder     ${BLITZ_BACKEND_DIR}" \
            "Edit deploy script      ${BLITZ_DEPLOY_SCRIPT}" \
            "Edit clone folder       ${BLITZ_BIN_DIR}" \
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
                prompt_text "Edit clone folder" BLITZ_BIN_DIR "Clone folder" "${BLITZ_BIN_DIR}" false
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

    case "${BLITZ_BIN_DIR}" in
        "" | /* | *..* | *" "*)
            error "Clone folder must be a simple relative path without spaces: ${BLITZ_BIN_DIR}"
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

    rm -rf "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}/B.L.I.T.Z"
    rmdir "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}" 2>/dev/null || true
    CLONED_SOURCE_ROOT=""
}

main() {
    local source_root

    print_header

    GIT_URL="${GIT_URL:-${DEFAULT_GIT_URL}}"
    BLITZ_BACKEND_DIR="${BLITZ_BACKEND_DIR:-${DEFAULT_BACKEND_DIR}}"
    BLITZ_BIN_DIR="${BLITZ_BIN_DIR:-${DEFAULT_BIN_DIR}}"
    BLITZ_DEPLOY_SCRIPT="${BLITZ_DEPLOY_SCRIPT:-${DEFAULT_DEPLOY_SCRIPT}}"

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
    if [ "${source_root}" = "${WPILIB_PROJECT}/${BLITZ_BIN_DIR}/B.L.I.T.Z" ]; then
        CLONED_SOURCE_ROOT="${source_root}"
        trap cleanup EXIT
    fi

    info "Installing BLITZ deployment files..."
    install_files "${source_root}"

    printf '\n%s\n' "${GREEN}BLITZ WPILib setup complete.${RESET}"
    printf '%s\n' "Edit ${BLITZ_BACKEND_DIR}/${BLITZ_DEPLOY_SCRIPT}, then run it from your robot project."
}

if [ "${BLITZ_SOURCE_ONLY:-false}" != "true" ] && [ "${BLITZ_UI_SOURCE_ONLY:-false}" != "true" ]; then
    main "$@"
fi
