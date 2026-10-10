# Writing `backend/deploy.py`

Moving an older project? Start with [backend migration](backend-migration.md).

For the overall layouts, build/runtime dataflow, library loading, and location
environment variables, see [deployment architecture](deployment-architecture.md).

This guide shows how to declare Python programs, native libraries, and C++/Rust
executables using the deployment APIs. The paths and target names below are
examples: create the corresponding source files before deploying.

All module source folders must live at `backend/<language>/<module-folder>`.
Deployment rejects folders outside this layout, including symlinks that escape
the backend. The configured backend root may have a different name in installer
projects, but the language/module structure stays the same. One module owns one
complete folder, including its supporting source files,
resources, and build configuration. Multiple declarations cannot share a source
folder, even through symlinks. Folder names may differ from module IDs; process
IDs remain separate from module IDs.

Every deployment file has three parts:

1. `ProcessType` names the programs watchdog can run and gives their scheduling weights.
2. `get_modules()` declares source folders, entrypoints, outputs, and dependencies.
3. `pi_name_to_process_types()` assigns programs to discovered devices.

A module's `name` is its unique dependency graph ID. Its
`equivalent_run_definition` identifies the runnable process. Libraries have module
IDs but no process type because watchdog does not launch them.

## 1. Two Python modules with different entry files

Example source layout:

```text
requirements.txt
backend/
├── deploy.py
├── python/
│   ├── common/
│   │   ├── __init__.py
│   │   └── messages.py
│   ├── control/
│   │   ├── main.py
│   │   ├── helpers.py
│   │   └── assets/model.json
│   └── telemetry/
│       └── telemetry.py
├── cpp/
│   └── vision/
└── rust/
    └── telemetry/
```

Use this as a complete `backend/deploy.py` template.
`BackendModules(__file__)` locates the backend beside this deployment file,
including installer projects with a renamed backend folder. Declarations need
only a folder name; paths do not depend on the current working directory.

```python
import base64

from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.module.catalog import BackendModules
from backend.deployment.module.contracts import (
    LaunchSettings,
    ModuleOutputs,
    PythonEntrypoint,
)
from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import ProcessPlan, WeightedProcess

modules = BackendModules(__file__)


class ProcessType(WeightedProcess):
    CONTROL = "control-process", 1.0
    TELEMETRY = "telemetry-process", 0.2


def get_modules() -> list[SupportedModules._Generic]:
    return [
        modules.python(
            "control", process=ProcessType.CONTROL, entrypoint="main.py",
            outputs=ModuleOutputs(resources=("assets/**/*",)),
            launch=LaunchSettings(
                arguments=("--mode", "tracking"),
            ),
        ),
        modules.python("telemetry", process=ProcessType.TELEMETRY, entrypoint="telemetry.py"),
    ]


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        .add(ProcessType.CONTROL)
        .add(ProcessType.TELEMETRY)
        .assign(pi_names)
    )


if __name__ == "__main__":
    config = (
        BlitzNetworkDeployer.Options()
        .set_local_backend_path(modules.backend_path)
        .set_config_supplier(lambda: base64.b64encode(b"{}").decode("ascii"))
        .build()
    )
    BlitzNetworkDeployer.run_cli(
        get_modules(), pi_name_to_process_types, config=config,
    )
```

This requests one control process and one telemetry process **across the fleet**.
On one device, both run there. With several devices, `ProcessPlan` balances their
weights. It does not filter devices by module target requirements; your placement
function must choose compatible devices for restricted programs.

For a program on every discovered device, replace the placement function with:

```python
def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return {
        name: [ProcessType.CONTROL, ProcessType.TELEMETRY]
        for name in pi_names
    }
```

A module declaration selects its entrypoint; the entire folder remains the
module source unit. Supporting files such as `helpers.py` are part of that
module, rather than separate module declarations. The entrypoint selects what
watchdog starts; it does not split the folder into multiple modules.

All Python programs use the single root `requirements.txt` and the device's shared
virtual environment. Their entry files can differ; their installed Python
dependency versions cannot differ. An omitted entrypoint defaults to
`__main__.py`. For a package, use
`PythonEntrypoint(file=None, package="control.worker")` with that package under
the declared source folder.

