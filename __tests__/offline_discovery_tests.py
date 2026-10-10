"""Discover offline targets even when their LAN has no default gateway."""
from types import SimpleNamespace
import subprocess

import pytest

from watchdog.util import system


def test_prefers_default_route_without_enumerating_interfaces(monkeypatch):
    monkeypatch.setattr(system.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="1.1.1.1 via 192.168.1.1 dev wlan0 src 192.168.1.25"))
    monkeypatch.setattr(system.netifaces, "interfaces", lambda: pytest.fail("unexpected fallback"))
    assert system.get_primary_ipv4() == "192.168.1.25"


def configure_offline_interfaces(monkeypatch, records, down=()):
    def no_route(*args, **kwargs):
        raise subprocess.CalledProcessError(2, ["ip", "route", "get", "1.1.1.1"])

    monkeypatch.setattr(system.subprocess, "run", no_route)
    monkeypatch.setattr(system.netifaces, "interfaces", lambda: list(records))
    monkeypatch.setattr(system.netifaces, "ifaddresses", lambda name: {system.netifaces.AF_INET: [{"addr": addr} for addr in records[name]]})
    monkeypatch.setattr(system.psutil, "net_if_stats", lambda: {name: SimpleNamespace(isup=name not in down) for name in records})


def test_offline_lan_prefers_physical_interface_and_skips_down_interfaces(monkeypatch):
    configure_offline_interfaces(monkeypatch, {"docker0": ["172.17.0.1"], "eth0": ["10.0.0.2"], "wlan0": ["192.168.4.2"], "lo": ["127.0.0.1"]}, down=("eth0",))
    assert system.get_primary_ipv4() == "192.168.4.2"


def test_link_local_lan_is_usable_as_last_resort(monkeypatch):
    configure_offline_interfaces(monkeypatch, {"eth0": ["169.254.12.34"], "lo": ["127.0.0.1"]})
    assert system.get_primary_ipv4() == "169.254.12.34"


def test_no_active_network_reports_cause(monkeypatch):
    configure_offline_interfaces(monkeypatch, {"eth0": ["192.168.4.2"], "lo": ["127.0.0.1"]}, down=("eth0",))
    with pytest.raises(RuntimeError, match="no active LAN address"):
        system.get_primary_ipv4()
