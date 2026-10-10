"""Discovery, exclusion, catalog collection, and simulation endpoint contracts."""
from dataclasses import asdict
from types import SimpleNamespace
import socket
import threading

import pytest
import requests
from zeroconf import ServiceInfo

from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.network_api import zeroconf as discovery
from backend.deployment.network_api.system_api import System
from watchdog import discovery as advertisement
from watchdog.util import system as watchdog_system


def profile(name="pi", hostname="pi.local"):
    return discovery.DiscoveredNetworkSystem(
        hostname, name, 5000, 8080, "/blitz", "aarch64", "Linux-glibc2.36", 3, 11,
        os_distribution_id="debian", os_distribution_version_id="12",
    )


def response(system=None, payload=None, status=200):
    payload = payload if payload is not None else {"schema_version": 2, "system": asdict(system or profile())}
    return SimpleNamespace(status_code=status, raise_for_status=lambda: None, json=lambda: payload)


def service(system=None, properties=None, address="192.0.2.10", server="pi.local."):
    system = system or profile()
    metadata = {key: str(getattr(system, key)) for key in ("hostname", "system_name", "watchdog_port", "autobahn_port", "ssh_port")}
    metadata["schema_version"] = "2"
    return ServiceInfo(discovery.SERVICE, system.system_name + "." + discovery.SERVICE,
        addresses=[socket.inet_pton(socket.AF_INET6 if ":" in address else socket.AF_INET, address)],
        server=server, port=system.watchdog_port,
        properties=metadata if properties is None else properties)


def config(**overrides):
    return watchdog_system.WatchdogSystemConfig(
        autobahn_connection={"host": "localhost", "port": 8080},
        logging={"log_publish_topic": "logs", "default_log_level": "INFO"},
        watchdog_api={"api_port": 5000, "system_stats_publish_interval_seconds": 5, "publish_system_stats": False},
        desired_config_base64_path="config/base64", discovery=overrides,
    )


def test_advertisement_is_lightweight_and_uses_reachable_simulation_ports(monkeypatch):
    settings = config(hostname="sim.local", addresses=["192.0.2.50"], watchdog_port=15000, autobahn_port=18080, ssh_port=12200)
    monkeypatch.setattr(advertisement, "load_basic_system_config", lambda: settings)
    monkeypatch.setattr(watchdog_system, "get_system_name", lambda: "sim")
    monkeypatch.setattr(watchdog_system.DiscoveredNetworkSystem, "collect", lambda: pytest.fail("profile probe from mDNS"))
    monkeypatch.setattr(watchdog_system, "collect_capabilities", lambda *_args: pytest.fail("hardware probe from mDNS"))
    monkeypatch.setattr(advertisement, "get_primary_ipv4", lambda: pytest.fail("explicit address ignored"))
    info = advertisement.construct_service_info()
    metadata = discovery.decode_zeroconf_properties(info.properties)
    assert info.type == "_watchdog._tcp.local."
    assert info.port == 15000
    assert info.parsed_addresses() == ["192.0.2.50"]
    assert set(metadata) == {"schema_version", "hostname", "system_name", "watchdog_host", "watchdog_port", "autobahn_host", "autobahn_port", "ssh_host", "ssh_port"}
    assert metadata["autobahn_host"] == "sim.local"
    assert metadata["ssh_port"] == "12200"


@pytest.mark.parametrize("broker_host", ["localhost", "127.0.0.1", "::1", "0.0.0.0", "::"])
def test_local_broker_hosts_are_advertised_as_machine_host(monkeypatch, broker_host):
    monkeypatch.setattr(watchdog_system, "get_local_hostname", lambda: "pi.local")
    monkeypatch.setattr(watchdog_system, "get_system_name", lambda: "pi")
    settings = config()
    settings.autobahn_connection.host = broker_host
    assert watchdog_system.DiscoveryAnnouncement.collect(settings).autobahn_host == "pi.local"


@pytest.mark.parametrize("external_host", ["127.0.0.1", "::1"])
def test_explicit_simulator_hosts_preserve_the_client_network_view(monkeypatch, external_host):
    monkeypatch.setattr(watchdog_system, "get_system_name", lambda: "sim")
    settings = config(
        hostname="sim.local", watchdog_host=external_host,
        autobahn_host=external_host, ssh_host=external_host,
    )
    announcement = watchdog_system.DiscoveryAnnouncement.collect(settings)
    assert announcement.watchdog_host == external_host
    assert announcement.autobahn_host == external_host
    assert announcement.ssh_host == external_host


