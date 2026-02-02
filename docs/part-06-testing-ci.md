## Part 6: Tests + CI expectations

## Goal

Run the repo’s test suite locally and understand what CI does on push.

## Prereqs

- Part 1 completed

## Steps: run tests locally

1. Run pytest via Makefile:

```bash
make test
```

2. (Optional) Run pytest directly:

```bash
.venv/bin/python -m pytest
```

## Where tests live

- `watchdog/`
- `backend/`

Pytest is configured in `pyproject.toml` with `testpaths = ["watchdog/", "backend/"]`.

## CI behavior (GitHub Actions)

The workflow in `.github/workflows/main.yml` builds a Raspberry Pi OS image using `scripts/install/raspi5.sh` and `scripts/install_deps.sh`, then uploads the compressed image as an artifact.

## Common failures

- **A test fails due to machine-specific assumptions**: some tests may be written against a specific environment (e.g. hostname expectations). Treat these as environment constraints, not necessarily product bugs.
