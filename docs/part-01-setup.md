## Part 1: Local setup + verify

## Goal

Get a working local Python environment and confirm the watchdog starts and responds.

## Prereqs

- `python3` (>= 3.8)
- `make`
- macOS: Homebrew (optional, for installing missing tools)

## Steps

1. From the repo root, create the venv and install dependencies:

```bash
make initiate-project
```

2. Set a local system name (required by the watchdog):

```bash
echo "dev" > system_data/name.txt
```

3. Start the watchdog:

```bash
make watchdog
```

4. In a second terminal, verify the HTTP API is up (default port is 5000):

```bash
curl -sS http://localhost:5000/get/system/status
```

## Expected result

- `make watchdog` stays running and prints startup logs.
- `curl` returns JSON with keys like `status`, `active_processes`, `possible_processes`.

## Common failures

- **`system_data/name.txt does not exist`**: create it (step 2) and restart.
- **`ModuleNotFoundError` inside the venv**: rerun `make initiate-project`.
- **Port 5000 already in use**: stop the other process or change `watchdog.port` in `system_data/basic_system_config.json`.
