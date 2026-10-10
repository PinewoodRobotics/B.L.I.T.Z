from __future__ import annotations

import json
from pathlib import Path
import socket
from types import SimpleNamespace
import zipfile

import pytest
from zeroconf import ServiceInfo, Zeroconf

from backend.deployment.bundle_index import save_bundle_index
from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.network_api.zeroconf import (
    SERVICE,
    DiscoveredNetworkSystem,
    discover_at_addresses,
)


def make_system(name: str, hostname: str) -> DiscoveredNetworkSystem:
    return DiscoveredNetworkSystem(
        hostname=hostname,
        system_name=name,
        watchdog_port=5000,
        autobahn_port=8080,
        blitz_path=FolderPath("/opt/blitz"),
        machine_architecture="aarch64",
        platform_description="Linux-with-glibc2.36",
        python_major_version=3,
        python_minor_version=11,
        os_distribution_id="debian",
        os_distribution_version_id="12",
    )


def options(tmp_path: Path) -> BlitzNetworkDeployer.Options:
    return (
        BlitzNetworkDeployer.Options()
        .set_build_folder_path(FolderPath(str(tmp_path / "build")))
        .set_output_folder_path(FolderPath(str(tmp_path / "bundles")))
        .build()
    )


def prepare_context(config: BlitzNetworkDeployer.Options, system_id) -> Path:
    context = (
        Path(config.build_folder_path)
        / config.bundle_name
        / "contexts"
        / system_id.to_build_key()
    )
    context.mkdir(parents=True)
    (context / "Dockerfile").write_text(f"FROM {system_id.linux_distro.value}\n")
    (context / "build-plan.json").write_text(json.dumps({"system": {
        "glibc": system_id.c_lib_version,
        "distro": system_id.linux_distro.value,
        "architecture": system_id.architecture.value,
        "python_major": system_id.python_version.major,
        "python_minor": system_id.python_version.minor,
    }, "steps": []}))
    return context


def test_discover_prepares_dockerfile_per_system_type_without_building(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    systems = {make_system("one", "one.local"), make_system("two", "two.local")}
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: systems)
    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.bundle", lambda *_args, **_kw: pytest.fail("build called"))
    prepared: list[str] = []

    def fake_prepare(bundler) -> None:
        prepared.append(bundler.system_id.to_build_key())
        prepare_context(config, bundler.system_id)

    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.prepare", fake_prepare)
    result = BlitzNetworkDeployer.discover([], config)
    assert len(result) == 1
    assert prepared == [result[0].to_build_key()]
    assert len(list((Path(config.build_folder_path) / config.bundle_name / "contexts").glob("*/Dockerfile"))) == 1
    inventory = json.loads((Path(config.build_folder_path) / config.bundle_name / "systems.json").read_text())
    assert sorted(inventory["devices"]) == ["one.local", "two.local"]
    assert inventory["system_ids"] == [result[0].to_build_key()]


def test_discover_writes_a_real_dockerfile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system = make_system("one", "one.local")
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: {system})

    BlitzNetworkDeployer.discover([], config)

    dockerfiles = list(Path(config.build_folder_path).glob("**/Dockerfile"))
    assert len(dockerfiles) == 1
    assert dockerfiles[0].parent.parent == Path(config.build_folder_path) / config.bundle_name / "contexts"
    assert "FROM --platform=linux/arm64 debian:12 AS dependencies\n" in dockerfiles[0].read_text()
    assert (dockerfiles[0].parent / "build_system.sh").is_file()
    assert (dockerfiles[0].parent / "build-plan.json").is_file()
    assert not (Path(config.build_folder_path) / "artifacts").exists()


def test_advertised_mdns_system_generates_dockerfile(tmp_path: Path) -> None:
    config = options(tmp_path).set_discovery_timeout(3)
    system = make_system("advertised", "advertised.local.")
    properties = {
        key: str(value) for key, value in vars(system).items()
        if key != "hostname" and value is not None
    }
    service = ServiceInfo(
        SERVICE, "blitz-dockerfile-test." + SERVICE,
        addresses=[socket.inet_aton("127.0.0.1")], port=9999,
        server=system.hostname, properties=properties,
    )
    zeroconf = Zeroconf()
    try:
        zeroconf.register_service(service)
        BlitzNetworkDeployer.discover([], config)
        dockerfiles = list(Path(config.build_folder_path).glob("**/Dockerfile"))
        assert len(dockerfiles) == 1
        assert "debian:12" in dockerfiles[0].read_text()
    finally:
        zeroconf.unregister_service(service)
        zeroconf.close()


