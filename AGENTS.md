# AGENTS.md

## Repository overview

BLITZ is a multi-process robotics stack. The Python deployment tooling discovers
target systems, builds architecture-specific bundles, syncs them to the fleet,
and assigns typed process plans. The watchdog runs those processes on each
target. The `website/` directory contains the standalone Next.js marketing site.

## Project layout

- `backend/`: deployment, bundling, compilation, networking, and module APIs.
- `watchdog/`: target-side discovery, monitoring, process management, and routes.
- `proto/`: protobuf source definitions.
- `scripts/`: setup, deployment, runtime, and installer scripts.
- `__tests__/`: repository-level Python tests.
- `website/`: Next.js frontend; follow `website/AGENTS.md` for work in this tree.

## Working rules

- Preserve the public deployment hooks in `backend/deploy.py`:
  `get_modules()` and `pi_name_to_process_types()`.
- Prefer typed Python APIs such as `ProcessPlan`, `WeightedProcess`, and
  `SupportedModules` over ad hoc dictionaries or new config formats.
- Keep deployment behavior compatible with both local Python execution and the
  existing installer/Gradle integration unless a change explicitly replaces it.
- Do not hand-edit generated protobuf files in `watchdog/generated/`; update the
  definitions in `proto/` and run `make generate`.
- Keep platform-specific build logic inside the existing compilation adapters.
- Never commit secrets, local system identities, virtual environments, build
  artifacts, caches, or machine-specific paths.
- Preserve unrelated work in the repository and keep changes scoped to the task.

## Validation

- Run targeted Python tests while iterating:
  `.venv/bin/python -m pytest path/to/test_file.py`.
- Run `make test` when changing shared deployment or watchdog behavior.
- Run `make generate` after changing protobuf definitions.
- For `website/`, run `pnpm lint` and `pnpm build` from that directory.

## Style

- Follow existing Python and shell conventions in the surrounding files.
- Add type annotations to new Python interfaces and keep functions focused.
- Prefer clear domain names over abbreviations, and document behavior that is
  not obvious from the code.
