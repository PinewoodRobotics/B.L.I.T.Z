import socket
import time
from zeroconf import ServiceInfo, Zeroconf

from watchdog.util.logger import success
from watchdog.util.system import (
    get_local_hostname,
    get_local_ip,
    get_system_name,
    load_basic_system_config,
)


TYPE_ = "_watchdog._udp.local."
_service_info = None
_should_stop = False


def enable_discovery():
    global zeroconf, _service_info
    zeroconf = Zeroconf()

    hostname = socket.gethostname()
    hostname_local = get_local_hostname()
    system_name = get_system_name()
    local_ip = get_local_ip("eth0") or get_local_ip("en0") or "127.0.0.1"
    system_config = load_basic_system_config()

    addresses = [socket.inet_aton(local_ip)]

    _service_info = ServiceInfo(
        TYPE_,
        f"{hostname}.{TYPE_}",
        addresses=addresses,
        port=9999,
        server=hostname_local,
        properties={
            "hostname": hostname,
            "hostname_local": hostname_local,
            "system_name": system_name,
            "watchdog_port": system_config.watchdog.port,
            "autobahn_port": system_config.autobahn.port,
        },
    )

    zeroconf.register_service(_service_info)
    success(f"Registered service {system_name} on {hostname_local} ({local_ip})")

    _refresh_loop(interval_seconds=10)


def _refresh_loop(interval_seconds: int = 30):
    global _should_stop, zeroconf, _service_info

    while not _should_stop:
        time.sleep(interval_seconds)
        if _should_stop:
            break

        try:
            if zeroconf and _service_info:
                zeroconf.update_service(_service_info)
                success(f"Refreshed service discovery for {_service_info.server}")
        except Exception as e:
            print(f"Error refreshing service: {e}")


def stop_discovery():
    global _should_stop
    _should_stop = True
