# B.L.I.T.Z

Multi-process robotics stack with a Python watchdog, codegen, and deploy tooling.

## Easy Setup

Install BLITZ on a Raspberry Pi or Linux coprocessor:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/install_on_system.sh)"
```

## WPILib Java Project Setup

From inside a Java WPILib robot project, run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/install_on_wpilib.sh)"
```

The installer discovers the current WPILib project, adds `backend/deployment`,
and creates `backend/deploy.py` if it does not already exist. Re-running the
installer refreshes BLITZ deployment files while preserving your customized
`backend/deploy.py`. During installation, BLITZ is cloned into `bin/B.L.I.T.Z`
inside the robot project and cleaned up after the needed files are copied.
The installer also adds a Gradle `deployBlitz` task by setting `backendPath`
in `settings.gradle` or `settings.gradle.kts` and applying the backend Gradle
task script from `backend/deployment/gradle`.

For non-interactive setup:

```bash
WPILIB_PROJECT=/path/to/robot \
BLITZ_ASSUME_YES=true \
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/PinewoodRobotics/B.L.I.T.Z/HEAD/scripts/ui/install_on_wpilib.sh)"
```

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
