from __future__ import annotations

from backend.deployment.processes import WeightedProcess as BackendWeightedProcess
from watchdog.ext.expected_deployment_struct import (
    Module,
    RunnableModule,
    SupportedModules,
    WeightedProcess,
    get_modules,
    pi_name_to_process_types,
)


class SampleProcess(BackendWeightedProcess):
    SAMPLE = "sample", 1.0


def test_deployment_stubs_resolve_backend_modules():
    modules = get_modules()

    assert isinstance(modules, list)
    assert all(isinstance(module, Module) for module in modules)


def test_runnable_module_stub_exposes_process_and_command_contract():
    runnable_module = SupportedModules.PythonModule(
        name=SampleProcess.SAMPLE.get_name(),
        extra_run_args=[],
        equivalent_run_definition=SampleProcess.SAMPLE,
        module_folder_path="backend/python/sample",
    )

    assert isinstance(runnable_module, RunnableModule)
    assert isinstance(runnable_module.equivalent_run_definition, WeightedProcess)
    assert runnable_module.equivalent_run_definition.get_name()
    assert runnable_module.get_run_command("backend")


def test_supported_modules_stub_resolves_nested_module_classes():
    python_module_class = SupportedModules.PythonModule
    generated_module_class = SupportedModules.GeneratedModule

    assert python_module_class.__name__ == "PythonModule"
    assert generated_module_class.__name__ == "GeneratedModule"


def test_lazy_deploy_function_stub_resolves_process_mapper():
    process_mapping = pi_name_to_process_types(["test-pi"])

    assert list(process_mapping.keys()) == ["test-pi"]
    assert isinstance(process_mapping["test-pi"], list)
    assert all(
        isinstance(process, WeightedProcess) for process in process_mapping["test-pi"]
    )
