## Part 3: Run core services locally

## Goal

Start the watchdog locally and use it to view system state and manage processes.

## Prereqs

- Part 1 completed (venv + `system_data/name.txt`)

## Steps: run the watchdog

1. Start the watchdog:

```bash
make watchdog
```

2. Check status:

```bash
curl -sS http://localhost:5000/get/system/status
```

## Steps: set the runtime config (required before starting processes)

The watchdog refuses to start/stop managed processes until a config is set.

1. Create the config file:

```bash
mkdir -p config
printf "{}" > config/config.txt
```

2. Tell the watchdog to load it:

```bash
curl -sS -X POST http://localhost:5000/set/config \
  -H 'Content-Type: application/json' \
  -d '{"config":"{}"}'
```

## Steps: managed processes (what exists today)

1. List possible processes:

```bash
curl -sS http://localhost:5000/get/system/status
```

2. If `possible_processes` is empty, that means there are no runnable modules registered in `backend/deploy.py` yet.

## How process launching is wired

- The watchdog gets process definitions from `backend.deploy.get_modules()`.
- Only modules that implement runnable behavior are exposed via the API.
- Today, `backend/deploy.py` returns an empty list, so the watchdog can’t start any extra processes beyond itself.

## Steps: start/stop a process (once modules exist)

1. Start one or more processes:

```bash
curl -sS -X POST http://localhost:5000/start/process \
  -H 'Content-Type: application/json' \
  -d '{"process_types":["<process_name>"]}'
```

2. Stop one or more processes:

```bash
curl -sS -X POST http://localhost:5000/stop/process \
  -H 'Content-Type: application/json' \
  -d '{"process_types":["<process_name>"]}'
```

## Expected result

- `get/system/status` shows the system name and watchdog state.
- If runnable modules are registered, `possible_processes` lists them and `active_processes` changes as you start/stop processes.

## Common failures

- **`Config not set` from start/stop endpoints**: run the “set the runtime config” steps above.
- **`Unknown process <name>`**: the name must match a process in `possible_processes`.
