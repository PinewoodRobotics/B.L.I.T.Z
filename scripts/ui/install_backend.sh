#!/bin/bash

set -euo pipefail

DEFAULT_GIT_URL="https://github.com/PinewoodRobotics/B.L.I.T.Z.git"
SOURCE_TEMP_DIR=""
SOURCE_ROOT=""

cleanup() {
    if [ -n "${SOURCE_TEMP_DIR}" ]; then
        rm -rf "${SOURCE_TEMP_DIR}"
    fi
}
trap cleanup EXIT

error() {
    printf 'Error: %s\n' "$*" >&2
}

source_root() {
    if [ -n "${BLITZ_SOURCE_DIR:-}" ]; then
        [ -f "${BLITZ_SOURCE_DIR}/backend/deployment/.blitz-build-version" ] || {
            error "BLITZ_SOURCE_DIR does not contain a BLITZ backend: ${BLITZ_SOURCE_DIR}"
            return 1
        }
        SOURCE_ROOT="$(cd "${BLITZ_SOURCE_DIR}" && pwd)"
        return
    fi

    SOURCE_TEMP_DIR="$(mktemp -d)"
    git clone --depth 1 --recurse-submodules \
        "${GIT_URL:-${DEFAULT_GIT_URL}}" "${SOURCE_TEMP_DIR}/B.L.I.T.Z" >&2
    SOURCE_ROOT="${SOURCE_TEMP_DIR}/B.L.I.T.Z"
}

detect_backend_dir() {
    local stamp
    local deployment_path=""
    local candidate

    while IFS= read -r stamp; do
        candidate="$(dirname "${stamp}")"
        if [ -n "${deployment_path}" ] && [ "${candidate}" != "${deployment_path}" ]; then
            error "Multiple BLITZ backend stamps found in ${BLITZ_PROJECT}."
            return 1
        fi
        deployment_path="${candidate}"
    done < <(
        find "${BLITZ_PROJECT}" \
            \( -name .git -o -name .venv -o -name node_modules -o \
               -path "${BLITZ_PROJECT}/${BLITZ_BIN_DIR:-bin}/B.L.I.T.Z" \) -prune -o \
            -type f \( -path '*/deployment/.blitz-build-version' -o \
                        -path '*/deployment/.build-version' \) -print
    )

    if [ -n "${deployment_path}" ]; then
        candidate="${deployment_path%/deployment}"
        candidate="${candidate#"${BLITZ_PROJECT}/"}"
        if [ -n "${BLITZ_BACKEND_DIR:-}" ] && [ "${BLITZ_BACKEND_DIR}" != "${candidate}" ]; then
            error "Installed backend is ${candidate}; requested ${BLITZ_BACKEND_DIR}."
            return 1
        fi
        BLITZ_BACKEND_DIR="${candidate}"
    fi
}

