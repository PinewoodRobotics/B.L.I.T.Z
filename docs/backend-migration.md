# Migrating an older backend to the module system

Use this guide **after updating BLITZ itself with the updater**. It covers your
application's source layout, declarations, imports, build files, and runtime
paths. Updating the tooling does not automatically reorganize your application.

Older releases and custom projects have different layouts. Match your project
to the patterns below rather than assuming every historical version used the
same API. For complete API examples, see [deployment examples](deployment-examples.md);
for build and target behavior, see [deployment architecture](deployment-architecture.md).

## 1. Record what the old deployment does

Create a source-control checkpoint before moving files. List:

- Each program's entrypoint, process name, arguments, configuration, and device assignment.
- Each native library, its consumers, build command, exported headers, and runtime dependencies.
- Shared helpers, models, configuration files, and other assets.
- Python requirements and native dependency manifests, including versions.
- Architecture, distro, Python ABI, or hardware restrictions such as CUDA.

Keep existing **process IDs** and placement behavior unless you intend to change
them. Moving a folder does not require renaming the process watchdog runs.
Keep updater/installer files, Gradle integration, and BLITZ's `backend/deployment/`
tooling; those are not application modules to move into a language folder.

## 2. Move application source into the target layout

```text
project/
├── requirements.txt                 One shared Python dependency file
├── backend/
│   ├── deploy.py                     Declarations and process placement
│   ├── deployment/                   BLITZ tooling; leave in place
│   ├── python/
│   │   ├── common/                   Shared Python helpers
│   │   │   ├── __init__.py
│   │   │   └── messages.py
│   │   ├── control/
│   │   │   ├── main.py
│   │   │   ├── helpers.py
│   │   │   └── assets/model.json
│   │   └── telemetry/
│   │       └── main.py
│   ├── cpp/
│   │   ├── common/                   Shared headers/source, if needed
│   │   └── vision/
│   │       ├── CMakeLists.txt
│   │       ├── vision.cpp
│   │       └── include/
│   └── rust/
│       └── motor/
│           ├── Cargo.toml
│           ├── Cargo.lock
│           └── src/main.rs
└── build/backend-bundle/             Generated locally during deployment
```

Every module owns **one complete folder**, directly under
`backend/<language>/<module-folder>`. All its source, supporting files, assets,
and build configuration belong there. An installer project may use a differently
named backend root; the language/module convention remains the same.

| Older arrangement | Migration |
| --- | --- |
| `backend/main.py` plus helpers | Move into `backend/python/control/`; select `main.py` as its entrypoint. |
| Two programs declared from the same folder | Give each program its own module folder. Move shared helpers to `python/common/`. |
| `backend/python/group/control/` | Move `control/` directly under `backend/python/`. |
| C++ or Rust project outside backend | Move the entire subproject into `backend/cpp/<name>/` or `backend/rust/<name>/`. |
| One folder mixing Python, C++, and Rust subprojects | Split into language-specific modules; declare native dependency edges between them. |
| Shared Python helpers imported from another runnable module | Move the shared code into `backend/python/common/`; update imports. |
| Assets loaded from a developer's absolute path | Move into their owning module and declare resource exports. |
| Multiple Python requirements files or per-program environments | Consolidate into root `requirements.txt`; resolve incompatible versions. |
| Hand-copied native binaries or application Dockerfiles | Declare native outputs and build configuration; let deployment generate target Dockerfiles. |

A module folder is not discovered merely because it exists: register it in
`get_modules()`. Do not register `common/` as a module. Symlinks that escape the
backend root are rejected; linking to an external source directory is not a
substitute for moving it.

Module IDs must be globally unique across languages. With the convenience API,
the ID is also the source folder name: do not register both `python/worker` and
`rust/worker` under ID `worker`. Rename one folder/ID, such as `rust-worker`.
Older typed constructors remain supported and can keep an ID different from its
folder name, but still enforce the same source layout and folder ownership.

If a native subproject produces both an executable and a library, use **one
runnable module declaration** with both output types. Do not declare a library
and runnable module that share its source folder.

## 3. Update `backend/deploy.py`

Keep the public hooks `get_modules()` and `pi_name_to_process_types()`.
`BackendModules(__file__)` finds the backend beside the deployment file; you do
not need `ROOT / "backend/cpp/vision"` or machine-specific source paths.

This complete template matches the tree above. Replace the example process names
with your existing IDs, and retain your project's configuration supplier and
placement rules where applicable.

