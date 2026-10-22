from __future__ import annotations

from backend.deployment.misc.report import profile, stage

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import subprocess

from backend.deployment.bundle_index import save_bundle_index, verify_bundles
from backend.deployment.bundler import CodeBundler
from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.fleet import (
    ExpectedSystemType, validate_fleet_configuration, validate_fleet_count,
    validate_fleet_profiles,
)
from backend.deployment.module.base import Module, matches_module_type
from backend.deployment.module.graph import ModuleGraph
from backend.deployment.network_api.internet import has_internet_access
from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.network_api.zeroconf import (
    discover_at_addresses,
    discover_all_on_network,
)
from backend.deployment.processes import WeightedProcess, normalize_pi_name
from backend.deployment.rsyncer import Rsyncer


ProcessMapper = Callable[..., Mapping[str, Sequence[WeightedProcess]]]


@dataclass(frozen=True)
class DeploymentContext:
    """One validated live fleet, reused by orchestration and deployment."""

    modules: tuple[Module, ...]
    options: BlitzNetworkDeployer.Options
    systems: frozenset[System]
    process_mapping: Mapping[str, tuple[WeightedProcess, ...]]


@dataclass(frozen=True)
class DeploymentCommand:
    phase: str
    options: BlitzNetworkDeployer.Options
    system_ids: tuple[str, ...] = ()


class MissingDependencyCacheError(RuntimeError):
    """A discovered target needs online dependency preparation."""


