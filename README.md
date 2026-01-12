## B.L.I.T.Z

Multi-process robotics stack with a Python watchdog, codegen, and deploy tooling.

## Docs

Start here: `docs/README.md`

## Quickstart (local)

```bash
make initiate-project
echo "dev" > system_data/name.txt
make generate
make watchdog
```

## Tests

```bash
make test
```

## Deploy to a target machine

```bash
make send-to-target
make deploy-to-target
```