def test_catalog_batch_waits_for_all_announcements_and_filters_before_http(monkeypatch):
    announcements = [service(), service(profile("blocked", "blocked.local"), address="192.0.2.20")]
    events = []
    class Zeroconf:
        def get_service_info(self, type_, name):
            return next(info for info in announcements if info.name == name)
        def close(self):
            events.append("closed")
    class Browser:
        def __init__(self, zc, type_, listener):
            for info in announcements:
                events.append("announced:" + info.name)
                listener.add_service(zc, type_, info.name)
        def cancel(self):
            events.append("discovery-complete")
    def get(url, **kwargs):
        assert "discovery-complete" in events
        assert "closed" in events
        assert "192.0.2.20" not in url
        events.append("http:" + url)
        return response()
    monkeypatch.setattr(discovery, "Zeroconf", Zeroconf)
    monkeypatch.setattr(discovery, "ServiceBrowser", Browser)
    monkeypatch.setattr(discovery.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(discovery.requests, "get", get)
    systems = discovery.discover_all_on_network(0, blacklist=["BLOCKED.LOCAL."])
    assert len(systems) == 1
    assert [event for event in events if event.startswith("http:")] == ["http:http://192.0.2.10:5000/get/system/catalog"]


@pytest.mark.parametrize("blocked", ["pi", "PI.LOCAL.", "server-alias.local", "192.0.2.10", "::ffff:192.0.2.10"])
def test_machine_hostname_alias_and_ip_blacklists_run_before_catalog(monkeypatch, blocked):
    endpoint = discovery.DiscoveredEndpoint.from_service_info(service(server="server-alias.local."))
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("blacklisted target queried"))
    assert discovery.collect_system_catalogs([endpoint], [blocked]) == set()


def test_shared_service_host_does_not_blacklist_unrelated_machine():
    endpoint = discovery.DiscoveredEndpoint("pi.local", 5000, autobahn_host="broker.local", ssh_host="gateway.local")
    assert not endpoint.is_blacklisted(["broker.local", "gateway.local"])


def test_invalid_blacklisted_announcement_does_not_block_fleet(monkeypatch):
    info = service(properties={"hostname": "pi.local"})
    class Zeroconf:
        def get_service_info(self, *_args):
            return info
        def close(self):
            pass
    class Browser:
        def __init__(self, zc, type_, listener):
            listener.add_service(zc, type_, info.name)
        def cancel(self):
            pass
    monkeypatch.setattr(discovery, "Zeroconf", Zeroconf)
    monkeypatch.setattr(discovery, "ServiceBrowser", Browser)
    monkeypatch.setattr(discovery.time, "sleep", lambda *_args: None)
    assert discovery.discover_endpoints_on_network(0, ["192.0.2.10"]) == set()
    with pytest.raises(ValueError, match="no deployment will proceed"):
        discovery.discover_endpoints_on_network(0)


def test_pinned_ipv6_and_duplicate_addresses_query_once(monkeypatch):
    queried = []
    def get(url, **kwargs):
        queried.append(url)
        return response()
    monkeypatch.setattr(discovery.requests, "get", get)
    systems = discovery.discover_at_addresses(["[2001:db8::1]:15000", "[2001:0db8:0:0:0:0:0:1]:15000"])
    assert len(queried) == 1
    system = System(systems.pop())
    assert system.watchdog_url().startswith("http://[2001:")
    assert system.general_info.watchdog_port == 15000
    assert system.ssh_port == 22
    assert system._rsync_remote_host().startswith("ubuntu@[2001:")
    system.user = "robot"
    assert system.remote_host.startswith("robot@2001:")
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("IPv6 blacklist ignored"))
    assert discovery.discover_at_addresses(["[2001:0db8::1]:15000"], ["2001:db8::1"]) == set()


def test_http_batch_is_concurrent_and_failure_never_returns_partial_fleet(monkeypatch):
    barrier = threading.Barrier(2)
    queried = []
    def get(url, **kwargs):
        queried.append(url)
        barrier.wait(timeout=2)
        if "bad.local" in url:
            raise requests.ConnectionError("unreachable")
        return response()
    monkeypatch.setattr(discovery.requests, "get", get)
    with pytest.raises(ValueError, match="no deployment will proceed"):
        discovery.discover_at_addresses(["good.local:5000", "bad.local:5000"])
    assert len(queried) == 2