```python
import base64

from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.module.catalog import BackendModules
from backend.deployment.module.contracts import ModuleOutputs
from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import ProcessPlan, WeightedProcess

modules = BackendModules(__file__)


class ProcessType(WeightedProcess):
    CONTROL = "control-process", 1.0
    TELEMETRY = "telemetry-process", 0.2
    MOTOR = "motor-process", 0.5


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
        modules.python(
            "telemetry", process=ProcessType.TELEMETRY, entrypoint="main.py",
        ),
        modules.rust("motor", process=ProcessType.MOTOR, executable="motor"),
    ]


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        .add(ProcessType.CONTROL)
        .add(ProcessType.TELEMETRY)
        .add(ProcessType.MOTOR)
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

The CMake project must actually produce `libvision.so`; Cargo must produce an
executable named `motor`. Change declarations to match your actual artifacts.
For a C++ executable use `modules.cpp(...)`; for a pure Rust library use
`modules.rust_library(...)`. See the [native examples](deployment-examples.md).

The template requests one instance of each process **across the fleet**. Do not
replace an existing per-device mapping with it unless that is your intended
behavior. A module ID identifies a dependency provider; a process ID identifies
what watchdog starts. They can differ. When renaming a module ID, update all
`dependencies` references and paths into that module's exported libraries.

## 4. Fix Python imports and dependencies

Inside a module, retain its private helper files and adjust imports for the new
entrypoint location. A file entrypoint defaults to `__main__.py`; explicitly set
`entrypoint="main.py"` or another relative file if needed. For `python -m`, use
`PythonEntrypoint(file=None, package="control.worker")`, with that package
inside the module folder.

Shared code is imported through `common`:

```python
from common.messages import encode_message
```

Do not import a sibling runnable module. A declaration such as
`dependencies=("vision",)` exposes compiled exports; it does not add another
Python module's source folder to `PYTHONPATH`. Avoid a module-local `common/`
folder when the shared `python/common/` exists, because that conflict is rejected.

All Python processes use a single target virtual environment and the project's
root `requirements.txt`. The current model cannot give two Python processes
conflicting installed package versions. Resolve those requirements before
deployment; moving files alone does not resolve the conflict.

## 5. Fix native builds and library consumers

- Update CMake source paths, include directories, and Cargo workspace/path
  dependencies after moving projects. Shared native source may live in
  `cpp/common/` or `rust/common/`; reference it explicitly in build files.
- Keep custom C++ build settings in the existing `CPPBuildConfig` API. Do not
  replace generated target Dockerfiles with separate application build pipelines.
- Declare exported libraries/executables with patterns relative to build
  artifacts; declare headers/resources relative to source. Do not assume every
  native source file is copied into the target runtime bundle.
- Declare every native dependency edge. For `control → vision → math-core`,
  `control` depends on `vision`, and `vision` depends on `math-core`.
- Dependency declarations provide build order and transitive search paths.
  CMake/Cargo must still specify actual includes and link dependencies.

At runtime, native libraries live under `lib/<module-id>/`. Python can load a
C-compatible export without a BLITZ command-line flag:

```python
import ctypes
import os
from pathlib import Path

vision = ctypes.CDLL(
    str(Path(os.environ["BLITZ_LIB_DIR"]) / "vision" / "libvision.so")
)
vision.add.argtypes = [ctypes.c_int, ctypes.c_int]
vision.add.restype = ctypes.c_int
print(vision.add(20, 22))
```

This requires a native `add(int, int)` function exported with a C ABI, for
example C++ `extern "C"`. Match signatures exactly. Watchdog supplies the
transitive library search paths before launch. Python extension modules also
need to match the target Python ABI.

Namespacing lets independent processes use different providers of
`libcommon.so`. If a single process depends on two libraries with the same
filename or ELF SONAME, bundling rejects the ambiguity; rename/rebuild one
provider instead of relying on folder names to solve it.

## 6. Replace old location assumptions and flags

Watchdog starts programs with the module folder as their working directory by
default. Use `LaunchSettings(working_directory="subfolder")` only when needed.
For resource paths that survive a program changing directories:

```python
import os
from pathlib import Path

