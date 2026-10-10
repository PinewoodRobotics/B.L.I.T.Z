if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import re
import shutil
import hashlib
from pathlib import Path
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    SystemId,
    PythonVersion,
)
from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.module.graph import ModuleGraph
from backend.deployment.module.layout import validate_backend_layout
from backend.deployment.module.base import (
    CompilableModule,
    Module,
    VerificationResult,
    matches_module_type,
)
import os

from backend.deployment.network_api.utils import FilePath, FolderPath


class CodeBundler:
    def __init__(
        self,
        modules: list[Module],
        backend_local_path: FolderPath,
        build_folder_path: FolderPath,
        output_folder_path: FolderPath,
        system_id: SystemId,
        bundle_name: str = "backend-bundle",
        bundle_dependencies: bool = True,
        additional_files: list[FilePath] | None = None,
    ):
        self.modules: list[Module] = modules
        self.backend_local_path: FolderPath = backend_local_path
        self.build_folder_path: FolderPath = build_folder_path
        self.output_folder_path: FolderPath = output_folder_path
        self.system_id: SystemId = system_id
        self.bundle_name: str = bundle_name
        self.system_key: str = self.system_id.to_build_key()
        self.bundle_root = FolderPath(os.path.join(build_folder_path, bundle_name))
        self.artifact_root = FolderPath(os.path.join(self.bundle_root, "artifacts"))
        self.build_path = FolderPath(
            os.path.join(self.artifact_root, self.system_key)
        )
        self.context_path = FolderPath(
            os.path.join(self.bundle_root, "contexts", self.system_key)
        )
        self.bundle_dependencies: bool = bundle_dependencies
        self.additional_files: set[FilePath] = {
            FilePath(os.path.join(backend_local_path, "deploy.py"))
        } | set(additional_files or [])

    def prepare(self) -> None:
        validate_backend_layout(self.modules, self.backend_local_path)
        for module in ModuleGraph(self.modules).compatible(self.system_id):
            self.verify_module(module)
        SystemBuilder(self.system_id, self.build_path, self.context_path, self.backend_local_path).prepare(
            self.modules, self.bundle_dependencies
        )

    def bundle(
        self, *, prepared: bool = False, dependency_image: str | None = None
    ) -> FilePath:
        validate_backend_layout(self.modules, self.backend_local_path)
        os.makedirs(self.build_folder_path, exist_ok=True)
        os.makedirs(self.output_folder_path, exist_ok=True)

        bundle_root_path = self.artifact_root
        os.makedirs(bundle_root_path, exist_ok=True)

        build_path = self.build_path
        if os.path.exists(build_path):
            if os.path.isdir(build_path):
                shutil.rmtree(build_path)
            else:
                os.unlink(build_path)
        os.makedirs(build_path, exist_ok=True)

        system_builder = SystemBuilder(self.system_id, build_path, self.context_path, self.backend_local_path)
        if prepared:
            system_builder.build_prepared(dependency_image=dependency_image)
        else:
            for module in ModuleGraph(self.modules).compatible(self.system_id):
                self.verify_module(module)
            system_builder.build(self.modules, self.bundle_dependencies)
        shutil.copyfile(
            system_builder.context / "build-plan.json",
            os.path.join(build_path, "build-plan.json"),
        )

        for module in ModuleGraph(self.modules).compatible(self.system_id):
            build_output_path = FolderPath(
                os.path.join(build_path, module.get_language_name(), module.name)
            )
            os.makedirs(build_output_path, exist_ok=True)

            if matches_module_type(module, CompilableModule):
                self.link_module(module, build_path)

        for additional_file in self.additional_files:
            _ = shutil.copy(
                additional_file,
                build_path,
            )

        # deploy.py imports this API on the target. Ship the library that built
        # the bundle rather than relying on the watchdog's installed copy.
        runtime_path = Path(build_path) / "deployment"
        shutil.copytree(
            Path(__file__).resolve().parent,
            runtime_path,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.pyo", ".DS_Store", ".blitz-runtime-id"
            ),
        )
        revision = hashlib.sha256()
        for path in sorted(runtime_path.rglob("*")):
            if path.is_file():
                revision.update(path.relative_to(runtime_path).as_posix().encode())
                revision.update(b"\0")
                revision.update(path.read_bytes())
                revision.update(b"\0")
        (runtime_path / ".blitz-runtime-id").write_text(revision.hexdigest() + "\n")

        archive_base_path = FilePath(
            os.path.join(self.output_folder_path, self.system_key)
        )

        archive_path = shutil.make_archive(
            archive_base_path,
            "zip",
            root_dir=bundle_root_path,
            base_dir=self.system_key,
        )

        return FilePath(archive_path)

    def verify_module(self, module: Module):
        success, error_message = module.verify()
        if success.value == VerificationResult.FATAL.value:
            raise Exception(
                f"Module {module.name} verification failed: {error_message}"
            )

        if success.value == VerificationResult.WARNING.value and not self.__question_user(
            f"Module {module.name} verification failed: {error_message}. Continue anyway?"
        ):
            raise Exception(
                f"Module {module.name} verification failed: {error_message}"
            )

    def link_module(self, module: CompilableModule, build_output_path: FolderPath):
        linking_path = FolderPath(
            os.path.join(
                build_output_path,
                "link",
                module.get_language_name(),
                module.name,
            )
        )
        os.makedirs(linking_path, exist_ok=True)

        files = self.__get_all_files_matching_pattern(
            module.get_project_path(build_output_path), module.get_link_file_pattern()
        )

        for file in files:  # copying here is not ideal but will have to do for now
            _ = shutil.copy(file, os.path.join(linking_path, os.path.basename(file)))

    def __get_all_files_matching_pattern(
        self, directory_path: FolderPath, pattern: re.Pattern[str]
    ) -> list[FilePath]:
        matched_files: list[FilePath] = []
        for root, _, files in os.walk(directory_path):
            for filename in files:
                if pattern.match(filename):
                    matched_files.append(FilePath(os.path.join(root, filename)))
        return matched_files

    def __question_user(self, question: str) -> bool:
        return input(f"{question} (y/n): ").lower() == "y"


if __name__ == "__main__":
    bundler = CodeBundler(
        modules=[],
        backend_local_path=FolderPath("backend/"),
        build_folder_path=FolderPath("build/"),
        output_folder_path=FolderPath("build/output/"),
        bundle_name="backend-bundle",
        system_id=SystemId(
            c_lib_version="2.39",
            linux_distro=LinuxDistro.JETPACK_L4T_R36_2,
            architecture=Architecture.AARCH64,
            python_version=PythonVersion(major=3, minor=12),
        ),
        bundle_dependencies=False,
        additional_files=[FilePath("backend/deploy.py")],
    )

    _ = bundler.bundle()