@pytest.mark.parametrize("change", [
    lambda data: data.pop("schema_version"),
    lambda data: data.update(schema_version=1),
    lambda data: data.update(schema_version=2.0),
    lambda data: data["system"].pop("capabilities_json"),
    lambda data: data["system"].update(capabilities_json='{"random_gpu": "1"}'),
    lambda data: data["system"].update(capabilities_json='[]'),
    lambda data: data["system"].update(ssh_host=["pi.local"]),
    lambda data: data["system"].update(ssh_port=22.5),
    lambda data: data["system"].update(autobahn_port=True),
    lambda data: data["system"].update(hostname="bad/hostname"),
    lambda data: data["system"].update(os_distribution_family=[]),
])
def test_incompatible_or_invalid_catalogs_fail_closed(monkeypatch, change):
    payload = {"schema_version": 2, "system": asdict(profile())}
    change(payload)
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: response(payload=payload))
    with pytest.raises(ValueError, match="no deployment will proceed"):
        discovery.discover_at_addresses(["pi.local:5000"])


def test_catalog_cannot_redirect_contacted_watchdog(monkeypatch):
    data = profile()
    data.watchdog_host = "other-device.local"
    data.watchdog_port = 9999
    data.ssh_host = "docker-internal.local"
    data.ssh_port = 12200
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: response(data))
    system = discovery.discover_at_addresses(["192.0.2.50:15000"]).pop()
    assert system.watchdog_host == "192.0.2.50"
    assert system.watchdog_port == 15000
    assert system.ssh_host == "docker-internal.local"  # Explicit external override is honored.
    assert system.ssh_port == 12200


@pytest.mark.parametrize("broker_host,expected", [
    (None, "192.0.2.50"),
    ("pi.local", "192.0.2.50"),
    ("broker.example", "broker.example"),
])
def test_known_address_keeps_same_machine_broker_reachable(monkeypatch, broker_host, expected):
    data = profile()
    data.autobahn_host = broker_host
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: response(data))
    system = discovery.discover_at_addresses(["192.0.2.50:5000"]).pop()
    assert system.autobahn_host == expected
    assert system.autobahn_port == 8080


def test_link_local_devices_on_separate_links_are_both_collected(monkeypatch):
    queried = []
    def get(url, **kwargs):
        queried.append(url)
        return response(profile("one" if "eth0" in url else "two"))
    monkeypatch.setattr(discovery.requests, "get", get)
    systems = discovery.discover_at_addresses([
        "[fe80::1%eth0]:5000", "[fe80:0:0:0:0:0:0:1%eth1]:5000",
    ])
    assert len(systems) == 2
    assert len(queried) == 2
    assert any("%25eth0" in url for url in queried)
    assert any("%25eth1" in url for url in queried)


def test_http_redirect_is_rejected(monkeypatch):
    def get(url, **kwargs):
        assert kwargs["allow_redirects"] is False
        return response(status=302)
    monkeypatch.setattr(discovery.requests, "get", get)
    with pytest.raises(ValueError, match="without redirects"):
        discovery.discover_at_addresses(["pi.local:5000"])


def test_duplicate_machine_names_fail_before_process_assignment(monkeypatch):
    systems = {profile("PI.local", "one.local"), profile("pi", "two.local")}
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kwargs: systems)
    with pytest.raises(ValueError, match="Duplicate discovered system name"):
        BlitzNetworkDeployer._find_systems(BlitzNetworkDeployer.Options())


def test_offline_inventory_discards_legacy_device_destinations(tmp_path):
    options = BlitzNetworkDeployer.Options().set_build_folder_path(str(tmp_path))
    path = BlitzNetworkDeployer._inventory_path(options)
    path.parent.mkdir(parents=True)
    path.write_text('{"system_ids": [], "devices": {"old.local": {"watchdog_port": 9999}}}')
    assert BlitzNetworkDeployer._read_inventory(options) == {"system_ids": []}
    BlitzNetworkDeployer._remember_systems(options, {System(profile())})
    contents = path.read_text()
    assert "old.local" not in contents and "pi.local" not in contents and "watchdog_port" not in contents