model_path = Path(os.environ["BLITZ_RESOURCE_DIR"]) / "assets/model.json"
model = model_path.read_text()
```

Declare that asset through `ModuleOutputs(resources=("assets/**/*",))`.
Use `BLITZ_MODULE_DIR` for the deployed module location and `BLITZ_LIB_DIR` for
the bundle's library root. `Path(__file__).resolve().parent` is also useful for
Python files beside the current script. These runtime locations differ from
the development checkout; remove assumptions about its absolute path.

BLITZ command-line flags are disabled by default. Prefer watchdog's environment
values such as `BLITZ_CONFIG_PATH` and `BLITZ_SYSTEM_NAME`. A legacy program that
still parses BLITZ flags can temporarily opt in with
`LaunchSettings(accepts_blitz_flags=True)`. Put application arguments in
`LaunchSettings(arguments=("--mode", "tracking"))`, as individual argv values.

## 7. Restore target restrictions and deployment behavior

Attach `TargetRequirements` to modules that require particular architectures,
distros, Python versions, or capabilities. For example,
`capabilities=(CapabilityRequirement("cuda", "12.2"),)` restricts a module to
profiles advertising an adequate CUDA version. Do not treat every ARM device
as a CUDA-capable Jetson.

Restrictions apply transitively to consumers. All compatible declared modules
are built for each system profile, regardless of later process placement.
`ProcessPlan` balances weights but does not choose devices by these constraints;
keep restricted programs assigned to compatible devices in your placement hook.

Run commands from the project root. The source catalog resolves paths from
`deploy.py`, but requirements/build settings can still be relative to the working
directory.

```sh
# Discover, check the dependency cache, build offline, and deploy.
.venv/bin/python backend/deploy.py

# Optional: pin a watchdog address instead of relying on mDNS.
.venv/bin/python backend/deploy.py --device pi.local:5000

# After discovery, connect the build computer to the internet to prepare caches.
.venv/bin/python backend/deploy.py cache
```

When a profile or dependency is uncached, the deployment cannot complete its
normal offline build. Prepare it with `cache`, reconnect to the devices, and
rerun deployment. An offered override can reuse older dependencies, but does not
make them satisfy new requirements. Source/resource edits normally reuse the
dependency image; dependency changes require cache preparation.

Generated Dockerfiles, contexts, bundles, inventory, and logs belong under
`build/backend-bundle/`; do not move application sources there or edit generated
Dockerfiles to register modules. Keep build artifacts out of source control.
Existing Gradle `deployBackend` integration remains supported.

## 8. Validate before deploying to your fleet

After creating the declared folders, run this structural check from the project
root (change `backend` if your configured root has another name):

```python
# Save as a temporary local check, or run in a Python session from the project root.
import runpy
from pathlib import Path

from backend.deployment.module.graph import ModuleGraph
from backend.deployment.module.layout import validate_backend_layout

deployment = runpy.run_path("backend/deploy.py")
declared = deployment["get_modules"]()
validate_backend_layout(declared, str(Path("backend").resolve()))
print("Build order:", [module.name for module in ModuleGraph(declared).ordered])
print("Sample placement:", deployment["pi_name_to_process_types"](["test-pi"]))
```

This checks declarations, ownership, dependency IDs/cycles, and source boundaries.
It does not prove that native compilation, linking, target hardware, or runtime
imports work. Complete one target build and test each process, its resources, and
its native library calls before rolling out to the fleet.

| Failure after migration | Check |
| --- | --- |
| Module must live in a language folder | Move the source to a direct language child; check symlink destinations and configured root. |
| Duplicate module ID or source folder | Give each declaration a unique ID and unique folder; combine native outputs from one subproject. |
| Duplicate process ID | Preserve unique runnable process definitions; libraries have no process definition. |
| Unknown dependency or dependency cycle | Update renamed IDs and remove cyclic dependency edges. |
| Python import failure | Fix local/package imports or move shared helpers to `python/common/`; check shared requirements. |
| Missing library or unresolved native symbol | Check output patterns, exported ABI, linker configuration, and transitive dependencies. |
| Missing assets | Check resource patterns and use runtime locations rather than the checkout path. |
| Process incompatible with target | Check declared restrictions and device placement. |
| Dependency image missing or outdated | Prepare matching dependencies online with `cache`, then retry offline. |

Deploying replaces the target's active application bundle, including removing
obsolete application files. There is one active bundle, but replacement is not
an atomic, rollback-safe release switch. Keep your source checkpoint and test a
device first. Remembered offline devices are not automatically retired just
because they are absent from a discovery run.
