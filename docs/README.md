## BLITZ docs

These docs are organized as parts. Each part is a step toward a bigger workflow (setup, codegen, run, deploy, autostart, testing, troubleshooting).

## Parts (follow in order)

1. `docs/part-01-setup.md` (local setup + verify)
2. `docs/part-02-codegen.md` (proto/codegen)
3. `docs/part-03-run-local.md` (run core services locally)
4. `docs/part-04-deploy.md` (deploy to target + restart)
5. `docs/part-05-autostart.md` (autostart on target via systemd)
6. `docs/part-06-testing-ci.md` (tests + repo expectations)
7. `docs/part-07-troubleshooting.md` (common failures + recovery)

## Glossary

- **target**: the machine you deploy to (typically an Ubuntu host on the robot side).
- **watchdog**: the Python service that exposes an API and manages subprocesses.
- **basic system config**: `system_data/basic_system_config.json` (baseline ports/paths).
- **generated proto**: Python output generated into `watchdog/generated/`.
