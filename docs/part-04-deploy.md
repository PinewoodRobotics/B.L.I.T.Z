## Part 4: Deploy to a target + restart

## Goal

Sync the repo to the target machine and restart the systemd service.

## Prereqs

- You can SSH to the target as `ubuntu`
- `sshpass` installed on your local machine
  - macOS: `make mac-deps`
  - Ubuntu: `sudo apt install -y sshpass`
- The target has `rsync` installed

## What the Make targets do

- `make send-to-target`: rsyncs the repo to `TARGET_FOLDER` using `sudo rsync` on the target
- `make deploy-to-target`: runs `send-to-target` and then restarts `startup.service` on the target

## Steps

1. Pick the target settings (defaults are in `Makefile`):

   - `UBUNTU_TARGET` (e.g. `nathanhale.local`)
   - `TARGET_PORT` (default `22`)
   - `SSH_PASS` (default `ubuntu`)
   - `TARGET_FOLDER` (default `/opt/blitz/B.L.I.T.Z/`)

2. Deploy:

```bash
make send-to-target UBUNTU_TARGET=<host_or_ip> TARGET_PORT=22 SSH_PASS=ubuntu
```

3. Restart the system service:

```bash
make deploy-to-target UBUNTU_TARGET=<host_or_ip> TARGET_PORT=22 SSH_PASS=ubuntu
```

## Expected result

- The repo contents exist under `TARGET_FOLDER` on the target.
- `startup.service` is restarted successfully.

## Common failures

- **`sshpass: command not found`**: install it (see prereqs).
- **Permission errors on the target**: `send-to-target` uses `--rsync-path="sudo rsync"`; the `ubuntu` user needs sudo.
- **Host key prompt / SSH failure**: confirm you can `ssh ubuntu@<host>` manually first.
