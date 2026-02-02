## Part 2: Proto/codegen

## Goal

Generate Python code from `.proto` files so the watchdog and other Python code can import the generated messages.

## Prereqs

- Part 1 completed (`make initiate-project`)
- `protoc` installed and on your PATH
  - Ubuntu: `sudo apt install -y protobuf-compiler`
  - macOS: `brew install protobuf`

## Steps

1. Generate Python protobuf output:

```bash
make generate
```

2. Confirm outputs exist:

```bash
ls watchdog/generated
```

## What it does

- Inputs: all `.proto` files in `proto/`
- Outputs: Python modules into `watchdog/generated/`
- Post-step: runs `fix-protobuf-imports` from the venv to normalize imports

## When to rerun

- You edited any file under `proto/`
- You pulled changes that modified `proto/`
- You see an import error coming from `watchdog/generated/`

## Expected result

- `watchdog/generated/` contains Python files for each `.proto`
- Imports from generated modules succeed when running `make watchdog`

## Common failures

- **`protoc: command not found`**: install protobuf compiler (see prereqs).
- **`fix-protobuf-imports: No such file or directory`**: rerun `make initiate-project` to recreate the venv and dependencies.