All module declarations default to `accepts_blitz_flags=False`, so ordinary
programs need no BLITZ argument parser. Programs that parse those flags can use
`launch=LaunchSettings(accepts_blitz_flags=True)` as an explicit compatibility
option, including with older module constructors.
Watchdog still supplies configuration and system information through environment
variables, such as `BLITZ_CONFIG_PATH` and `BLITZ_SYSTEM_NAME`.

### Shared source without sibling imports

Put shared Python code in `backend/python/common/`, with `__init__.py` when
using a regular package. Each Python module receives that folder as `common`:

```python
from common.messages import encode_message
```

Do not import sibling modules. Declaring `dependencies=("vision",)` exposes
compiled native outputs; it does not expose a sibling Python source package.
A module-local `common` folder is rejected when the shared folder exists, to
avoid silently shadowing shared code. Shared code edits rebuild bundles without
invalidating the dependency image.

C++ and Rust shared source can live in `backend/cpp/common/` and
`backend/rust/common/`. Their build files must reference those paths explicitly;
native staging preserves the backend tree so relative references work. Keep
module source, headers, and assets inside backend. The existing root
`requirements.txt` remains the single Python dependency manifest. This source
layout is an application convention, not a security sandbox for arbitrary build
commands or programs.

## 2. Python using a compiled C++ library

Keep the imports and CLI block from example 1. Replace `get_modules()` with:

```python
def get_modules() -> list[SupportedModules._Generic]:
    return [
        modules.cpp_library(
            "vision",
            outputs=ModuleOutputs(
                libraries=("libvision.so",),
                headers=("include/**/*.h",),
            ),
        ),
        modules.python(
            "control", process=ProcessType.CONTROL, entrypoint="main.py",
            dependencies=("vision",),
            outputs=ModuleOutputs(resources=("assets/**/*",)),
        ),
    ]
```

Update the placement function to assign only `ProcessType.CONTROL`. The vision
folder needs a `CMakeLists.txt` that builds `libvision.so`. Library patterns refer
to bundled build outputs; header and resource patterns refer to source files.
Only list patterns for files your project actually produces.

### Complete shared-library example

Create `backend/cpp/vision/CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.16)
project(vision LANGUAGES CXX)
add_library(vision SHARED vision.cpp)
```

Create `backend/cpp/vision/vision.cpp`. `extern "C"` exposes a stable function name
that Python can look up:

```cpp
extern "C" int add(int left, int right) {
    return left + right;
}
```

With the declarations above, Docker compiles this as `libvision.so` and BLITZ
exports it to `backend/lib/vision/libvision.so` in the installed bundle.

Create `backend/python/control/main.py`:

```python
import ctypes
import os
from pathlib import Path

library_path = Path(os.environ["BLITZ_LIB_DIR"]) / "vision" / "libvision.so"
vision = ctypes.CDLL(str(library_path))
vision.add.argtypes = [ctypes.c_int, ctypes.c_int]
vision.add.restype = ctypes.c_int

print(vision.add(20, 22))  # 42
```

Watchdog supplies `BLITZ_LIB_DIR` and the transitive library search directories
before launching Python. No BLITZ command-line flags or custom Python packages
are needed (`ctypes` is in the standard library). This example runs on the Linux
target after bundle installation. A missing library or unresolved dependency
raises `OSError` at `CDLL`; an undeclared/missing C symbol raises `AttributeError`.
Always specify argument and return types to match the native function signature.
Importable Python extensions instead need to match the target Python ABI.

### Transitive dependencies and conflicting library names

For a graph `control → vision → math-core`, declare:

```python
# On the vision module:
dependencies=("math-core",)

# On the control module:
dependencies=("vision",)
```

Also register the `math-core` library in `get_modules()`. Compilation follows the
dependency graph, even if consumers appear first in the list. Native build files
still choose which libraries to link; BLITZ supplies library and header search
paths for the transitive dependencies.

Exports live under `lib/<module-id>/` and `include/<module-id>/`. Independent
programs can each depend on a different provider of `libcommon.so`. If one
program's dependency closure includes two different libraries with the same
filename or ELF SONAME, bundling fails with both providers identified. Namespaced
folders cannot resolve that ambiguity within one process.

### Resources and working directories

Declared resources retain their source-relative paths in the runnable module's
folder and are exported under `resources/<module-id>/`. Watchdog sets the working
directory to the module folder by default, so this works regardless of watchdog's
own working directory:

```python
from pathlib import Path

model = Path("assets/model.json").read_text()
```

An explicit resource path also works if your program changes directories:

```python
import os
from pathlib import Path

model = (Path(os.environ["BLITZ_RESOURCE_DIR"]) / "assets/model.json").read_text()
```

Use `LaunchSettings(working_directory="subfolder", ...)` for a different module
working directory. Paths must stay inside the module. Arguments are tuples of
individual arguments, not a shell command string.

## 3. C++ and Rust executables

Keep the imports and CLI block from example 1. Replace `ProcessType`,
`get_modules()`, and placement with:

```python
class ProcessType(WeightedProcess):
    MOTOR = "motor-process", 1.0
    TELEMETRY = "telemetry-process", 0.2


def get_modules() -> list[SupportedModules._Generic]:
    return [
        modules.cpp("motor", process=ProcessType.MOTOR, executable="main"),
        modules.rust("telemetry", process=ProcessType.TELEMETRY),
    ]


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        .add(ProcessType.MOTOR)
        .add(ProcessType.TELEMETRY)
        .assign(pi_names)
    )
```

`backend/cpp/motor/CMakeLists.txt` must produce an executable named `main`.
`backend/rust/telemetry/Cargo.toml` must define a binary named `telemetry`.
`executable` selects the compiled executable and defaults to the module name.
C++ defaults to CMake; pass `compilation=CPPBuildConfig(...)` for a custom build.
Use `modules.rust_library("math", outputs=ModuleOutputs(libraries=("libmath.so",)))`
for a Rust library; its Cargo crate type determines the output format.
The older typed constructors remain supported for existing deployment files.

## Optional target restrictions

Import the target types:

```python
from backend.deployment.compilation.util.systems import Architecture
from backend.deployment.module.contracts import CapabilityRequirement, TargetRequirements
```

Add this keyword to a module that specifically requires ARM64 and CUDA 12.2:

```python
targets=TargetRequirements(
    architectures=(Architecture.AARCH64,),
    capabilities=(CapabilityRequirement("cuda", minimum_version="12.2"),),
)
```

Restrictions can also specify `distros` and exact `(major, minor)`
`python_versions`. Ordinary Raspberry Pis do not satisfy the CUDA requirement.
The build skips incompatible modules and their consumers; assigning an
incompatible process fails before compilation or transfer. Provision a suitable
CUDA toolkit separately through the existing native dependency configuration;
detecting CUDA driver support does not install it.

## Running the examples

Run from the repository root with Docker available:

```bash
.venv/bin/python backend/deploy.py
```

The default command discovers devices, records profiles, prepares Dockerfiles,
checks cached dependencies, builds bundles, and distributes them. Docker is the
compilation environment; the target receives bundles, not a Docker runtime image.
Generated contexts and bundles are under `build/backend-bundle/`.

Each target keeps one installed bundle in its `backend/` folder. Installing a new
bundle removes files and module folders absent from the replacement, while
preserving `backend/deployment/` and the root package marker used by watchdog.
Extraction uses a temporary folder that is cleaned on completion or failure.
After installation and offline dependency installation succeed, deployment
removes ZIP transfers and their legacy extracted folders from the dedicated
target transfer directory (normally `bundles/`). A failed dependency installation
retains the incoming ZIP for retry. Build-machine Docker caches and bundles stay
available for the next deployment.

To select a device without mDNS discovery:

```bash
.venv/bin/python backend/deploy.py --device raspberrypi.local:9999
```

If dependencies are missing, the command records the discovered systems and
stops with instructions. Connect to the internet and run:

```bash
.venv/bin/python backend/deploy.py cache
```

Then reconnect to the device network and rerun the default command. Dependency
changes or new target profiles require cache preparation. Source, entrypoint,
and resource edits reuse dependency images and rebuild the bundle. When an older
dependency image exists, deployment may offer an explicit override; that does
not guarantee newly requested dependencies are available.

For a working source fixture with transitive libraries, two Python entrypoints,
resources, and independent `libcommon.so` providers, see
[`module_contract_backend`](../__tests__/fixtures/module_contract_backend/deploy.py).
Its Docker coverage is in
[`module_contract_docker_tests.py`](../__tests__/module_contract_docker_tests.py).
