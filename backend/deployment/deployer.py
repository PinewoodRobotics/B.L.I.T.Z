from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from backend.deployment.bundler import CodeBundler
from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.misc import output
from backend.deployment.module.base import Module
from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.zeroconf import (
    DiscoveredNetworkSystem,
    discover_all_on_network,
)
from backend.deployment.processes import WeightedProcess, normalize_pi_name
from backend.deployment.rsyncer import Rsyncer


ProcessMapper = Callable[..., Mapping[str, Sequence[WeightedProcess]]]


class BlitzNetworkDeployer:
    build_folder_path: str = "build/"
    output_folder_path: str = "build/bundle-outputs/"
    bundle_name: str = "backend-bundle"
    remote_bundle_path: str = "bundles/"
    discovery_timeout: float = 5.0
    bundle_dependencies: bool = False
    host_to_pass_user_mapper: dict[str, tuple[str, str]] = {}
    docker_compose_service_mapper: dict[str, str] = {
        "blitz-discoverable-dev-test": "blitz-dev-test",
    }

    @staticmethod
    def deploy(
        modules: list[Module],
        mapper: ProcessMapper,
        local_backend_path: str = "src/backend/",
    ) -> None:
        output.start_deployment()
        output.start_discovery(BlitzNetworkDeployer.discovery_timeout)
        discovered_systems = discover_all_on_network(
            timeout_seconds=BlitzNetworkDeployer.discovery_timeout,
            on_discovered=BlitzNetworkDeployer._log_discovered_system,
            on_tick=output.discovery_tick,
        )
        output.finish_discovery(len(discovered_systems))

        systems = {System(general_info=discovered) for discovered in discovered_systems}
        for system in systems:
            BlitzNetworkDeployer._configure_system_transport(system)

        system_ids = BlitzNetworkDeployer._unique_system_ids(systems)
        for system_id in system_ids:
            bundle_stage = f"bundle {system_id.to_build_key()}"
            output.deployment_stage(bundle_stage, "running", "building backend bundle")
            output.refresh_deployment_display()
            _ = CodeBundler(
                modules=modules,
                backend_local_path=local_backend_path,
                build_folder_path=BlitzNetworkDeployer.build_folder_path,
                output_folder_path=BlitzNetworkDeployer.output_folder_path,
                system_id=system_id,
                bundle_name=BlitzNetworkDeployer.bundle_name,
                bundle_dependencies=BlitzNetworkDeployer.bundle_dependencies,
                additional_files=[],
            ).bundle()
            output.deployment_stage(bundle_stage, "done", "bundle archive ready")

        Rsyncer(
            modules=modules,
            local_bundler_output_path=BlitzNetworkDeployer.output_folder_path,
            backend_bundle_path=BlitzNetworkDeployer.remote_bundle_path,
            systems=systems,
            system_host_to_pass_user=BlitzNetworkDeployer.host_to_pass_user_mapper,
            are_deps_bundled=BlitzNetworkDeployer.bundle_dependencies,
        ).deploy()

        process_mapping = mapper(
            [system.general_info.system_name for system in systems]
        )
        output.start_process_assignment(
            [BlitzNetworkDeployer._system_label(system) for system in systems]
        )
        for system in sorted(systems, key=BlitzNetworkDeployer._system_label):
            pi_name = normalize_pi_name(system.general_info.system_name)
            processes = process_mapping.get(
                pi_name,
                process_mapping.get(system.general_info.system_name, ()),
            )
            system_label = BlitzNetworkDeployer._system_label(system)
            output.process_assignment(
                system_label,
                [process.get_name() for process in processes],
            )
            if len(processes) == 0:
                continue

            successfully_set_processes = system.set_processes(processes)
            if not successfully_set_processes:
                output.process_assignment_failure(system_label)
                raise RuntimeError(
                    f"Failed to set processes on {system.general_info.hostname}"
                )
            output.process_assignment_success(system_label)

        output.finish_process_assignment()

    @staticmethod
    def _unique_system_ids(systems: set[System]) -> list[SystemId]:
        system_ids_by_build_key: dict[str, SystemId] = {}
        for system in systems:
            try:
                system_id = system.general_info.to_system_id()
            except ValueError as error:
                BlitzNetworkDeployer._log_system_id_failure(
                    system.general_info,
                    error,
                )
                raise
            _ = system_ids_by_build_key.setdefault(system_id.to_build_key(), system_id)
        return [
            system_ids_by_build_key[key]
            for key in sorted(system_ids_by_build_key.keys())
        ]

    @staticmethod
    def _system_label(system: System) -> str:
        return f"{system.general_info.system_name} " f"({system.general_info.hostname})"

    @staticmethod
    def _log_discovered_system(system: DiscoveredNetworkSystem) -> None:
        try:
            system_key = system.to_system_id().to_build_key()
        except ValueError as error:
            output.discovered_system(
                system.system_name,
                system.hostname,
                "system id unavailable",
            )
            BlitzNetworkDeployer._log_system_id_failure(system, error)
            return

        output.discovered_system(
            system.system_name,
            system.hostname,
            system_key,
        )

    @staticmethod
    def _log_system_id_failure(
        system: DiscoveredNetworkSystem,
        error: ValueError,
    ) -> None:
        output.warning(f"Could not build system id for {system.hostname}: {error}")
        for label, value in system.system_id_diagnostics().items():
            output.detail(f"zeroconf {label}", value)

    @staticmethod
    def _configure_system_transport(system: System) -> None:
        docker_service = BlitzNetworkDeployer.docker_compose_service_mapper.get(
            system.general_info.system_name,
            BlitzNetworkDeployer.docker_compose_service_mapper.get(
                system.general_info.hostname
            ),
        )
        if docker_service is None:
            return

        system.docker_compose_service = docker_service
        output.detail(
            "deploy transport",
            f"{system.general_info.system_name} -> docker compose {docker_service}",
        )

    class Options:
        @staticmethod
        def set_host_to_pass_user_mapper(
            mapper: dict[str, tuple[str, str]],
        ) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.host_to_pass_user_mapper = mapper
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_pass_user_for_host(
            host: str, pass_user: tuple[str, str]
        ) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.host_to_pass_user_mapper[host] = pass_user
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_docker_compose_service_mapper(
            mapper: dict[str, str],
        ) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.docker_compose_service_mapper = mapper
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_docker_compose_service_for_system(
            system_name_or_host: str,
            service: str,
        ) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.docker_compose_service_mapper[system_name_or_host] = (
                service
            )
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_discovery_timeout(
            timeout: float,
        ) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.discovery_timeout = timeout
            return BlitzNetworkDeployer.Options

        @staticmethod
        def should_bundle_dependencies(
            dependencies: bool,
        ) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.bundle_dependencies = dependencies
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_build_folder_path(path: str) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.build_folder_path = path
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_output_folder_path(path: str) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.output_folder_path = path
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_bundle_name(name: str) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.bundle_name = name
            return BlitzNetworkDeployer.Options

        @staticmethod
        def set_remote_bundle_path(path: str) -> "type[BlitzNetworkDeployer.Options]":
            BlitzNetworkDeployer.remote_bundle_path = path
            return BlitzNetworkDeployer.Options


def _verify_deploy_file():

    import importlib

    deploy_module = importlib.import_module("backend.deploy")
    all_functions = deploy_module.__dict__
    if "get_modules" not in all_functions:
        raise Exception(
            "get_modules() not found in backend.deploy. Please add a function that returns a list[Module] named get_modules(). THIS IS A REQUIRED FUNCTION."
        )

    get_modules = all_functions["get_modules"]
    pi_name_to_process_types = all_functions.get("pi_name_to_process_types")
    modules = get_modules()
    if not isinstance(modules, list) or not all(isinstance(m, Module) for m in modules):
        raise Exception(
            f"get_modules() returned {type(modules)} with element types {[type(m) for m in modules] if isinstance(modules, list) else 'N/A'} instead of list[Module]"
        )

    if pi_name_to_process_types is None or not callable(pi_name_to_process_types):
        raise Exception(
            "pi_name_to_process_types() not found in backend.deploy. Please add a function named pi_name_to_process_types. "
            "It must return dict[str, list[_WeightedProcess]] and may optionally accept a list[str] of discovered Pi names."
        )


_verify_deploy_file()