def test_watchdog_catalog_cache_probes_once_and_refreshes_atomically(monkeypatch):
    cache = watchdog_system.SystemCatalogCache()
    now = [0.0]
    probes = []
    monkeypatch.setattr(watchdog_system, "get_local_hostname", lambda: "pi.local")
    monkeypatch.setattr(watchdog_system, "get_system_name", lambda: "pi")
    monkeypatch.setattr(watchdog_system.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(watchdog_system, "load_basic_system_config", lambda: config(catalog_refresh_interval_seconds=300))
    def collect():
        probes.append(now[0])
        data = asdict(profile())
        data["capabilities_json"] = '{}' if len(probes) == 1 else '{"gpio": "present"}'
        return watchdog_system.DiscoveredNetworkSystem(**data)
    monkeypatch.setattr(watchdog_system.DiscoveredNetworkSystem, "collect", collect)
    first = cache.get()
    now[0] = 299
    assert cache.get() == first
    now[0] = 300
    threads = [threading.Thread(target=cache.get) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert probes == [0, 300]
    assert cache.get()["system"]["capabilities_json"] == '{"gpio": "present"}'
    first["system"]["hostname"] = "changed"
    assert cache.get()["system"]["hostname"] == "pi.local"


def test_failed_catalog_probes_are_also_rate_limited(monkeypatch):
    cache = watchdog_system.SystemCatalogCache()
    now = [0.0]
    probes = []
    monkeypatch.setattr(watchdog_system, "get_local_hostname", lambda: "pi.local")
    monkeypatch.setattr(watchdog_system, "get_system_name", lambda: "pi")
    monkeypatch.setattr(watchdog_system.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(watchdog_system, "load_basic_system_config", lambda: config(catalog_refresh_interval_seconds=60))
    def fail():
        probes.append(now[0])
        raise OSError("hardware unavailable")
    monkeypatch.setattr(watchdog_system.DiscoveredNetworkSystem, "collect", fail)
    for value in (0, 1, 59, 60):
        now[0] = value
        with pytest.raises(RuntimeError, match="hardware unavailable"):
            cache.get()
    assert probes == [0, 60]


def test_endpoint_configuration_updates_without_hardware_reprobe(monkeypatch):
    cache = watchdog_system.SystemCatalogCache()
    settings = config()
    probes = []
    monkeypatch.setattr(watchdog_system, "load_basic_system_config", lambda: settings)
    monkeypatch.setattr(watchdog_system, "get_local_hostname", lambda: "pi.local")
    monkeypatch.setattr(watchdog_system, "get_system_name", lambda: "pi")
    def collect():
        probes.append(1)
        return watchdog_system.DiscoveredNetworkSystem(**asdict(profile()))
    monkeypatch.setattr(watchdog_system.DiscoveredNetworkSystem, "collect", collect)
    assert cache.get()["system"]["watchdog_port"] == 5000
    settings.discovery.watchdog_port = 15000
    settings.discovery.hostname = "new-pi.local"
    current = cache.get()["system"]
    assert current["watchdog_port"] == 15000
    assert current["hostname"] == "new-pi.local"
    assert probes == [1]


@pytest.mark.parametrize("initial_valid", [True, False])
def test_service_update_to_blacklisted_identity_clears_prior_record(monkeypatch, initial_valid):
    original = service(properties=None if initial_valid else {"hostname": "pi.local"})
    updated = service(profile("pi", "blocked.local"))
    current = [original]
    class Zeroconf:
        def get_service_info(self, *_args):
            return current[0]
        def close(self):
            pass
    class Browser:
        def __init__(self, zc, type_, listener):
            listener.add_service(zc, type_, original.name)
            current[0] = updated
            listener.update_service(zc, type_, original.name)
        def cancel(self):
            pass
    monkeypatch.setattr(discovery, "Zeroconf", Zeroconf)
    monkeypatch.setattr(discovery, "ServiceBrowser", Browser)
    monkeypatch.setattr(discovery.time, "sleep", lambda *_args: None)
    assert discovery.discover_endpoints_on_network(0, ["blocked.local"]) == set()


def test_cli_blacklist_preserves_project_exclusions(monkeypatch):
    options = BlitzNetworkDeployer.Options().set_blacklist(["protected.local"])
    seen = []
    monkeypatch.setattr(BlitzNetworkDeployer, "discover", lambda _modules, config: seen.extend(config.blacklist))
    BlitzNetworkDeployer.run_cli([], lambda _names: {}, options, ["discover", "--blacklist", "sim.local"])
    assert seen == ["protected.local", "sim.local"]


def test_scoped_ipv6_matches_bare_ip_blacklist_but_preserves_contact_scope():
    endpoint = discovery.DiscoveredEndpoint("pi.local", 5000, addresses=("fe80::1%eth0",))
    assert endpoint.is_blacklisted(["fe80:0:0:0:0:0:0:1"])
    assert endpoint.contact_host == "fe80::1%eth0"
    assert endpoint.authority == "[fe80::1%25eth0]:5000"


def dns_record(address, port=5000):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


def test_pinned_hostname_ip_blacklist_blocks_any_resolved_address_before_http(monkeypatch):
    resolutions = []
    def resolve(host, port, **kwargs):
        resolutions.append(host)
        return [dns_record("192.0.2.10"), dns_record("2001:db8::1")]
    monkeypatch.setattr(discovery.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("resolved blockedIP was queried"))
    assert discovery.discover_at_addresses(["sim.local:5000"], ["2001:0db8::1"]) == set()
    assert resolutions == ["sim.local"]


def test_pinned_hostname_ip_blacklist_resolution_failure_aborts_before_all_http(monkeypatch):
    def resolve(*_args, **_kwargs):
        raise socket.gaierror("DNS unavailable")
    monkeypatch.setattr(discovery.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("queried before required DNS resolution"))
    with pytest.raises(ValueError, match="Cannot enforce IP blacklist.*hostname resolution failed"):
        discovery.discover_at_addresses(["sim.local:5000", "192.0.2.10:5000"], ["192.0.2.20"])


@pytest.mark.parametrize("addresses, blacklist", [
    (["192.0.2.10:5000"], ["192.0.2.20"]),
    (["sim.local:5000"], []),
    (["sim.local:5000"], ["other.local"]),
])
def test_pinned_numeric_seed_or_hostname_only_blacklist_does_not_resolve(monkeypatch, addresses, blacklist):
    monkeypatch.setattr(discovery.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("unnecessary DNS lookup"))
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: response())
    assert len(discovery.discover_at_addresses(addresses, blacklist)) == 1


def test_pinned_hostname_blacklist_skips_dns_even_with_ip_exclusions(monkeypatch):
    monkeypatch.setattr(discovery.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("hostname already excluded"))
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("hostname already excluded"))
    assert discovery.discover_at_addresses(["sim.local:5000"], ["sim.local", "192.0.2.20"]) == set()


def test_pinned_fleet_resolves_all_required_addresses_before_http_and_keeps_hostnames(monkeypatch):
    events = []
    def resolve(host, port, **kwargs):
        events.append("dns:" + host)
        return [dns_record("192.0.2.10" if host == "one.local" else "192.0.2.11")]
    def get(url, **kwargs):
        assert set(events[:2]) == {"dns:one.local", "dns:two.local"}
        assert "192.0.2.10" not in url and "192.0.2.11" not in url
        events.append("http:" + url)
        return response(profile("one" if "one.local" in url else "two"))
    monkeypatch.setattr(discovery.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(discovery.requests, "get", get)
    systems = discovery.discover_at_addresses(["one.local:5000", "two.local:5000"], ["192.0.2.20"])
    assert len(systems) == 2
    assert {system.watchdog_host for system in systems} == {"one.local", "two.local"}


def test_distinct_dns_names_cannot_share_blacklist_resolution_or_catalog(monkeypatch):
    resolutions = []
    queried = []
    def resolve(host, port, **kwargs):
        resolutions.append(host)
        return [dns_record("192.0.2.10" if host == "robot" else "192.0.2.20")]
    def get(url, **kwargs):
        queried.append(url)
        return response()
    monkeypatch.setattr(discovery.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(discovery.requests, "get", get)
    assert len(discovery.discover_at_addresses(
        ["robot:5000", "robot.local:5000"], ["192.0.2.20"],
    )) == 1
    assert set(resolutions) == {"robot", "robot.local"}
    assert queried == ["http://robot:5000/get/system/catalog"]
    queried.clear()
    assert len(discovery.discover_at_addresses(["robot:5000", "robot.local:5000"])) == 2
    assert set(queried) == {
        "http://robot:5000/get/system/catalog",
        "http://robot.local:5000/get/system/catalog",
    }
