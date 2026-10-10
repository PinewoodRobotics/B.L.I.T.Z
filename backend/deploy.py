import json
import subprocess
from backend.deployment.deployer import BlitzNetworkDeployer, MissingDependencyCacheError, PresetConfigSuppliers
from backend.deployment.compilation.system_builder import DockerCacheInspectionError
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.processes import ProcessPlan, WeightedProcess
from backend.deployment.module.supported import SupportedModules
from backend.deployment.module.catalog import BackendModules
from backend.deployment.fleet import ExpectedSystemType, FleetValidationError

modules = BackendModules(__file__)

# Configure simulation here. Only --simulation (or enabling this default) uses
# these watchdog HTTP addresses. Docker must already publish the listed ports.
SIMULATION_ENABLED = False
SIMULATION_DEVICES: tuple[str, ...] = ()
# Example: ("127.0.0.1:15000", "127.0.0.1:25000", "127.0.0.1:35000")

# Optional live-fleet checks, applied after blacklisting and before any build.
FLEET_SIZE: int | None = None
DEVICE_PROFILES: tuple[ExpectedSystemType, ...] = ()


class ProcessType(WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return ProcessPlan[ProcessType]().assign(pi_names)


def get_modules() -> list[SupportedModules._Generic]:
    return []


if __name__ == "__main__":
    config = (
        BlitzNetworkDeployer.Options()
        .set_local_backend_path(modules.backend_path)
        .set_simulation(SIMULATION_ENABLED)
        .set_simulation_devices(SIMULATION_DEVICES)
        .require_fleet_size(FLEET_SIZE)
        .require_device_profiles(DEVICE_PROFILES)
        .set_config_supplier(
            lambda: json.dumps(
                {
                    "config": "test",
                }
            )
        )
        .build()
    )

    try:
        BlitzNetworkDeployer.run_cli(
            get_modules(),
            pi_name_to_process_types,
            config=config,
        )
    except (MissingDependencyCacheError, DockerCacheInspectionError, FleetValidationError) as error:
        raise SystemExit(str(error)) from None
    except subprocess.CalledProcessError as error:
        if error.cmd and error.cmd[0] == "docker":
            raise SystemExit(f"Docker command failed with exit code {error.returncode}; see the step output and log path above.") from None
        raise
