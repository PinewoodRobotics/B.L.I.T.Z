"""Create and execute one complete build graph for each discovered system."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tomllib

from backend.deployment.compilation.util.commands import run_command
from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.module.base import Module, matches_module_type
from backend.deployment.module.graph import ModuleGraph
from backend.deployment.module.layout import validate_backend_layout
from backend.deployment.module.supported import (
    CPPLibraryModule,
    CPPRunnableModule,
    GeneratedModule,
    PythonModule,
    RustModule,
    RustLibraryModule,
)
from backend.deployment.network_api.utils import FolderPath

ARTIFACT_SCRIPT_PATH = Path(__file__).with_name("build_artifacts.py")
SCRIPT_PATH = Path(__file__).with_name("build_system.sh")
# Bump this when the script's provisioning behavior changes. Compile and logging
# edits must not force dependency downloads for every recorded system type.
PROVISION_SCHEMA_VERSION = "1"


class DockerCacheInspectionError(RuntimeError):
    """Docker could not report whether a dependency image is present."""


@dataclass(frozen=True)
class BuildStep:
    """One ordered node in the per-system dependency and compilation graph."""

    id: str
    kind: str
    requires: tuple[str, ...] = ()
    module: str | None = None
    language: str | None = None
    source: str | None = None
    command: str | None = None
    libraries: str | None = None
    extra_commands: str | None = None
    binary: str | None = None
    dependencies: tuple[str, ...] = ()
    outputs: dict[str, tuple[str, ...]] | None = None
    entry_file: str | None = None
    entry_package: str | None = None
    target_capabilities: tuple[dict[str, str | None], ...] = ()


@dataclass(frozen=True)
class BuildPlan:
    system_id: SystemId
    steps: tuple[BuildStep, ...]

    def to_dict(self) -> dict[str, object]:
        completed: set[str] = set()
        for step in self.steps:
            missing = set(step.requires) - completed
            if step.id in completed or missing:
                raise ValueError(f"Invalid build graph at {step.id}: missing {sorted(missing)}")
            completed.add(step.id)
        serialized_steps = []
        provision_kinds = {"system-packages", "cpp-dependencies", "rust-toolchain", "rust-fetch", "python-wheels"}
        for step in self.steps:
            values = asdict(step)
            if step.kind in provision_kinds:
                for key in ("dependencies", "outputs", "entry_file", "entry_package", "target_capabilities"):
                    values.pop(key)
            serialized_steps.append(values)
        return {
            "system": {
                **({"capabilities": dict(self.system_id.capabilities)} if self.system_id.capabilities else {}),
                "glibc": self.system_id.c_lib_version,
                "distro": self.system_id.linux_distro.value,
                "distro_key": self.system_id.linux_distro.remove_nonchars(),
                "architecture": self.system_id.architecture.value,
                "python_major": self.system_id.python_version.major,
                "python_minor": self.system_id.python_version.minor,
            },
            "steps": serialized_steps,
        }


def _copy_source(source: str, destination: Path, exclude: str = "") -> None:
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", "build", "target", "node_modules",
            ".env*", ".ssh", "system_data", exclude,
        ),
    )


class SystemBuilder:
    def __init__(
        self, system_id: SystemId, build_path: FolderPath, context_path: FolderPath,
        backend_path: FolderPath | None = None,
    ):
        self.system_id = system_id
        self.build_path = Path(build_path).resolve()
        self.context = Path(context_path).resolve()
        self.dockerfile = self.context / "Dockerfile"
        self.backend_path = Path(backend_path).resolve() if backend_path is not None else None

    def _stage_project(self, module: Module, source: str, workspace_copied: bool) -> tuple[str, bool]:
        source_path = Path(source).resolve()
        if self.backend_path is not None:
            if not workspace_copied:
                _copy_source(str(self.backend_path), self.context / 'workspace' / 'backend')
            staged_source = self.context / 'workspace' / 'backend' / source_path.relative_to(self.backend_path)
            return f'/work/{staged_source.relative_to(self.context)}', True
        try:
            relative_path = source_path.relative_to(Path.cwd().resolve())
        except ValueError:
            staged_source = self.context / "sources" / module.get_language_name() / module.name
            _copy_source(source, staged_source)
        else:
            if not workspace_copied:
                _copy_source(str(Path.cwd()), self.context / "workspace", self.context.name)
                workspace_copied = True
            staged_source = self.context / "workspace" / relative_path
        return f"/work/{staged_source.relative_to(self.context)}", workspace_copied

    def create_plan(self, modules: list[Module], bundle_dependencies: bool) -> BuildPlan:
        """Build every compatible declared module, regardless of process assignment."""
        if self.backend_path is not None:
            validate_backend_layout(modules, str(self.backend_path))
        graph = ModuleGraph(modules)
        for module in graph.ordered:
            reason = graph.reason(module.name, self.system_id)
            if reason:
                print(f"Skipping module {module.name}: {reason}")
        modules = graph.compatible(self.system_id)
        self.context.mkdir(parents=True, exist_ok=True)
        for folder in ("sources", "workspace", "dependency-inputs"):
            staged_folder = self.context / folder
            if staged_folder.exists():
                shutil.rmtree(staged_folder)
            staged_folder.mkdir()
        staged: list[tuple[Module, str]] = []
        workspace_copied = False
        for module in modules:
            if matches_module_type(module, CPPLibraryModule, CPPRunnableModule, RustModule, RustLibraryModule, GeneratedModule):
                source, workspace_copied = self._stage_project(
                    module, module.project_root_folder_path, workspace_copied
                )
            elif matches_module_type(module, PythonModule):
                staged_source = self.context / "sources" / "python" / module.name
                _copy_source(module.module_folder_path, staged_source)
                if self.backend_path is not None:
                    common = self.backend_path / 'python' / 'common'
                    if common.is_dir():
                        if (staged_source / 'common').exists():
                            raise ValueError(f'Module {module.name} shadows shared backend/python/common')
                        _copy_source(str(common), staged_source / 'common')
                source = f"/work/{staged_source.relative_to(self.context)}"
            else:
                raise TypeError(f"Container build does not support {type(module).__name__}")
            staged.append((module, source))

        cpp_modules = [(m, s) for m, s in staged if matches_module_type(m, CPPLibraryModule, CPPRunnableModule)]
        rust_modules = [(m, s) for m, s in staged if matches_module_type(m, RustModule, RustLibraryModule)]
        python_wheels = bundle_dependencies and any(matches_module_type(m, PythonModule) for m, _ in staged)
        if python_wheels and not workspace_copied and self.backend_path is None:
            _copy_source(str(Path.cwd()), self.context / "workspace", self.context.name)
        dependency_inputs = self.context / "dependency-inputs"
        if python_wheels:
            requirements = Path.cwd() / "requirements.txt"
            if not requirements.is_file():
                raise FileNotFoundError("Python modules require requirements.txt for offline bundles")
            python_inputs = dependency_inputs / "python"
            python_inputs.mkdir(parents=True)
            pending = [requirements]
            copied: set[Path] = set()
            while pending:
                requirement_file = pending.pop().resolve()
                if requirement_file in copied:
                    continue
                relative = requirement_file.relative_to(Path.cwd().resolve())
                destination = python_inputs / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(requirement_file, destination)
                copied.add(requirement_file)
                for line in requirement_file.read_text().splitlines():
                    tokens = shlex.split(line, comments=True)
                    if not tokens:
                        continue
                    option = tokens[0]
                    if option in ("-r", "--requirement", "-c", "--constraint"):
                        if len(tokens) < 2:
                            raise ValueError(f"Missing requirement include in {requirement_file}")
                        pending.append(requirement_file.parent / tokens[1])
                    elif option.startswith(("-r", "-c")) and len(option) > 2:
                        pending.append(requirement_file.parent / option[2:])
                    elif option.startswith(("--requirement=", "--constraint=")):
                        pending.append(requirement_file.parent / option.split("=", 1)[1])
        rust_fetch_sources: dict[str, str] = {}
        for module, source in rust_modules:
            project = self.context / source.removeprefix("/work/")
            manifest_root = project
            while not (manifest_root / "Cargo.toml").is_file() and manifest_root != self.context:
                manifest_root = manifest_root.parent
            if not (manifest_root / "Cargo.toml").is_file():
                raise FileNotFoundError(f"Cargo.toml not found for {module.name}")
            if self.backend_path is not None:
                # Preserve relative path dependencies on backend/rust/common,
                # including its manifests, without caching source contents.
                manifest_root = self.context / 'workspace' / 'backend' / 'rust'
            rust_inputs = dependency_inputs / "rust" / module.name
            fetch_project = project if (project / 'Cargo.toml').is_file() else manifest_root
            rust_fetch_sources[module.name] = str(Path('/work/dependency-inputs/rust') / module.name / fetch_project.relative_to(manifest_root))
            for manifest in manifest_root.rglob("Cargo.toml"):
                if any(part in ("target", "build", ".git") for part in manifest.relative_to(manifest_root).parts):
                    continue
                dest = rust_inputs / manifest.relative_to(manifest_root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(manifest, dest)
                # Cargo validates targets even for `cargo fetch`; placeholder files
                # keep source edits out of the dependency image.
                metadata = tomllib.loads(manifest.read_text())
                target_paths = {"src/lib.rs", "src/main.rs"}
                for target in [metadata.get("lib", {}), *metadata.get("bin", [])]:
                    if isinstance(target, dict) and isinstance(target.get("path"), str):
                        target_paths.add(target["path"])
                for target_path in target_paths:
                    target = dest.parent / target_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("fn main() {}\n")
            for filename in ("Cargo.lock", ".cargo/config", ".cargo/config.toml"):
                candidate = manifest_root / filename
                if candidate.is_file():
                    dest = rust_inputs / filename
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(candidate, dest)
        steps: list[BuildStep] = []
        if staged:
            steps.append(BuildStep("system-packages", "system-packages"))
        cpp_deps: list[str] = []
        for module, _source in cpp_modules:
            assert matches_module_type(module, CPPLibraryModule, CPPRunnableModule)
            step_id = f"cpp-dependencies:{module.name}"
            cpp_deps.append(step_id)
            steps.append(BuildStep(
                step_id, "cpp-dependencies", ("system-packages",), module=module.name,
                libraries=module.compilation_config.libs,
                extra_commands=module.compilation_config.extra_docker_commands,
            ))
        if rust_modules:
            steps.append(BuildStep("rust-toolchain", "rust-toolchain", ("system-packages",)))
            for module, _source in rust_modules:
                steps.append(BuildStep(
                    f"rust-fetch:{module.name}", "rust-fetch", ("rust-toolchain",),
                    module=module.name,
                    source=rust_fetch_sources[module.name],
                ))
        if python_wheels:
            steps.append(BuildStep(
                "python-wheels", "python-wheels", ("system-packages", *cpp_deps),
            ))
        build_ids: dict[str, str] = {}
        for module, source in staged:
            dependencies = tuple(build_ids[name] for name in module.dependencies)
            metadata = dict(
                module=module.name, language=module.get_language_name(), source=source,
                dependencies=tuple(graph.closure(module.name)[1:]), outputs=asdict(module.outputs),
                target_capabilities=tuple(asdict(requirement) for requirement in module.targets.capabilities),
            )
            if matches_module_type(module, CPPLibraryModule, CPPRunnableModule):
                step = BuildStep(
                    f"cpp-build:{module.name}", "cpp-build", (*cpp_deps, *dependencies),
                    command=module.compilation_config.build_cmd,
                    binary=module.runnable_name if matches_module_type(module, CPPRunnableModule) else None,
                    **metadata,
                )
            elif matches_module_type(module, RustModule, RustLibraryModule):
                step = BuildStep(
                    f"rust-build:{module.name}", "rust-build", (f"rust-fetch:{module.name}", *dependencies),
                    binary=module.runnable_name if matches_module_type(module, RustModule) else None,
                    **metadata,
                )
            else:
                step = BuildStep(
                    f"copy:{module.get_language_name()}:{module.name}", "copy-module", dependencies,
                    entry_file=module.entrypoint.file if matches_module_type(module, PythonModule) else None,
                    entry_package=module.entrypoint.package if matches_module_type(module, PythonModule) else None,
                    **metadata,
                )
            steps.append(step)
            build_ids[module.name] = step.id
        if staged:
            steps.append(BuildStep("native-libraries", "native-libraries", (*build_ids.values(), *(("python-wheels",) if python_wheels else ()))))
        plan = BuildPlan(self.system_id, tuple(steps))
        (self.context / "build-plan.json").write_text(
            json.dumps(plan.to_dict(), indent=2) + "\n"
        )
        provision_steps = tuple(
            step for step in steps
            if step.kind in ("system-packages", "cpp-dependencies", "rust-toolchain", "rust-fetch", "python-wheels")
        )
        provision_plan = BuildPlan(self.system_id, provision_steps)
        (self.context / "provision-plan.json").write_text(
            json.dumps(provision_plan.to_dict(), indent=2) + "\n"
        )
        return plan

    def prepare(self, modules: list[Module], bundle_dependencies: bool) -> BuildPlan:
        plan = self.create_plan(modules, bundle_dependencies)
        shutil.copyfile(SCRIPT_PATH, self.context / "build_system.sh")
        shutil.copyfile(ARTIFACT_SCRIPT_PATH, self.context / "build_artifacts.py")
        platform = self.system_id.docker_image
        dockerfile_lines = [
            "ARG DEPENDENCY_IMAGE=scratch",
            f"# dependency-cache: {self.dependency_image()}",
            f"FROM --platform={platform} {self.system_id.linux_distro.value} AS dependencies",
            "WORKDIR /work",
            "COPY provision-plan.json build_system.sh /work/",
            "COPY dependency-inputs /work/dependency-inputs",
            "RUN /bin/bash /work/build_system.sh provision",
            "FROM ${DEPENDENCY_IMAGE} AS build",
            "COPY build_system.sh /work/build_system.sh",
            "COPY build_artifacts.py /work/build_artifacts.py",
            "COPY build-plan.json /work/build-plan.json",
            "COPY sources /work/sources",
            "COPY workspace /work/workspace",
            "RUN --network=none /bin/bash /work/build_system.sh compile",
        ]
        content = "\n".join(dockerfile_lines) + "\n"
        if not self.dockerfile.is_file() or self.dockerfile.read_text() != content:
            self.dockerfile.write_text(content)
        return plan

    def dependency_image(self) -> str:
        """Name the cached dependency image from inputs that can need downloads."""
        digest = hashlib.sha256()
        digest.update(PROVISION_SCHEMA_VERSION.encode())
        path = self.context / "provision-plan.json"
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
        inputs = self.context / "dependency-inputs"
        if inputs.exists():
            for path in sorted(inputs.rglob("*")):
                if path.is_file():
                    digest.update(str(path.relative_to(inputs)).encode())
                    digest.update(path.read_bytes())
        digest.update(self.system_id.linux_distro.value.encode())
        return f"blitz-deps-{self.system_id.to_build_key()}-{digest.hexdigest()[:16]}".lower()

    def dependencies_cached(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.dependency_image()],
                capture_output=True, text=True, check=False,
            )
        except OSError as error:
            raise DockerCacheInspectionError(f"Cannot inspect Docker dependency cache: {error}") from error
        if result.returncode == 0:
            return True
        if "No such image" in result.stderr or "No such object" in result.stderr:
            return False
        raise DockerCacheInspectionError(
            "Cannot inspect Docker dependency cache. Check that Docker is running: "
            + result.stderr.strip()
        )

    def stale_dependency_images(self) -> list[str]:
        """Find older cached dependency images for this exact system profile."""
        prefix = f"blitz-deps-{self.system_id.to_build_key()}-".lower()
        try:
            result = subprocess.run(
                ["docker", "image", "ls", "--format", "{{.Repository}}"],
                capture_output=True, text=True, check=False,
            )
        except OSError as error:
            raise DockerCacheInspectionError(f"Cannot inspect Docker dependency cache: {error}") from error
        if result.returncode != 0:
            raise DockerCacheInspectionError(
                "Cannot list Docker dependency images. Check that Docker is running: "
                + result.stderr.strip()
            )
        current = self.dependency_image()
        return list(dict.fromkeys(
            image for image in result.stdout.splitlines()
            if image.startswith(prefix) and image != current
        ))

    def prune_stale_dependency_images(self) -> list[str]:
        """Remove superseded BLITZ dependency tags only after verifying replacement."""
        if not self.dependencies_cached():
            raise RuntimeError("Cannot remove older Docker images before current dependencies are cached")
        prefix = f"blitz-deps-{self.system_id.to_build_key()}-".lower()
        pattern = re.compile(re.escape(prefix) + r"[0-9a-f]{16}")
        stale = [image for image in self.stale_dependency_images() if pattern.fullmatch(image)]
        if not stale:
            print(f"Docker cache cleanup for {self.system_id.to_build_key()}: no stale dependency images")
            return []
        removed: list[str] = []
        for image in stale:
            try:
                run_command(
                    ["docker", "image", "rm", image],
                    f"Remove stale Docker dependency image {image}",
                    log_path=self._log_path(f"cleanup-{image[-16:]}"),
                )
            except (subprocess.CalledProcessError, OSError) as error:
                # Containers may still use this image. Never force their removal.
                print(f"WARNING: Kept stale Docker image {image}: {error}")
            else:
                removed.append(image)
                print(f"Removed stale Docker dependency image {image}")
        return removed

    def _log_path(self, phase: str) -> Path:
        return self.context.parents[1] / "logs" / self.context.name / f"{phase}.log"

    def cache_dependencies(self) -> None:
        run_command(
            ["docker", "build", "--progress=plain", "--platform", self.system_id.docker_image,
             "--target", "dependencies", "-f", str(self.dockerfile),
             "-t", self.dependency_image(), str(self.context)],
            f"Cache dependencies for {self.system_id.to_build_key()}",
            log_path=self._log_path("dependencies"), show_progress=True,
        )

    def build_prepared(self, dependency_image: str | None = None) -> None:
        if not self.dockerfile.is_file():
            raise FileNotFoundError(f"Prepared Dockerfile not found: {self.dockerfile}. Run discover first.")
        if dependency_image is None and not self.dependencies_cached():
            raise RuntimeError(
                f"Dependencies for {self.system_id.to_build_key()} are not cached. "
                "Connect to the internet and run: python backend/deploy.py cache"
            )
        image = dependency_image or self.dependency_image()
        image_name = f"blitz-build-{self.system_id.to_build_key()}".lower()
        platform = self.system_id.docker_image
        run_command(
            ["docker", "build", "--progress=plain", "--network", "none", "--pull=false",
             "--build-arg", f"DEPENDENCY_IMAGE={image}",
             "--platform", platform,
             "-f", str(self.dockerfile), "-t", image_name, str(self.context)],
            f"Build target bundle for {self.system_id.to_build_key()}",
            log_path=self._log_path("compile"), show_progress=True,
        )
        container_id = run_command(
            ["docker", "create", "--platform", platform, image_name],
            "Create artifact extraction container",
            log_path=self._log_path("create"), show_progress=True,
        ).strip()
        try:
            run_command(
                ["docker", "cp", f"{container_id}:/artifacts/.", str(self.build_path)],
                "Extract target artifacts",
                log_path=self._log_path("extract"), show_progress=True,
            )
        finally:
            run_command(["docker", "rm", container_id], "Remove artifact extraction container",
                        log_path=self._log_path("cleanup"), show_progress=True)

    def build(self, modules: list[Module], bundle_dependencies: bool) -> BuildPlan:
        plan = self.prepare(modules, bundle_dependencies)
        if not self.dependencies_cached():
            self.cache_dependencies()
        self.build_prepared()
        return plan

    @staticmethod
    def prepared_system_ids(build_folder_path: FolderPath, bundle_name: str) -> list[SystemId]:
        contexts = sorted(Path(build_folder_path).resolve().joinpath(bundle_name, "contexts").glob(
            "*"
        ))
        systems: list[SystemId] = []
        for context in contexts:
            if not (context / "Dockerfile").is_file():
                continue
            system = json.loads((context / "build-plan.json").read_text())["system"]
            system_id = SystemId.from_plan_system(system)
            if context.name != system_id.to_build_key():
                raise ValueError(f"Prepared Dockerfile has mismatched system: {context}")
            systems.append(system_id)
        if not systems:
            raise FileNotFoundError("No prepared Dockerfiles found. Run discover first.")
        return systems
