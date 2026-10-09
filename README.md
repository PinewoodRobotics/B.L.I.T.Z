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