validate_backend_dir() {
    case "${BLITZ_BACKEND_DIR}" in
        "" | /* | *..* | *" "*)
            error "Backend folder must be a relative path without spaces: ${BLITZ_BACKEND_DIR}"
            return 1
            ;;
    esac
}

write_deploy_template() {
    local deploy_path="$1"
    cat >"${deploy_path}" <<PY
from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import ProcessPlan, WeightedProcess
from backend.deployment.fleet import ExpectedSystemType

SIMULATION_ENABLED = False
SIMULATION_DEVICES: tuple[str, ...] = ()
# Example: ("127.0.0.1:15000", "127.0.0.1:25000")
FLEET_SIZE: int | None = None
DEVICE_PROFILES: tuple[ExpectedSystemType, ...] = ()


class ProcessType(WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return ProcessPlan[ProcessType]().assign(pi_names)


def get_modules() -> list[SupportedModules._Generic]:
    return []


if __name__ == "__main__":
    options = (
        BlitzNetworkDeployer.Options()
        .set_local_backend_path("${BLITZ_BACKEND_DIR}")
        .set_simulation(SIMULATION_ENABLED)
        .set_simulation_devices(SIMULATION_DEVICES)
        .require_fleet_size(FLEET_SIZE)
        .require_device_profiles(DEVICE_PROFILES)
        .should_bundle_dependencies(True)
        .build()
    )
    BlitzNetworkDeployer.run_cli(get_modules(), pi_name_to_process_types, options)
PY
}

install_plain_backend() {
    local source="$1"
    local backend_path="${BLITZ_PROJECT}/${BLITZ_BACKEND_DIR}"
    local deployment_path="${backend_path}/deployment"
    local deploy_path="${backend_path}/deploy.py"
    local local_script="${BLITZ_PROJECT}/scripts/backend.sh"

    if [ "${source}/backend/deployment" = "${deployment_path}" ]; then
        error "Source and destination deployment folders must differ."
        return 1
    fi
    if [ "${BLITZ_BACKEND_DIR}" != "backend" ] &&
        [ -e "${BLITZ_PROJECT}/backend" ] && [ ! -L "${BLITZ_PROJECT}/backend" ]; then
        error "Cannot create Python import alias because backend already exists."
        return 1
    fi
    if [ -L "${BLITZ_PROJECT}/backend" ] &&
        [ "$(readlink "${BLITZ_PROJECT}/backend")" != "${BLITZ_BACKEND_DIR}" ]; then
        error "Cannot replace an unrelated backend import alias."
        return 1
    fi
    mkdir -p "${backend_path}" "${BLITZ_PROJECT}/scripts"
    rm -rf "${deployment_path}"
    cp -R "${source}/backend/deployment" "${deployment_path}"
    find "${deployment_path}" \( -name __pycache__ -o -name .DS_Store \) -prune -exec rm -rf {} +

    if [ ! -f "${deploy_path}" ]; then
        write_deploy_template "${deploy_path}"
    fi
    cp "${source}/scripts/wpi-local/backend.sh" "${local_script}"
    chmod +x "${local_script}"

    if [ "${BLITZ_BACKEND_DIR}" != "backend" ]; then
        ln -sfn "${BLITZ_BACKEND_DIR}" "${BLITZ_PROJECT}/backend"
    fi

    printf 'Installed BLITZ backend in %s\n' "${backend_path}"
}

main() {
    local source
    BLITZ_PROJECT="${BLITZ_PROJECT:-${WPILIB_PROJECT:-$(pwd)}}"
    [ -d "${BLITZ_PROJECT}" ] || { error "Project path does not exist: ${BLITZ_PROJECT}"; return 1; }
    BLITZ_PROJECT="$(cd "${BLITZ_PROJECT}" && pwd)"

    detect_backend_dir
    BLITZ_BACKEND_DIR="${BLITZ_BACKEND_DIR:-backend}"
    validate_backend_dir

    BLITZ_SETUP="${BLITZ_SETUP:-none}"
    if [ -t 0 ] && [ -z "${BLITZ_ASSUME_YES:-}" ]; then
        read -r -p "Setup integration [none/wpilib] [${BLITZ_SETUP}]: " selected_setup
        BLITZ_SETUP="${selected_setup:-${BLITZ_SETUP}}"
    fi
    case "${BLITZ_SETUP}" in
        none | wpilib) ;;
        *) error "Unsupported setup integration: ${BLITZ_SETUP}"; return 1 ;;
    esac

    source_root
    source="${SOURCE_ROOT}"
    [ -f "${source}/backend/deployment/.blitz-build-version" ] || {
        error "Source is missing backend/deployment/.blitz-build-version."
        return 1
    }
    if [ "${BLITZ_SETUP}" = "wpilib" ]; then
        BLITZ_SOURCE_DIR="${source}" \
        WPILIB_PROJECT="${BLITZ_PROJECT}" \
        BLITZ_BACKEND_DIR="${BLITZ_BACKEND_DIR}" \
        BLITZ_ASSUME_YES=true \
            bash "${source}/scripts/ui/install_on_wpilib.sh"
    else
        install_plain_backend "${source}"
    fi
}

main "$@"
