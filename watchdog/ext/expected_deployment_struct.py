from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUninitializedInstanceVariable=false, reportUnusedParameter=false

from typing import Any

from watchdog.util.lazy_importer import lazy_import_class, lazy_import_function


DEFAULT_DEPLOY_MODULE = "backend.deploy"
DEFAULT_RUNTIME_BUNDLE_PATH = "backend"


@lazy_import_class("backend.deployment.processes")
class WeightedProcess:
    def get_name(self) -> str: ...

    def get_weight(self) -> float: ...


@lazy_import_class("backend.deployment.module.base")
class Module:
    name: str

    def get_language_name(self) -> str: ...

    def get_project_path(self, bundle_path: Any) -> Any: ...


@lazy_import_class("backend.deployment.module.base")
class RunnableModule(Module):
    extra_run_args: list[tuple[str, str]]
    equivalent_run_definition: WeightedProcess

    def get_run_command(self, bundle_path: Any) -> str: ...


@lazy_import_class("backend.deployment.module.supported")
class SupportedModules:
    _Generic: type[Module]
    CPPLibraryModule: type[Module]
    CPPRunnableModule: type[RunnableModule]
    PythonModule: type[RunnableModule]
    RustModule: type[RunnableModule]
    GeneratedModule: type[Module]


@lazy_import_function(DEFAULT_DEPLOY_MODULE)
def get_modules() -> list[Module]: ...


@lazy_import_function(DEFAULT_DEPLOY_MODULE)
def pi_name_to_process_types(
    pi_names: list[str],
) -> dict[str, list[WeightedProcess]]: ...
