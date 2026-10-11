"""Exercise the real HTTP catalog and client pipeline across a local socket."""
from __future__ import annotations

from collections.abc import Iterator
import json
import threading
from types import SimpleNamespace

from flask import Flask, request
import pytest
import requests
from werkzeug.serving import make_server

from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.zeroconf import discover_at_addresses
from watchdog.routes import getters
from watchdog.util import system as watchdog_system


@pytest.fixture
def catalog_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, list[str], list[str]]]:
    app = Flask(__name__)
    app.register_blueprint(getters.GETTERS_BP)
    paths: list[str] = []
    probes: list[str] = []

    @app.before_request
    def record_request() -> None:
        paths.append(request.path)

    server = make_server("127.0.0.1", 0, app, threaded=True)
    port = server.server_port
    profile = watchdog_system.SystemCatalog(
        hostname="sim-one.local", system_name="sim-one", watchdog_port=port,
        autobahn_port=18080, blitz_path="/opt/blitz", machine_architecture="aarch64",
        platform_description="Linux-with-glibc2.36", python_major_version=3,
        python_minor_version=11, os_distribution_id="debian",
        os_distribution_version_id="12", ssh_port=12222,
        watchdog_host="127.0.0.1", autobahn_host="127.0.0.1", ssh_host="127.0.0.1",
        capabilities={"gpio": "present"},
    )

    def collect() -> watchdog_system.SystemCatalog:
        probes.append("collected")
        return profile

    monkeypatch.setattr(watchdog_system, "collect_system_catalog", collect)
    announcement = watchdog_system.DiscoveryAnnouncement(
        hostname=profile.hostname, system_name=profile.system_name,
        watchdog_port=profile.watchdog_port, autobahn_port=profile.autobahn_port,
        ssh_port=profile.ssh_port, watchdog_host=profile.watchdog_host,
        autobahn_host=profile.autobahn_host, ssh_host=profile.ssh_host,
    )
    monkeypatch.setattr(
        watchdog_system.DiscoveryAnnouncement, "collect", lambda config=None: announcement,
    )
    monkeypatch.setattr(
        watchdog_system, "load_basic_system_config",
        lambda: SimpleNamespace(discovery=SimpleNamespace(catalog_refresh_interval_seconds=300)),
    )
    monkeypatch.setattr(getters, "system_catalog_cache", watchdog_system.SystemCatalogCache())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"127.0.0.1:{port}", paths, probes
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_http_catalog_bootstraps_a_simulator_with_mapped_services(
    catalog_server: tuple[str, list[str], list[str]],
) -> None:
    address, paths, probes = catalog_server
    # Duplicate seeds must not produce duplicate requests or duplicate targets.
    systems = discover_at_addresses([address, address])
    assert len(systems) == 1
    profile = next(iter(systems))
    assert profile.to_system_id().capabilities == (("gpio", "present"),)
    target = System(profile)
    assert target.watchdog_url() == f"http://{address}/"
    assert target.ssh_port == 12222
    assert target.remote_host == "ubuntu@127.0.0.1"
    assert profile.autobahn_host == "127.0.0.1"
    assert profile.autobahn_port == 18080
    assert paths == ["/get/system/catalog"]
    assert probes == ["collected"]

    # Repeated catalog requests share one hardware snapshot.
    response = requests.get(f"http://{address}/get/system/catalog", timeout=5)
    response.raise_for_status()
    assert response.json()["schema_version"] == 3
    discover_at_addresses([address])
    assert probes == ["collected"]


def test_blacklisting_a_known_simulator_prevents_any_http_or_probe(
    catalog_server: tuple[str, list[str], list[str]],
) -> None:
    address, paths, probes = catalog_server
    assert discover_at_addresses([address], blacklist=["127.0.0.1"]) == set()
    assert paths == []
    assert probes == []


def test_prepared_deployment_reuses_catalog_and_process_plan(catalog_server, monkeypatch, tmp_path):
    from backend.deployment.deployer import BlitzNetworkDeployer
    from backend.deployment.compilation.system_builder import SystemBuilder

    address, paths, probes = catalog_server
    options = (BlitzNetworkDeployer.Options().set_pinned_devices([address])
               .set_build_folder_path(str(tmp_path / "build")))
    assignments = []
    def mapper(names):
        assignments.append(names)
        return {name: [] for name in names}
    context = BlitzNetworkDeployer.prepare_deployment([], mapper, options)
    assert paths == ["/get/system/catalog"]
    monkeypatch.setattr(BlitzNetworkDeployer, "_find_systems", lambda *_args: pytest.fail("recollected fleet"))
    monkeypatch.setattr(BlitzNetworkDeployer, "_preflight", lambda *_args: pytest.fail("repeated placement"))
    monkeypatch.setattr(BlitzNetworkDeployer, "prepare_systems", lambda *_args: None)
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: True)
    monkeypatch.setattr(BlitzNetworkDeployer, "build_bundles", lambda *_args: {})
    transferred = []
    monkeypatch.setattr(BlitzNetworkDeployer, "distribute_prepared", transferred.append)
    BlitzNetworkDeployer.deploy_prepared(context)
    assert transferred == [context]
    assert assignments == [["sim-one"]]
    assert paths == ["/get/system/catalog"]
    assert probes == ["collected"]
