import socket
import time

from zeroconf import ServiceInfo, Zeroconf

from watchdog.util.logger import error, success
from watchdog.util.system import (
    DiscoveryAnnouncement,
    load_basic_system_config,
    get_primary_ipv4,
)


TYPE_ = "_watchdog._tcp.local."
_service_info = None
_should_stop = False
zeroconf = None


def _zeroconf_properties(properties: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in properties.items() if value is not None}


def construct_service_info():
    config = load_basic_system_config()
    announcement = DiscoveryAnnouncement.collect(config)
    addresses = config.discovery.addresses or [get_primary_ipv4()]
    packed_addresses = [socket.inet_pton(socket.AF_INET6 if ":" in address else socket.AF_INET, address) for address in addresses]
    server = announcement.hostname.rstrip(".") + "."
    return ServiceInfo(
        TYPE_,
        f"{announcement.system_name}.{TYPE_}",
        addresses=packed_addresses,
        port=announcement.watchdog_port,
        server=server,
        properties=_zeroconf_properties(announcement.to_dict()),
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
