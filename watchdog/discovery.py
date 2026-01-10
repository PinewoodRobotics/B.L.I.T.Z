import socket
import time
from zeroconf import ServiceInfo, Zeroconf

from watchdog.util.logger import error, success
from watchdog.util.system import (
    get_local_hostname,
    get_local_ip,
    get_primary_ipv4,
    get_system_name,
    load_basic_system_config,
)


TYPE_ = "_watchdog._udp.local."
_service_info = None
_should_stop = False


def construct_service_info():
    hostname = socket.gethostname()
    hostname_local = get_local_hostname()
    system_name = get_system_name()
    local_ip = get_primary_ipv4()
    system_config = load_basic_system_config()
    addresses = [socket.inet_aton(local_ip)]
    return ServiceInfo(
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


def enable_discovery():
    global zeroconf, _service_info, _should_stop

    zeroconf = Zeroconf()
    registered = False

    while not _should_stop:
        time.sleep(5)
        try:
            _service_info = construct_service_info()
            if not registered:
                zeroconf.register_service(_service_info)
                registered = True
                continue

            zeroconf.update_service(_service_info)
            success(f"Refreshed service discovery for {_service_info.server}")
        except Exception as e:
            error(f"Error updating service discovery: {e}")


def stop_discovery():
    global _should_stop
    _should_stop = True
