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
