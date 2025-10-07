from backend.deployment.util import (
    CommonModule,
    PythonModule,
    set_modules,
    with_automatic_discovery,
    with_custom_backend_dir,
)


def get_modules() -> list[CommonModule] | CommonModule:
    return [
        PythonModule(
            local_root_folder_path="./pose_extrapolator",
            local_main_file_path="main",
            extra_run_args=[],
            equivalent_run_definition="pose_extrapolator",
        )
    ]


set_modules(get_modules())

with_custom_backend_dir("~/Documents/B.L.I.T.Z/backend")
with_automatic_discovery()
