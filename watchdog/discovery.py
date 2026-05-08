import socket
import time

from zeroconf import ServiceInfo, Zeroconf

from watchdog.util.logger import error, success
from watchdog.util.system import (
    DiscoveredNetworkSystem,
    get_primary_ipv4,
)


TYPE_ = "_watchdog._udp.local."
_service_info = None
_should_stop = False
zeroconf = None


def _zeroconf_properties(properties: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in properties.items() if value is not None}


def construct_service_info():
    hostname = socket.gethostname()
    local_ip = get_primary_ipv4()
    discovered_system = DiscoveredNetworkSystem.collect()
    addresses = [socket.inet_aton(local_ip)]
    return ServiceInfo(
        TYPE_,
        f"{hostname}.{TYPE_}",
        addresses=addresses,
        port=9999,
        server=discovered_system.hostname,
        properties=_zeroconf_properties(discovered_system.to_dict()),
    )


def enable_discovery():
    global zeroconf, _service_info, _should_stop

    while not _should_stop:
        time.sleep(5)
        try:
            if zeroconf is not None:
                try:
                    if _service_info is not None:
                        zeroconf.unregister_service(_service_info)
                except Exception:
                    pass
                zeroconf.close()

            zeroconf = Zeroconf()
            _service_info = construct_service_info()
            zeroconf.register_service(_service_info)
            success(f"Refreshed service discovery for {_service_info.server}")
        except Exception as e:
            error(f"Error updating service discovery: {str(e)} {e.args}")

    if zeroconf is not None:
        try:
            if _service_info is not None:
                zeroconf.unregister_service(_service_info)
        except Exception:
            pass
        zeroconf.close()


def stop_discovery():
    global _should_stop
    _should_stop = True
