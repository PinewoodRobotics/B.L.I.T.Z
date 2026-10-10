# B.L.I.T.Z

Multi-process robotics stack with a Python watchdog, codegen, and deploy tooling.

## Install BLITZ

Run this command on the machine you want to set up:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/install.sh)"
```

Choose **Coprocessor** to install the target watchdog, or
**Development computer** from a project directory to install the Python
deployment backend. On the development computer, choose `wpilib` integration
for a Java WPILib project; otherwise choose `none`.

For automation, set `BLITZ_INSTALL_TARGET=coprocessor` or
`BLITZ_INSTALL_TARGET=development`. The development installer also accepts
`BLITZ_SETUP=wpilib` and `BLITZ_PROJECT=/path/to/project`.

## Development backend

This installs `backend/deployment`, `backend/deploy.py`, and
`scripts/backend.sh`. The version stamp at
`backend/deployment/.blitz-build-version` identifies the backend folder: the
backend folder is the parent of `deployment/`. Reinstalling preserves your
`deploy.py`. Run `scripts/backend.sh` to deploy, check updates, or see the
detected backend location. The local tool no longer creates language modules.

For a non-interactive installation into another project, set `BLITZ_PROJECT`
to its root. Set `BLITZ_BACKEND_DIR` to choose a different backend folder; the
installer adds a `backend` import alias because the Python API uses that package
name.

Discovery immediately generates one Dockerfile and build context for each
distinct discovered system ID. The Dockerfile and its build inputs are kept under
`build/backend-bundle/contexts/<system-id>/`. Its base image matches the
target distribution and architecture. The adjacent `build-plan.json` lists
every module declared by `get_modules()`, plus ordered dependency and build
steps. `build_system.sh` provisions the image in a cached Docker layer, then
executes the complete build plan after sources are copied into the image.
BLITZ extracts the resulting C++, Rust, and Python artifacts into the usual
zip bundle, including a copy of the plan, and sends the zip to the target. The
Docker image is only a build environment and is never run on the target.

```text
build/
  backend-bundle/
    contexts/<system-id>/        Dockerfile, build script, plans, staged sources
    systems.json                  saved device identities and system types
    artifacts/<system-id>/       extracted files before packaging
    logs/<system-id>/            Docker dependency, compile, and extraction logs
    outputs/<system-id>.zip      finished bundle
    outputs/bundle-index.json    bundle checksums
