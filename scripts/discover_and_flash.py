import subprocess
import requests
import time

SUBNET = "10.47.65."
PORT = 9000
ENDPOINT = "/pi_identity"
TIMEOUT = 0.5


def send_to_target(last_octet):
    try:
        result = subprocess.run(
            ["make", "send-to-target", f"ARGS={last_octet}"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("[✓] Make command succeeded:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Make command failed:")
        print(e.stderr)


def scan():
    found = []

    print(f"[+] Scanning subnet {SUBNET}0/24...")

    for i in range(1, 255):
        ip = f"{SUBNET}{i}"
        url = f"http://{ip}:{PORT}{ENDPOINT}"
        try:
            response = requests.get(url, timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                pi_name = data.get("pi_name", "unknown")
                print(f"  ✓ {ip} → {pi_name}")
                found.append((ip, pi_name))
            else:
                print(f"  × {ip} (non-200)")
        except requests.RequestException:
            pass

    print(f"[✓] Done. Found {len(found)} responsive Pi(s).")

    return found


if __name__ == "__main__":
    start = time.time()
    scan()
    print(f"[⏱] Scan completed in {time.time() - start:.2f}s.")
