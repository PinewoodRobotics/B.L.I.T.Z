#!/usr/bin/env python3
import sys
import time
import socket
import subprocess
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange

SERVICE = "_deploy._udp.local."
DISCOVERY_TIMEOUT = 2.0
TARGET_FOLDER = "~/Documents/B.L.I.T.Z/"

pis: dict[str, str] = {}


def on_state_change(zeroconf: Zeroconf, service_type, name, state):
    if state is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        if not info:
            return
        ip = socket.inet_ntoa(info.addresses[0])
        pis[name] = ip


def discover_pis():
    zc = Zeroconf()
    ServiceBrowser(zc, SERVICE, handlers=[on_state_change])
    time.sleep(DISCOVERY_TIMEOUT)
    zc.close()
    return pis


def deploy(project_dir):
    if not pis:
        print("❌ No Pis discovered. Check your network and that they're advertising.")
        sys.exit(1)

    for name, ip in pis.items():
        target = f"ubuntu@{ip}:{TARGET_FOLDER}"
        print(f"\n->  Deploying to {name} ({ip})…")

        rsync_cmd = [
            "rsync",
            "-av",
            "--progress",
            "--exclude-from=.gitignore",
            "--delete",
            f"{project_dir.rstrip('/')}/",
            target,
        ]
        ret = subprocess.run(rsync_cmd)
        if ret.returncode != 0:
            print(f"   ❌ rsync failed for {name}")
            continue

        ssh_cmd = [
            "ssh",
            f"ubuntu@{ip}",
            f"sudo systemctl restart startup.service",
        ]
        ret = subprocess.run(ssh_cmd, capture_output=True, text=True)
        print("->  stdout:", ret.stdout.strip())
        print("->  stderr:", ret.stderr.strip())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <project_dir>")
        sys.exit(1)

    project_dir = sys.argv[1]

    print("🔍 Discovering Pis on the LAN…")
    discover_pis()
    print(f"✅ Found {len(pis)} Pi(s):", ", ".join(pis.values()))

    deploy(project_dir)
