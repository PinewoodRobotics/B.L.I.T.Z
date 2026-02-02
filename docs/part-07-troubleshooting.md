## Part 7: Troubleshooting playbook

## Goal

Fast diagnosis and recovery when the system won’t start, deploy, or behave as expected.

## Watchdog won’t start

- **Symptom**: crash mentioning `system_data/name.txt`.
  - **Fix**:

```bash
echo "dev" > system_data/name.txt
make watchdog
```

- **Symptom**: missing Python modules.
  - **Fix**:

```bash
make initiate-project
make watchdog
```

## Watchdog API not responding

- **Check**:

```bash
curl -v http://localhost:5000/get/system/status
```

- **If port 5000 is busy**: change `watchdog.port` in `system_data/basic_system_config.json` and restart.

## start/stop endpoints return `Config not set`

- **Fix**: set config once per watchdog startup:

```bash
mkdir -p config
printf "{}" > config/config.txt
curl -sS -X POST http://localhost:5000/set/config \
  -H 'Content-Type: application/json' \
  -d '{"config":"{}"}'
```

## `possible_processes` is empty

- **Meaning**: `backend.deploy.get_modules()` currently returns no runnable modules, so there is nothing for the watchdog to start.
- **Check**:

```bash
curl -sS http://localhost:5000/get/system/status
```

## Deploy failures (send-to-target / deploy-to-target)

- **Symptom**: `sshpass: command not found`.
  - **Fix (macOS)**:

```bash
make mac-deps
```

- **Symptom**: permission errors during rsync.

  - **Fix**: confirm `ubuntu` can run `sudo rsync` on the target.

- **Symptom**: SSH can’t connect.
  - **Fix**: verify manually:

```bash
ssh ubuntu@<host>
```

## systemd service issues on the target

- **Check status**:

```bash
sudo systemctl status startup.service
```

- **Follow logs**:

```bash
sudo journalctl -u startup.service -f
```

- **Restart**:

```bash
sudo systemctl restart startup.service
```

## Codegen failures (`make generate`)

- **Symptom**: `protoc: command not found`.
  - **Fix**:

```bash
sudo apt install -y protobuf-compiler
make generate
```

- **Symptom**: `fix-protobuf-imports` missing.
  - **Fix**:

```bash
make initiate-project
make generate
```