class PresetConfigSuppliers(Enum):
    NPM_CONFIG_COMMAND = "npm run config --silent"

    def create_supplier(self) -> Callable[[], str]:
        if self is PresetConfigSuppliers.NPM_CONFIG_COMMAND:
            return lambda: subprocess.check_output(
                self.value,
                shell=True,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        raise ValueError(f"Unsupported config supplier preset: {self}")


class BlitzNetworkDeployer:
    @staticmethod
    def discover(
        modules: list[Module], config: BlitzNetworkDeployer.Options | None = None
    ) -> list[SystemId]:
        if config is None:
            config = BlitzNetworkDeployer.Options().build()
        systems = BlitzNetworkDeployer._find_systems(config)
        if not systems:
            raise ValueError(
                "No watchdog systems discovered via _watchdog._tcp.local. "
                "No Dockerfiles were generated. Connect to the device network "
                "and confirm the watchdog is advertising its service, or pass "
                "--device HOST:PORT."
            )
        system_ids = BlitzNetworkDeployer._unique_system_ids(systems)
        BlitzNetworkDeployer._remember_systems(config, systems)
        BlitzNetworkDeployer.prepare_systems(modules, system_ids, config)
        print(f"[ OK ] Selected {len(systems)} target(s)")
        return system_ids

    @staticmethod
    def prepare_systems(
        modules: list[Module], system_ids: Sequence[SystemId],
        config: BlitzNetworkDeployer.Options,
    ) -> None:
        """Generate Dockerfiles for known target profiles without contacting devices."""
        if not system_ids:
            raise ValueError("No system profiles provided")
        system_ids = list({system_id.to_build_key(): system_id for system_id in system_ids}.values())
        if not modules:
            print("warning: get_modules() returned no modules; generated Dockerfiles will have no project builds")
        for system_id in system_ids:
            BlitzNetworkDeployer._bundler(modules, config, system_id).prepare()
        build_root = Path(config.build_folder_path) / config.bundle_name / "contexts"
        print(f"[ OK ] Prepared {len(system_ids)} build profile(s)")
        print(f"       Build contexts: {build_root}")

    @staticmethod
    def build_bundles(
        modules: list[Module], config: BlitzNetworkDeployer.Options | None = None,
        system_ids: Sequence[SystemId] | None = None,
        dependency_images: Mapping[str, str] | None = None,
    ) -> dict[str, Path]:
        if config is None:
            config = BlitzNetworkDeployer.Options().build()
        bundles: dict[str, Path] = {}
        for system_id in (system_ids if system_ids is not None else SystemBuilder.prepared_system_ids(
            config.build_folder_path, config.bundle_name
        )):
            bundler = BlitzNetworkDeployer._bundler(modules, config, system_id)
            image = (dependency_images or {}).get(system_id.to_build_key())
            archive = bundler.bundle(prepared=True, dependency_image=image)
            bundles[system_id.to_build_key()] = Path(archive)
        save_bundle_index(BlitzNetworkDeployer._index_path(config), bundles)
        print(f"[ OK ] Built {len(bundles)} bundle(s): {config.output_folder_path}")
        return bundles

    @staticmethod
    def distribute(
        modules: list[Module],
        mapper: ProcessMapper,
        config: BlitzNetworkDeployer.Options | None = None,
        systems: set[System] | None = None,
        process_mapping: Mapping[str, Sequence[WeightedProcess]] | None = None,
    ) -> None:
        if config is None:
            config = BlitzNetworkDeployer.Options().build()
        if systems is None:
            systems = BlitzNetworkDeployer._find_systems(config)
        else:
            BlitzNetworkDeployer._validate_fleet(config, systems)
        if not systems:
            raise ValueError("No systems discovered")
        if process_mapping is None:
            process_mapping = BlitzNetworkDeployer._preflight(modules, mapper, systems)
        else:
            BlitzNetworkDeployer._validate_mapping(modules, process_mapping, systems)
        context = DeploymentContext(
            tuple(modules), config, frozenset(systems),
            {name: tuple(processes) for name, processes in process_mapping.items()},
        )
        BlitzNetworkDeployer.distribute_prepared(context)

    @staticmethod
    def distribute_prepared(context: DeploymentContext) -> None:
        """Transfer verified bundles to an already validated deployment fleet."""
        modules = list(context.modules)
        config = context.options
        systems = set(context.systems)
        process_mapping = context.process_mapping
        bundle_paths = BlitzNetworkDeployer._bundle_paths(config, systems)
        verify_bundles(BlitzNetworkDeployer._index_path(config), bundle_paths)

        Rsyncer(
            modules=modules,
            local_bundler_output_path=config.output_folder_path,
            backend_bundle_path=config.remote_bundle_path,
            systems=systems,
            system_host_to_pass_user=config.host_to_pass_user_mapper,
            are_deps_bundled=config.bundle_dependencies,
        ).deploy()

        for system in sorted(systems, key=BlitzNetworkDeployer._system_label):
            pi_name = normalize_pi_name(system.general_info.system_name)
            processes = process_mapping.get(
                pi_name,
                process_mapping.get(system.general_info.system_name, ()),
            )

            with stage(f"{system.general_info.hostname}: send runtime configuration"):
                if not system.set_config(config.base64_supplier()):
                    raise RuntimeError(f"Failed to set config on {system.general_info.hostname}")

            names = ', '.join(p.get_name() for p in processes) or '(none)'
            with stage(f"{system.general_info.hostname}: assign processes: {names}"):
                if not system.set_processes(processes):
                    raise RuntimeError(f"Failed to set processes on {system.general_info.hostname}")
        print(f"\n[ OK ] Deployment complete: {len(systems)} target(s). Configuration and process plans accepted.\n       Process health is reported by the watchdog/dashboard.")

    @staticmethod
    def deploy(
        modules: list[Module],
        mapper: ProcessMapper,
        config: BlitzNetworkDeployer.Options | None = None,
    ) -> None:
        context = BlitzNetworkDeployer.prepare_deployment(modules, mapper, config)
        BlitzNetworkDeployer.deploy_prepared(context)

    @staticmethod
    def prepare_deployment(
        modules: list[Module], mapper: ProcessMapper,
        config: BlitzNetworkDeployer.Options | None = None,
    ) -> DeploymentContext:
        """Collect and validate targets once, without building or transferring."""
        config = config or BlitzNetworkDeployer.Options().build()
        systems = BlitzNetworkDeployer._find_systems(config)
        if not systems:
            raise ValueError("No watchdog systems discovered; no bundles were built")
        mapping = BlitzNetworkDeployer._preflight(modules, mapper, systems)
        return DeploymentContext(
            tuple(modules), config, frozenset(systems),
            {name: tuple(processes) for name, processes in mapping.items()},
        )

    @staticmethod
    def deploy_prepared(context: DeploymentContext) -> None:
        """Build and deploy using the fleet already selected by preflight."""
        modules = list(context.modules)
        config = context.options
        systems = set(context.systems)
        print(f"[ OK ] Selected {len(systems)} target(s)")
        for system in sorted(systems, key=BlitzNetworkDeployer._system_label):
            print(f"       {BlitzNetworkDeployer._system_label(system)} | {profile(system.general_info.to_system_id())}")
        BlitzNetworkDeployer._remember_systems(config, systems)
        system_ids = BlitzNetworkDeployer._unique_system_ids(systems)
        BlitzNetworkDeployer.prepare_systems(modules, system_ids, config)
        missing: dict[str, SystemBuilder] = {}
        stale_images: dict[str, str] = {}
        for system_id in system_ids:
            key = system_id.to_build_key()
            builder = BlitzNetworkDeployer._builder(config, system_id)
            cached = builder.dependencies_cached()
            print(f"[{' OK ' if cached else 'WAIT'}] Dependencies: {profile(system_id)} — {'cached' if cached else 'build required'}")
            if not cached:
                missing[key] = builder
        cache_instruction = (
            "Connect to the internet and run: python3 backend/deploy.py cache; "
            "then rerun python3 backend/deploy.py on the device network."
        )
        if missing and has_internet_access():
            print("Internet access detected; preparing missing Docker dependencies.")
            for key, builder in missing.items():
                try:
                    builder.cache_dependencies()
                    if not builder.dependencies_cached():
                        raise RuntimeError("Matching Docker dependency image is still missing")
                except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
                    raise MissingDependencyCacheError(
                        f"Online dependency preparation failed for {key}: {error}. "
                        "No deployment will proceed. " + cache_instruction
                    ) from error
            # Keep fallbacks until every selected profile has a replacement.
            for builder in missing.values():
                builder.prune_stale_dependency_images()
            missing.clear()
        elif missing:
            print("Internet access was not detected; cannot prepare missing Docker dependencies.")
            for key, builder in missing.items():
                candidates = builder.stale_dependency_images()
                if candidates:
                    stale_images[key] = candidates[0]
        unavailable = [key for key in missing if key not in stale_images]
        if unavailable:
            raise MissingDependencyCacheError(
                "Docker dependencies are not cached for: " + ", ".join(unavailable)
                + ". No older image for these system types is available. "
                + cache_instruction
            )
        if missing:
            print("WARNING: Matching Docker dependency images are missing; older images are cached.")
            for key in missing:
                print(f"  {key}: older cached image {stale_images[key]}")
            print("Continuing may build or deploy with outdated dependencies, or fail compilation.")
            try:
                answer = input("Continue with these older images? [y/N]: ").strip().lower()
            except (EOFError, OSError):
                answer = ""
            if answer not in ("y", "yes"):
                raise MissingDependencyCacheError("Deployment cancelled. " + cache_instruction)
            print("Continuing with older cached dependencies by user choice.")
        BlitzNetworkDeployer.build_bundles(modules, config, system_ids, stale_images)
        BlitzNetworkDeployer.distribute_prepared(context)

    @staticmethod
    def cache_dependencies(
        modules: list[Module], config: BlitzNetworkDeployer.Options | None = None,
    ) -> None:
        """Prepare every recorded system type while internet access is available."""
        if config is None:
            config = BlitzNetworkDeployer.Options().build()
        inventory = BlitzNetworkDeployer._read_inventory(config)
        keys = inventory["system_ids"]
        if not keys:
            raise ValueError("No systems recorded. Run python backend/deploy.py on the device network first.")
        system_ids = [SystemId.from_build_key(key) for key in keys]
        BlitzNetworkDeployer.prepare_systems(modules, system_ids, config)
        for system_id in system_ids:
            builder = BlitzNetworkDeployer._builder(config, system_id)
            if builder.dependencies_cached():
                print(f"Docker dependencies for {system_id.to_build_key()}: cached")
            else:
                builder.cache_dependencies()
        # Finish caching the fleet before discarding fallback images.
        for system_id in system_ids:
            BlitzNetworkDeployer._builder(config, system_id).prune_stale_dependency_images()
        print(f"cached dependencies for {len(system_ids)} system types")

    @staticmethod
    def parse_cli(
        argv: Sequence[str] | None = None,
        config: BlitzNetworkDeployer.Options | None = None,
        *,
        config_factory: Callable[[bool], BlitzNetworkDeployer.Options] | None = None,
    ) -> DeploymentCommand:
        """Parse and apply deployment options for every caller, without I/O."""
        parser = argparse.ArgumentParser(description="Discover, build, and distribute BLITZ bundles")
        parser.add_argument("phase", choices=("discover", "build", "distribute", "deploy", "cache"), nargs="?", default="deploy")
        parser.add_argument("--output-dir", type=Path, help="Directory for built bundles")
        parser.add_argument(
            "--device", action="append", default=[], metavar="HOST:PORT",
            help="Query this watchdog directly instead of using mDNS (repeatable)",
        )
        parser.add_argument(
            "--system-id", action="append", default=[], metavar="BUILD_KEY",
            help="Prepare a known system profile without contacting devices (repeatable)",
        )
        parser.add_argument("--blacklist", action="append", default=[], metavar="HOST_OR_IP", help="Exclude a hostname or IP before catalog requests (repeatable)")
        parser.add_argument("--sim", "--simulation", action="store_true", dest="simulation", help="Use the simulation watchdog addresses configured in deploy.py, bypassing mDNS")
        parser.add_argument("--expected-systems", type=int, metavar="COUNT", help="Require exactly this many devices after exclusions")
        args = parser.parse_args(argv)
        if args.system_id and (args.phase not in ("discover", "cache") or args.device or args.simulation):
            parser.error("--system-id is only valid for discover/cache and cannot be combined with --device or --simulation")
        options = config_factory(args.simulation) if config_factory is not None else (config or BlitzNetworkDeployer.Options().build())
        if args.simulation:
            options.set_simulation(True)
        if args.expected_systems is not None:
            options.require_fleet_size(args.expected_systems)
        if args.blacklist:
            options.set_blacklist((*options.blacklist, *args.blacklist))
        if args.device:
            if options.simulation:
                options.set_simulation_devices(args.device)
            else:
                options.set_pinned_devices(args.device)
        if args.output_dir is not None:
            options.set_output_folder_path(FolderPath(str(args.output_dir)))
        return DeploymentCommand(args.phase, options, tuple(args.system_id))

    @staticmethod
    def run_cli(
        modules: list[Module],
        mapper: ProcessMapper,
        config: BlitzNetworkDeployer.Options | None = None,
        argv: Sequence[str] | None = None,
        *,
        config_factory: Callable[[bool], BlitzNetworkDeployer.Options] | None = None,
    ) -> None:
        command = BlitzNetworkDeployer.parse_cli(argv, config, config_factory=config_factory)
        with stage(f"BLITZ {command.phase}"):
            BlitzNetworkDeployer.execute_cli(command, modules, mapper)

    @staticmethod
    def execute_cli(command: DeploymentCommand, modules: list[Module], mapper: ProcessMapper) -> None:
        options = command.options
        if command.phase == "discover":
            if command.system_ids:
                system_ids = [SystemId.from_build_key(key) for key in command.system_ids]
                BlitzNetworkDeployer._remember_system_ids(options, system_ids)
                BlitzNetworkDeployer.prepare_systems(modules, system_ids, options)
            else:
                BlitzNetworkDeployer.discover(modules, options)
        elif command.phase == "build":
            BlitzNetworkDeployer.build_bundles(modules, options)
        elif command.phase == "distribute":
            BlitzNetworkDeployer.distribute(modules, mapper, options)
        elif command.phase == "cache":
            if command.system_ids:
                BlitzNetworkDeployer._remember_system_ids(
                    options, [SystemId.from_build_key(key) for key in command.system_ids]
                )
            BlitzNetworkDeployer.cache_dependencies(modules, options)
        else:
            BlitzNetworkDeployer.deploy(modules, mapper, options)

    @staticmethod
    def _index_path(config: BlitzNetworkDeployer.Options) -> Path:
        return Path(config.output_folder_path) / "bundle-index.json"

    @staticmethod
    def _inventory_path(config: BlitzNetworkDeployer.Options) -> Path:
        return Path(config.build_folder_path) / config.bundle_name / "systems.json"

    @staticmethod
    def _read_inventory(config: BlitzNetworkDeployer.Options) -> dict:
        path = BlitzNetworkDeployer._inventory_path(config)
        inventory = json.loads(path.read_text()) if path.is_file() else {"system_ids": []}
        # Legacy destinations are never restored: offline caching remembers only
        # compatibility profiles, not device identities, addresses, or ports.
        return {"system_ids": inventory.get("system_ids", [])}

    @staticmethod
    def _remember_system_ids(config: BlitzNetworkDeployer.Options, system_ids: Sequence[SystemId]) -> None:
        inventory = BlitzNetworkDeployer._read_inventory(config)
        inventory["system_ids"] = sorted(set(inventory["system_ids"]) | {
            system_id.to_build_key() for system_id in system_ids
        })
        path = BlitzNetworkDeployer._inventory_path(config)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")

    @staticmethod
    def _remember_systems(config: BlitzNetworkDeployer.Options, systems: set[System]) -> None:
        BlitzNetworkDeployer._remember_system_ids(config, BlitzNetworkDeployer._unique_system_ids(systems))

    @staticmethod
    def _preflight(
        modules: list[Module], mapper: ProcessMapper, systems: set[System]
    ) -> Mapping[str, Sequence[WeightedProcess]]:
        mapping = mapper([system.general_info.system_name for system in sorted(systems, key=BlitzNetworkDeployer._system_label)])
        BlitzNetworkDeployer._validate_mapping(modules, mapping, systems)
        return mapping

    @staticmethod
    def _validate_mapping(
        modules: list[Module], mapping: Mapping[str, Sequence[WeightedProcess]], systems: set[System]
    ) -> None:
        graph = ModuleGraph(modules)
        for system in systems:
            name = system.general_info.system_name
            processes = mapping.get(normalize_pi_name(name), mapping.get(name, ()))
            graph.validate_processes([process.get_name() for process in processes], system.general_info.to_system_id())

    @staticmethod
    def _builder(config: BlitzNetworkDeployer.Options, system_id: SystemId) -> SystemBuilder:
        bundler = BlitzNetworkDeployer._bundler([], config, system_id)
        return SystemBuilder(system_id, bundler.build_path, bundler.context_path, config.local_backend_path)

    @staticmethod
    def _find_systems(config: BlitzNetworkDeployer.Options) -> set[System]:
        expected_count = validate_fleet_configuration(config.expected_system_count, config.expected_system_types)
        if config.simulation:
            if config.pinned_devices:
                raise ValueError("Simulation mode cannot use pinned physical targets; use simulation_devices instead")
            if not config.simulation_devices:
                raise ValueError("Simulation mode requires watchdog HOST:PORT addresses in SIMULATION_DEVICES in deploy.py, or --simulation --device HOST:PORT. mDNS will not be used.")
            discovered = discover_at_addresses(config.simulation_devices, blacklist=config.blacklist, expected_count=expected_count)
        elif config.pinned_devices:
            discovered = discover_at_addresses(config.pinned_devices, blacklist=config.blacklist, expected_count=expected_count)
        else:
            discovered = discover_all_on_network(timeout_seconds=config.discovery_timeout, blacklist=config.blacklist, expected_count=expected_count)
        names: set[str] = set()
        for system in discovered:
            name = normalize_pi_name(system.system_name)
            if name in names:
                raise ValueError(f"Duplicate discovered system name: {name}. Assign unique system names before deployment.")
            names.add(name)
        systems = {System(general_info=system) for system in discovered}
        BlitzNetworkDeployer._validate_fleet(config, systems)
        return systems

    @staticmethod
    def _validate_fleet(config: BlitzNetworkDeployer.Options, systems: set[System]) -> None:
        validate_fleet_count(len(systems), config.expected_system_count, config.expected_system_types)
        if config.expected_system_types:
            validate_fleet_profiles(
                [system.general_info.to_system_id() for system in systems],
                config.expected_system_types,
            )

    @staticmethod
    def _bundler(
        modules: list[Module], config: BlitzNetworkDeployer.Options, system_id: SystemId
    ) -> CodeBundler:
        return CodeBundler(
            modules=modules,
            backend_local_path=config.local_backend_path,
            build_folder_path=config.build_folder_path,
            output_folder_path=config.output_folder_path,
            system_id=system_id,
            bundle_name=config.bundle_name,
            bundle_dependencies=config.bundle_dependencies,
            additional_files=[],
        )

    @staticmethod
    def _bundle_paths(
        config: BlitzNetworkDeployer.Options, systems: set[System]
    ) -> dict[str, Path]:
        return {
            system_id.to_build_key(): Path(config.output_folder_path)
            / f"{system_id.to_build_key()}.zip"
            for system_id in BlitzNetworkDeployer._unique_system_ids(systems)
        }

    @staticmethod
    def _unique_system_ids(systems: set[System]) -> list[SystemId]:
        system_ids_by_build_key: dict[str, SystemId] = {}
        for system in systems:
            system_id = system.general_info.to_system_id()
            _ = system_ids_by_build_key.setdefault(system_id.to_build_key(), system_id)
        return [
            system_ids_by_build_key[key]
            for key in sorted(system_ids_by_build_key.keys())
        ]

    @staticmethod
    def _system_label(system: System) -> str:
        return f"{system.general_info.system_name} " f"({system.general_info.hostname})"

    @dataclass
    class Options:
        local_backend_path: FolderPath = field(
            default_factory=lambda: FolderPath(str(Path(__file__).resolve().parents[1]))
        )
        build_folder_path: FolderPath = FolderPath("build/")
        output_folder_path: FolderPath = FolderPath("build/backend-bundle/outputs/")
        bundle_name: str = "backend-bundle"
        remote_bundle_path: FolderPath = FolderPath("bundles/")
        discovery_timeout: float = 10.0
        pinned_devices: tuple[str, ...] = ()
        simulation: bool = False
        simulation_devices: tuple[str, ...] = ()
        expected_system_count: int | None = None
        expected_system_types: tuple[ExpectedSystemType, ...] = ()
        blacklist: tuple[str, ...] = ()
        bundle_dependencies: bool = True
        host_to_pass_user_mapper: dict[str, tuple[str, str]] = field(
            default_factory=dict
        )
        base64_supplier: Callable[[], str] = field(default_factory=lambda: lambda: "")

        def set_host_to_pass_user_mapper(
            self,
            mapper: dict[str, tuple[str, str]],
        ) -> "BlitzNetworkDeployer.Options":
            self.host_to_pass_user_mapper = dict(mapper)
            return self

        def set_local_backend_path(
            self,
            path: FolderPath,
        ) -> "BlitzNetworkDeployer.Options":
            self.local_backend_path = path
            return self

        def set_pass_user_for_host(
            self,
            host: str,
            pass_user: tuple[str, str],
        ) -> "BlitzNetworkDeployer.Options":
            self.host_to_pass_user_mapper[host] = pass_user
            return self

        def set_discovery_timeout(
            self,
            timeout: float,
        ) -> "BlitzNetworkDeployer.Options":
            self.discovery_timeout = timeout
            return self

        def set_pinned_devices(
            self, addresses: Sequence[str]
        ) -> "BlitzNetworkDeployer.Options":
            self.pinned_devices = tuple(addresses)
            return self

        def set_blacklist(self, hosts_or_ips: Sequence[str]) -> "BlitzNetworkDeployer.Options":
            self.blacklist = tuple(hosts_or_ips)
            return self

        def set_simulation(self, enabled: bool = True) -> "BlitzNetworkDeployer.Options":
            self.simulation = enabled
            return self

        def set_simulation_devices(self, addresses: Sequence[str]) -> "BlitzNetworkDeployer.Options":
            self.simulation_devices = tuple(addresses)
            return self

        def require_fleet_size(self, count: int | None) -> "BlitzNetworkDeployer.Options":
            validate_fleet_configuration(count, self.expected_system_types)
            self.expected_system_count = count
            return self

        def require_device_profiles(self, profiles: Sequence[ExpectedSystemType]) -> "BlitzNetworkDeployer.Options":
            profiles = tuple(profiles)
            validate_fleet_configuration(self.expected_system_count, profiles)
            self.expected_system_types = profiles
            return self

        def set_expected_system_count(self, count: int | None) -> "BlitzNetworkDeployer.Options":
            """Compatibility alias for require_fleet_size."""
            return self.require_fleet_size(count)

        def set_expected_system_types(self, profiles: Sequence[ExpectedSystemType]) -> "BlitzNetworkDeployer.Options":
            """Compatibility alias for require_device_profiles."""
            return self.require_device_profiles(profiles)

        def set_config_supplier(
            self,
            base64_supplier: Callable[[], str] | PresetConfigSuppliers,
        ) -> "BlitzNetworkDeployer.Options":
            if isinstance(base64_supplier, PresetConfigSuppliers):
                self.base64_supplier = base64_supplier.create_supplier()
                return self
            self.base64_supplier = base64_supplier
            return self

        def should_bundle_dependencies(
            self,
            dependencies: bool,
        ) -> "BlitzNetworkDeployer.Options":
            self.bundle_dependencies = dependencies
            return self

        def set_build_folder_path(
            self,
            path: FolderPath,
        ) -> "BlitzNetworkDeployer.Options":
            self.build_folder_path = path
            return self

        def set_output_folder_path(
            self,
            path: FolderPath,
        ) -> "BlitzNetworkDeployer.Options":
            self.output_folder_path = path
            return self

        def set_bundle_name(
            self,
            name: str,
        ) -> "BlitzNetworkDeployer.Options":
            self.bundle_name = name
            return self

        def set_remote_bundle_path(
            self,
            path: FolderPath,
        ) -> "BlitzNetworkDeployer.Options":
            self.remote_bundle_path = path
            return self

        def build(self) -> "BlitzNetworkDeployer.Options":
            validate_fleet_configuration(self.expected_system_count, self.expected_system_types)
            return self


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
    if not isinstance(modules, list) or not all(matches_module_type(m, Module) for m in modules):
        raise Exception(
            f"get_modules() returned {type(modules)} with element types {[type(m) for m in modules] if isinstance(modules, list) else 'N/A'} instead of list[Module]"
        )

    if pi_name_to_process_types is None or not callable(pi_name_to_process_types):
        raise Exception(
            "pi_name_to_process_types() not found in backend.deploy. Please add a function named pi_name_to_process_types. "
            "It must return dict[str, list[_WeightedProcess]] and may optionally accept a list[str] of discovered Pi names."
        )


if __name__ == "__main__":
    _verify_deploy_file()
