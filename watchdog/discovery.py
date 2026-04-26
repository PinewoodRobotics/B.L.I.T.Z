import os
import socket
import time
from pathlib import Path

from zeroconf import ServiceInfo, Zeroconf

from watchdog.util.logger import error, success
from watchdog.util.system import (
    RaspberryPiInfo,
    get_local_hostname,
    get_primary_ipv4,
    get_system_name,
    load_basic_system_config,
)


TYPE_ = "_watchdog._udp.local."
_service_info = None
_should_stop = False
zeroconf = None


def _zeroconf_properties(properties: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in properties.items() if value is not None}


def construct_service_info():
    hostname = socket.gethostname()
    hostname_local = get_local_hostname()
    system_name = get_system_name()
    local_ip = get_primary_ipv4()
    system_config = load_basic_system_config()
    raspberry_pi_info = RaspberryPiInfo.collect().to_dict()
    addresses = [socket.inet_aton(local_ip)]
    blitz_path = os.environ.get("BLITZ_PATH") or str(Path(__file__).resolve().parents[1])
    return ServiceInfo(
        TYPE_,
        f"{hostname}.{TYPE_}",
        addresses=addresses,
        port=9999,
        server=hostname_local,
        properties=_zeroconf_properties(
            {
                "hostname": hostname_local,
                "system_name": system_name,
                "watchdog_port": system_config.watchdog.port,
                "autobahn_port": system_config.autobahn.port,
                "blitz_path": blitz_path,
                **raspberry_pi_info,
            }
        ),
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
            error(f"Error updating service discovery: {e}")

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