def test_pinned_device_reads_watchdog_identity_without_mdns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system = make_system("pinned", "device.local")
    requested: list[str] = []

    def fake_get(url: str, *, timeout: int):
        requested.append(url)
        assert timeout == 5
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: vars(system))

    monkeypatch.setattr("backend.deployment.network_api.zeroconf.requests.get", fake_get)
    monkeypatch.setattr(
        "backend.deployment.deployer.discover_all_on_network",
        lambda **_kw: pytest.fail("mDNS called"),
    )
    BlitzNetworkDeployer.run_cli(
        [], lambda _names: {}, config,
        ["discover", "--device", "192.0.2.10:5000"],
    )
    assert config.pinned_devices == ("192.0.2.10:5000",)
    assert requested == ["http://192.0.2.10:5000/get/system/identity"]
    assert len(list(Path(config.build_folder_path).glob("**/Dockerfile"))) == 1
    assert discover_at_addresses(["192.0.2.10:5000"]).pop().hostname == "192.0.2.10"


def test_known_system_profile_generates_dockerfile_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system_id = make_system("previous", "previous.local").to_system_id()
    monkeypatch.setattr(
        "backend.deployment.deployer.discover_all_on_network",
        lambda **_kw: pytest.fail("mDNS called"),
    )
    monkeypatch.setattr(
        "backend.deployment.deployer.discover_at_addresses",
        lambda _addresses: pytest.fail("HTTP discovery called"),
    )

    BlitzNetworkDeployer.run_cli(
        [], lambda _names: {}, config,
        ["discover", "--system-id", system_id.to_build_key()],
    )

    dockerfiles = list(Path(config.build_folder_path).glob("**/Dockerfile"))
    assert len(dockerfiles) == 1
    assert "FROM --platform=linux/arm64 debian:12 AS dependencies\n" in dockerfiles[0].read_text()


def test_build_uses_prepared_dockerfile_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system_id = make_system("one", "one.local").to_system_id()
    prepare_context(config, system_id)
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: pytest.fail("discovery called"))
    built: list[str] = []

    def fake_bundle(
        bundler, *, prepared: bool = False, dependency_image: str | None = None
    ) -> FilePath:
        assert prepared
        assert dependency_image is None
        built.append(bundler.system_id.to_build_key())
        output = Path(config.output_folder_path) / f"{bundler.system_key}.zip"
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("artifact", "ready")
        return FilePath(str(output))

    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.bundle", fake_bundle)
    bundles = BlitzNetworkDeployer.build_bundles([], config)
    assert built == [system_id.to_build_key()]
    assert set(bundles) == set(built)
    assert (Path(config.output_folder_path) / "bundle-index.json").is_file()


def test_distribute_rediscovers_and_checks_prebuilt_bundles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path).set_pinned_devices(["one.local:5000"])
    system = make_system("one", "one.local")
    key = system.to_system_id().to_build_key()
    archive = Path(config.output_folder_path) / f"{key}.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"prepared bundle")
    save_bundle_index(archive.parent / "bundle-index.json", {key: archive})
    monkeypatch.setattr("backend.deployment.deployer.discover_at_addresses", lambda _addresses: {system})
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: pytest.fail("mDNS called"))
    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.bundle", lambda *_args, **_kw: pytest.fail("build called"))
    deployed: list[str] = []
    monkeypatch.setattr("backend.deployment.deployer.Rsyncer.deploy", lambda self: deployed.extend(system.general_info.hostname for system in self.systems))
    monkeypatch.setattr("backend.deployment.network_api.system_api.System.set_config", lambda *_args: True)
    monkeypatch.setattr("backend.deployment.network_api.system_api.System.set_processes", lambda *_args: True)

    BlitzNetworkDeployer.distribute([], lambda _names: {}, config)
    assert deployed == ["one.local"]

    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Missing or changed bundle"):
        BlitzNetworkDeployer.distribute([], lambda _names: {}, config)


def test_one_command_discovers_then_fails_before_distribution_when_cache_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system = make_system("one", "one.local")
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: {system})
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: False)
    monkeypatch.setattr(SystemBuilder, "stale_dependency_images", lambda _self: [])
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("prompted without a cached image"))
    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.bundle", lambda *_args, **_kw: pytest.fail("built before cache check"))
    monkeypatch.setattr("backend.deployment.deployer.Rsyncer.deploy", lambda *_args: pytest.fail("distributed before cache check"))

    with pytest.raises(RuntimeError, match="python3 backend/deploy.py cache"):
        BlitzNetworkDeployer.run_cli([], lambda _names: {}, config, [])

    inventory = json.loads((Path(config.build_folder_path) / config.bundle_name / "systems.json").read_text())
    assert inventory["devices"]["one.local"]["machine_architecture"] == "aarch64"
    assert len(inventory["system_ids"]) == 1


