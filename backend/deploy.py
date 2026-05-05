from backend.deployment.deployer import BlitzNetworkDeployer, PresetConfigSuppliers
from backend.deployment.misc import output
from backend.deployment.processes import ProcessPlan, WeightedProcess
from backend.deployment.module.supported import SupportedModules


class ProcessType(WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        # .add(ProcessType.POS_EXTRAPOLATOR)
        # .pin(ProcessType.APRIL_SERVER, "nathan-hale")
        .assign(pi_names)
    )


def get_modules() -> list[SupportedModules.Generic]:
    return []


if __name__ == "__main__":
    output.set_verbosity(False)

    config = (
        BlitzNetworkDeployer.Options()
        .should_bundle_dependencies(True)
        .set_discovery_timeout(2)
        .set_config_supplier(PresetConfigSuppliers.NPM_CONFIG_COMMAND)
        .build()
    )

    BlitzNetworkDeployer.deploy(
        get_modules(),
        pi_name_to_process_types,
        config=config,
    )
