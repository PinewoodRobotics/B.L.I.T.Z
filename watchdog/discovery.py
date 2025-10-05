import socket
from zeroconf import ServiceInfo, Zeroconf

from backend.python.common.debug.logger import error, success
from backend.python.common.util.system import get_local_hostname, get_local_ip


def enable_discovery():
    global zeroconf
    zeroconf = Zeroconf()

    hostname = socket.gethostname()
    hostname_local = get_local_hostname()
    local_ip = get_local_ip("eth0") or get_local_ip("en0") or "127.0.0.1"

    addresses = [socket.inet_aton(local_ip)]

    _info = ServiceInfo(
        "_deploy._udp.local.",
        f"{hostname}._deploy._udp.local.",
        addresses=addresses,
        port=9999,
        server=hostname_local,
        properties={"id": hostname, "hostname": hostname_local},
    )

    zeroconf.register_service(_info)
    success(f"Registered service {hostname} on {hostname_local} ({local_ip})")