@pytest.mark.parametrize("answer, deploys", [("yes", True), ("n", False), ("", False)])
def test_changed_dependencies_prompt_before_using_older_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    answer: str, deploys: bool,
) -> None:
    config = options(tmp_path)
    system = make_system("one", "one.local")
    key = system.to_system_id().to_build_key()
    old_image = f"blitz-deps-{key}-oldhash"
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: {system})
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: False)
    monkeypatch.setattr(SystemBuilder, "stale_dependency_images", lambda _self: [old_image])
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return answer

    monkeypatch.setattr("builtins.input", fake_input)
    images_used: list[str | None] = []

    def fake_bundle(bundler, *, prepared: bool, dependency_image: str | None) -> FilePath:
        assert prepared
        images_used.append(dependency_image)
        return _write_bundle(config, bundler.system_key)

    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.bundle", fake_bundle)
    deployed: list[str] = []
    monkeypatch.setattr("backend.deployment.deployer.Rsyncer.deploy", lambda self: deployed.extend(s.general_info.hostname for s in self.systems))
    monkeypatch.setattr("backend.deployment.network_api.system_api.System.set_config", lambda *_args: True)
    monkeypatch.setattr("backend.deployment.network_api.system_api.System.set_processes", lambda *_args: True)

    if deploys:
        BlitzNetworkDeployer.run_cli([], lambda _names: {}, config, [])
    else:
        with pytest.raises(RuntimeError, match="Deployment cancelled"):
            BlitzNetworkDeployer.run_cli([], lambda _names: {}, config, [])

    assert images_used == ([old_image] if deploys else [])
    assert deployed == (["one.local"] if deploys else [])
    assert prompts == ["Continue with these older images? [y/N]: "]
    output = capsys.readouterr().out
    assert "older images are cached" in output
    assert old_image in output


def test_cache_command_uses_recorded_types_without_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system = make_system("one", "one.local")
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: {system})
    BlitzNetworkDeployer.discover([], config)
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **_kw: pytest.fail("discovery called"))
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: False)
    cached: list[str] = []
    monkeypatch.setattr(SystemBuilder, "cache_dependencies", lambda self: cached.append(self.system_id.to_build_key()))

    cleaned: list[str] = []
    monkeypatch.setattr(SystemBuilder, "prune_stale_dependency_images", lambda self: cleaned.append(self.system_id.to_build_key()))
    BlitzNetworkDeployer.run_cli([], lambda _names: {}, config, ["cache"])
    assert cleaned == cached
    assert cached == [system.to_system_id().to_build_key()]


def test_one_command_reuses_cache_and_distributes_from_same_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = options(tmp_path)
    system = make_system("one", "one.local")
    discoveries = 0

    def find_systems(**_kwargs):
        nonlocal discoveries
        discoveries += 1
        return {system}

    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", find_systems)
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: True)
    monkeypatch.setattr("backend.deployment.deployer.CodeBundler.bundle", lambda self, **_kw: _write_bundle(config, self.system_key))
    deployed: list[str] = []
    monkeypatch.setattr("backend.deployment.deployer.Rsyncer.deploy", lambda self: deployed.extend(s.general_info.hostname for s in self.systems))
    monkeypatch.setattr("backend.deployment.network_api.system_api.System.set_config", lambda *_args: True)
    monkeypatch.setattr("backend.deployment.network_api.system_api.System.set_processes", lambda *_args: True)

    BlitzNetworkDeployer.run_cli([], lambda _names: {}, config, [])

    assert discoveries == 1
    assert deployed == ["one.local"]
    assert (Path(config.output_folder_path) / "bundle-index.json").is_file()


def _write_bundle(config: BlitzNetworkDeployer.Options, key: str) -> FilePath:
    output = Path(config.output_folder_path) / f"{key}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("artifact", "ready")
    return FilePath(str(output))


@pytest.mark.parametrize('already_cached,fail_second', [(True, False), (False, False), (False, True)])
def test_cache_cleans_only_after_all_replacements_succeed(tmp_path, monkeypatch, already_cached, fail_second):
    from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
    config = options(tmp_path)
    profiles = [
        SystemId('2.36', LinuxDistro.DEBIAN_12, Architecture.ARM64, PythonVersion(3, 11)),
        SystemId('2.39', LinuxDistro.UBUNTU_24, Architecture.ARM64, PythonVersion(3, 12)),
    ]
    BlitzNetworkDeployer._remember_system_ids(config, profiles)
    monkeypatch.setattr(BlitzNetworkDeployer, 'prepare_systems', lambda *_args: None)
    events = []
    class Builder:
        def __init__(self, profile):
            self.profile = profile
        def dependencies_cached(self):
            return already_cached
        def cache_dependencies(self):
            events.append('cache')
            if fail_second and len(events) == 2:
                raise RuntimeError('download failed')
        def prune_stale_dependency_images(self):
            events.append('cleanup')
    monkeypatch.setattr(BlitzNetworkDeployer, '_builder', lambda _config, profile: Builder(profile))
    if fail_second:
        with pytest.raises(RuntimeError, match='download failed'):
            BlitzNetworkDeployer.cache_dependencies([], config)
        assert events == ['cache', 'cache']
    else:
        BlitzNetworkDeployer.cache_dependencies([], config)
        assert events == (['cleanup', 'cleanup'] if already_cached else ['cache', 'cache', 'cleanup', 'cleanup'])