```

Run one deployment command from the project root while connected to the devices:

```bash
python3 backend/deploy.py
```

This discovers watchdogs through mDNS, records their identities and system types
in `build/backend-bundle/systems.json`, refreshes the Dockerfiles and build
inputs, checks the local Docker dependency images, compiles bundles with network
access disabled, and distributes them. If requirements changed and an older
dependency image for the same system is still cached, deployment asks whether
to continue with that image. The default answer is no; continuing may leave
out new dependencies or fail compilation. If there is no cached image for a
system type, deployment stops before building or transferring bundles. To
refresh dependencies, connect the build machine to the internet and run:

```bash
python3 backend/deploy.py cache
```

The cache command uses recorded system types without contacting devices.
Reconnect to the device network and rerun `python3 backend/deploy.py`. Source
changes alone do not invalidate dependency images. Python wheels and Rust crates
are downloaded during online cache preparation; C++ dependency commands also
run there. The device never runs the Docker image and installs Python wheels
from the bundle without internet access.

Docker builds show each dependency or compilation step as it starts and ends.
Full output is saved in `build/backend-bundle/logs/<system-id>/` (including
`dependencies.log` and `compile.log`). If a step fails, the terminal reports
its phase, step, module, exit code, and log path, followed by the recent Docker
output. Set `BLITZ_VERBOSE=1` to stream every Docker output line while it runs.

The self-contained backend in `__tests__/fixtures/bundling_backend/` exercises
C++ and Rust libraries and executables. Run
`.venv/bin/python -m pytest __tests__/native_bundle_tests.py` to build its
Docker bundle, inspect the zip, and execute all four artifacts in a container.

If mDNS is unavailable, pin watchdog addresses with `--device HOST:PORT`, for
example `python3 backend/deploy.py --device 192.168.1.50:5000`. The flag is
repeatable. Pinned discovery queries each watchdog's `/get/system/identity`
endpoint instead of using mDNS.

If a device is unavailable but its system build key is known, prepare its cache
without contacting the device:

```bash
python3 backend/deploy.py cache --system-id 2.36-aarch64-debian-12-python3-11
```

This records the profile but does not select a deployment destination. The
resulting zip bundles and checksum index are under
`build/backend-bundle/outputs/`; extracted artifacts are under
`build/backend-bundle/artifacts/`. Keep this folder and Docker's local images
when switching networks. Cross-architecture targets require Docker support
for the target platform. WPILib projects can use `deployBackend` and
`cacheBackend`; the installed `scripts/backend.sh` menu provides Deploy and
Cache dependencies. Automation can set `BLITZ_BACKEND_ACTION` to `deploy` or
`cache`.

## WPILib Java Project Setup

Choose `wpilib` integration when installing the development backend in a Java
WPILib project, or set `BLITZ_SETUP=wpilib` for automation.

WPILib setup adds the Gradle `deployBackend` task by setting `backendPath` in
`settings.gradle` or `settings.gradle.kts` and applying the task script in
`backend/deployment/gradle`. An existing backend can add this integration with
`BLITZ_BACKEND_ACTION=setup-wpilib bash scripts/backend.sh`.

Run the Gradle task with Gradle's own console output muted so BLITZ can keep
control of the terminal:

```bash
./gradlew --console=plain --quiet deployBackend
```

The previous `install_on_wpilib.sh` entry point remains available for existing
WPILib installation workflows.

## Quickstart (local)

```bash
make setup
make set-name NAME=dev
make generate
make run
```

## Tests

The default test suite includes Docker-based installation tests. Start Docker
before running tests.

```bash
make test
```

## Deploy to a target machine

```bash
make deploy-sync
make deploy
```

### Module entrypoints, libraries, resources, and target constraints

For an existing project, follow [backend migration](docs/backend-migration.md)
to reorganize older layouts after updating BLITZ.

See [deployment architecture](docs/deployment-architecture.md) for the backend
and frontend layouts, deployment dataflow, target bundle retention, native
library linking/loading, and runtime paths and flags.

See [deployment examples](docs/deployment-examples.md) for a complete
`backend/deploy.py` template, two Python module entrypoints, Python using a C++ library,
C++/Rust executables, resources, target restrictions, and deployment commands.

All module sources live under `backend/<language>/<module-folder>`. One module
owns one complete folder; different entry files cannot be registered as separate
modules sharing that folder. Shared
Python source lives in `backend/python/common/`; sibling modules are not added
to Python import paths. Native common folders remain accessible to build files
inside the backend tree.

Keep module declarations in `get_modules()` and assign their process types in
`pi_name_to_process_types()`. Module `name` is a globally unique ID; a runnable
module's `equivalent_run_definition` supplies its process ID. These IDs may differ.
Existing positional constructors and default Python `__main__.py` entrypoints
remain supported.

```python
from backend.deployment.module.contracts import (
    CapabilityRequirement, LaunchSettings, ModuleOutputs,
    PythonEntrypoint, TargetRequirements,
)

from backend.deployment.module.catalog import BackendModules

modules = BackendModules(__file__)

