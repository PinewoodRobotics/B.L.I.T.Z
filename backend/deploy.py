import json
from backend.deployment.deployer import BlitzNetworkDeployer, PresetConfigSuppliers
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.processes import ProcessPlan, WeightedProcess
from backend.deployment.module.supported import SupportedModules


class ProcessType(WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return ProcessPlan[ProcessType]().assign(pi_names)


def get_modules() -> list[SupportedModules._Generic]:
    return []


if __name__ == "__main__":
    config = (
        BlitzNetworkDeployer.Options()
        .set_local_backend_path(FolderPath("backend/"))
        # .should_bundle_dependencies(True)
        .set_discovery_timeout(2)
        .set_config_supplier(
            lambda: json.dumps(
                {
                    "config": "test",
                }
            )
        )
        .build()
    )

    BlitzNetworkDeployer.deploy(
        get_modules(),
        pi_name_to_process_types,
        config=config,
    )