# Each module owns a different folder; both use the shared requirements.
modules.python(
    "camera", process=ProcessType.CAMERA, entrypoint="camera.py",
    dependencies=("vision-library",),
    outputs=ModuleOutputs(resources=("assets/**/*",)),
    launch=LaunchSettings(arguments=("--mode", "tracking")),
)
modules.python("navigation", process=ProcessType.NAVIGATION, entrypoint="navigation.py")
```

Use `PythonEntrypoint(file=None, package="control.worker")` for `python -m`.
C++ and Rust runnable modules use `runnable_name` to select their compiled
executable. Watchdog passes argument lists directly, uses an absolute interpreter
and executable path, and sets the working directory to the bundled module folder.
`LaunchSettings.working_directory` can select a subfolder. Program paths and
arguments can contain spaces. BLITZ CLI flags are disabled by default. Legacy
programs can explicitly opt in
with `LaunchSettings(accepts_blitz_flags=True)`.
BLITZ also supplies those values through environment variables, including
`BLITZ_CONFIG_PATH`, `BLITZ_BUNDLE_FOLDER_PATH`, and `BLITZ_SYSTEM_NAME`.

Declare module dependencies by ID, for example `dependencies=("math-library",)`.
The builder rejects unknown IDs, duplicate module/process IDs, and dependency
cycles, then orders compilation across Python, C++, and Rust modules. It builds
all compatible declared modules for each profile, regardless of process assignment.
Native consumers receive `LIBRARY_PATH`, `LD_LIBRARY_PATH`, `CPATH`,
`CMAKE_LIBRARY_PATH`, `CMAKE_INCLUDE_PATH`, and Rust native search flags for their
transitive dependencies. `BLITZ_INCLUDE_DIR/<module-id>` provides an explicit,
namespaced header root. Build commands still choose which libraries to link.

`ModuleOutputs` accepts relative glob patterns:

- `libraries` and `executables` are relative to the module's bundled native build
  outputs. Unspecified library patterns export all recognized native libraries.
- `headers` and `resources` are relative to the source folder. Declared files must
  exist; missing outputs and invalid native entrypoints fail the build.
- Header exports appear under `include/<module-id>/`; library exports appear
  under `lib/<module-id>/`. Resources appear under `resources/<module-id>/` and
  retain their relative paths in the runnable module folder as well.

At runtime, `runtime-manifest.json` records each module's transitive library
search directories. Watchdog exposes `BLITZ_LIB_DIR`, `BLITZ_MODULE_DIR`, and
`BLITZ_RESOURCE_DIR`. Python receives its own module and library directories in
`PYTHONPATH`, supporting compatible Python extension modules. Shared-library
loading uses each program's dependency closure; it does not inherit the deploying
computer's library search paths. The builder checks native dependencies
recursively, packages required system libraries, and rejects unresolved libraries.
Target glibc and NVIDIA driver libraries remain supplied by the device.

Two independent programs may depend on different modules that each export
`libcommon.so`. Their library directories remain isolated. If a single dependency
closure contains different libraries with the same filename or ELF SONAME, the
build fails and names both providers; a search-path ordering cannot safely resolve
that ambiguity. Rename/relink those providers or choose one implementation.
Static `.a` libraries are compile inputs; Python `ctypes` requires a shared
library with a compatible C interface. Importable native Python extensions must
match the selected Python ABI.

Use target requirements for hardware-specific modules:

```python
TargetRequirements(
    architectures=(Architecture.AARCH64,),
    capabilities=(CapabilityRequirement("cuda", minimum_version="12.2"),),
)
```

Requirements can also restrict `distros` and exact `(major, minor)`
`python_versions`. Discovery advertises CUDA driver support when `nvidia-smi`
reports it; unknown capabilities are treated as unavailable. Custom target
profiles can supply `SystemId.capabilities` as `(name, version)` pairs.
Capability values are part of the profile/cache key and persist with recorded
systems. CUDA compiler modules additionally verify the cached `nvcc` version
against the module requirement and the target driver's supported version.
Provision the appropriate toolkit using the existing C++ dependency configuration
or a supported CUDA base distro; detecting a GPU does not install a toolkit.

Incompatible modules and their consumers are skipped with the dependency chain
logged. Assigning an incompatible program fails before compilation or transfer,
including when distributing an existing bundle. The stale-dependency override
cannot bypass target compatibility checks. Dependency cache preparation stays
online; compilation stays offline. Source, entrypoint, and resource edits do not
invalidate dependency images. **All Python programs share the one root
`requirements.txt` and one target virtual environment.**

The self-contained backend in `__tests__/fixtures/module_contract_backend/`
exercises transitive libraries, exported headers, two Python modules with different entry files, conflicting library names across independent programs, and relative
resources. Run its actual Docker tests with:

```bash
.venv/bin/python -m pytest __tests__/module_contract_docker_tests.py __tests__/module_contract_tests.py
```
