"""Simulation selection and fleet checks must precede deployment side effects."""
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.fleet import ExpectedSystemType, FleetValidationError, validate_fleet_profiles
from backend.deployment.compilation.util.capabilities import Capability
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro
from backend.deployment.module.contracts import CapabilityRequirement, TargetRequirements
from backend.deployment.network_api import zeroconf as discovery
from backend.deployment.network_api.system_api import System


def device(name: str, architecture: str = "aarch64", cuda: bool = False) -> discovery.SystemCatalog:
    return discovery.SystemCatalog(
        hostname=name + ".local", system_name=name, watchdog_port=5000,
        autobahn_port=8080, blitz_path="/blitz", machine_architecture=architecture,
        platform_description="Linux-glibc2.36", python_major_version=3,
        python_minor_version=11, os_distribution_id="debian",
        os_distribution_version_id="12", capabilities={"cuda": "12.2"} if cuda else {},
    )


ARM = TargetRequirements(architectures=(Architecture.ARM64,))
CUDA = TargetRequirements(capabilities=(CapabilityRequirement(Capability.CUDA, "12.2"),))


def test_simulation_uses_declared_endpoints_and_the_regular_catalog(monkeypatch):
    options = BlitzNetworkDeployer.Options().set_simulation().set_simulation_devices([
        "127.0.0.1:15000", "127.0.0.1:25000",
    ]).require_fleet_size(2)
    requests = []
    def get(url, **kwargs):
        requests.append(url)
        profile = device("one" if ":15000/" in url else "two")
        return SimpleNamespace(status_code=200, raise_for_status=lambda: None,
            json=lambda: {"schema_version": 3, "system": asdict(profile)})
    monkeypatch.setattr(discovery.requests, "get", get)
    monkeypatch.setattr(discovery, "Zeroconf", lambda: pytest.fail("simulation attempted mDNS"))
    systems = BlitzNetworkDeployer._find_systems(options)
    assert len(systems) == 2
    assert set(requests) == {
        "http://127.0.0.1:15000/get/system/catalog",
        "http://127.0.0.1:25000/get/system/catalog",
    }
    assert {system.ssh_port for system in systems} == {22}


def test_configured_simulators_are_ignored_in_default_physical_mode(monkeypatch):
    options = BlitzNetworkDeployer.Options().set_simulation_devices(["127.0.0.1:15000"])
    calls = []
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **kwargs: calls.append(kwargs) or {device("physical")})
    monkeypatch.setattr("backend.deployment.deployer.discover_at_addresses", lambda *_args, **_kwargs: pytest.fail("simulator selected without flag"))
    assert len(BlitzNetworkDeployer._find_systems(options)) == 1
    assert len(calls) == 1


@pytest.mark.parametrize("pinned", [(), ("physical.local:5000",)])
def test_incomplete_or_ambiguous_simulation_never_falls_back(monkeypatch, pinned):
    options = BlitzNetworkDeployer.Options(simulation=True, pinned_devices=pinned)
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **kwargs: pytest.fail("mDNS fallback"))
    monkeypatch.setattr("backend.deployment.deployer.discover_at_addresses", lambda *_args, **_kwargs: pytest.fail("physical fallback"))
    with pytest.raises(ValueError, match="Simulation mode"):
        BlitzNetworkDeployer._find_systems(options)


def test_cli_enables_simulation_and_can_override_declared_addresses(monkeypatch):
    options = BlitzNetworkDeployer.Options().set_simulation_devices(["127.0.0.1:15000"])
    seen = []
    monkeypatch.setattr(BlitzNetworkDeployer, "discover", lambda modules, config: seen.append(config))
    BlitzNetworkDeployer.run_cli([], lambda names: {}, options, [
        "discover", "--simulation", "--device", "127.0.0.1:25000", "--expected-systems", "1",
    ])
    assert seen[0].simulation is True
    assert seen[0].simulation_devices == ("127.0.0.1:25000",)
    assert seen[0].pinned_devices == ()
    assert seen[0].expected_system_count == 1


@pytest.mark.parametrize("addresses", [
    ["127.0.0.1:15000", "127.0.0.1:25000"],
    ["127.0.0.1:15000", "127.0.0.1:25000", "127.0.0.1:35000", "127.0.0.1:45000"],
])
def test_exact_count_mismatch_is_reported_before_any_catalog(monkeypatch, addresses):
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("count mismatch requested a catalog"))
    with pytest.raises(FleetValidationError, match="expected exactly 3 devices"):
        discovery.discover_at_addresses(addresses, expected_count=3)


def test_exclusions_and_duplicate_addresses_do_not_inflate_count(monkeypatch):
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("insufficient allowed devices"))
    with pytest.raises(FleetValidationError, match="found 1"):
        discovery.discover_at_addresses([
            "127.0.0.1:15000", "127.0.0.1:15000", "192.0.2.10:5000",
        ], blacklist=["192.0.2.10"], expected_count=2)


def test_mdns_count_is_checked_after_exclusions_and_before_http(monkeypatch):
    endpoints = {discovery.DiscoveredEndpoint("one.local", 5000), discovery.DiscoveredEndpoint("blocked.local", 5000)}
    monkeypatch.setattr(discovery, "discover_endpoints_on_network", lambda *_args, **kwargs: endpoints)
    monkeypatch.setattr(discovery.requests, "get", lambda *_args, **_kwargs: pytest.fail("count mismatch requested a catalog"))
    with pytest.raises(FleetValidationError, match="found 1"):
        discovery.discover_all_on_network(blacklist=["blocked.local"], expected_count=2)


@pytest.mark.parametrize("operation", ["deploy", "discover", "distribute"])
def test_wrong_profile_blocks_build_inventory_process_assignment_and_transfer(monkeypatch, tmp_path, operation):
    options = BlitzNetworkDeployer.Options().set_build_folder_path(str(tmp_path)).require_device_profiles([
        ExpectedSystemType("CUDA ARM", 1, TargetRequirements(architectures=(Architecture.AARCH64,), capabilities=CUDA.capabilities)),
    ])
    monkeypatch.setattr("backend.deployment.deployer.discover_all_on_network", lambda **kwargs: {device("cpu")})
    monkeypatch.setattr(BlitzNetworkDeployer, "_remember_systems", lambda *_args: pytest.fail("inventory written"))
    monkeypatch.setattr(BlitzNetworkDeployer, "prepare_systems", lambda *_args: pytest.fail("build prepared"))
    monkeypatch.setattr("backend.deployment.deployer.Rsyncer", lambda **kwargs: pytest.fail("transfer started"))
    mapper = lambda names: pytest.fail("process mapper invoked")
    with pytest.raises(FleetValidationError, match="CUDA ARM"):
        if operation == "discover":
            BlitzNetworkDeployer.discover([], options)
        else:
            getattr(BlitzNetworkDeployer, operation)([], mapper, options)
    assert list(tmp_path.iterdir()) == []


def test_explicit_distribute_systems_must_also_match_fleet(monkeypatch):
    options = BlitzNetworkDeployer.Options().require_fleet_size(2)
    with pytest.raises(FleetValidationError, match="found 1"):
        BlitzNetworkDeployer.distribute([], lambda names: pytest.fail("mapper invoked"), options, systems={System(device("one"))})


def test_overlapping_profile_slots_need_distinct_devices():
    options = BlitzNetworkDeployer.Options().require_device_profiles([
        ExpectedSystemType("ARM", 2, ARM), ExpectedSystemType("CUDA", 1, CUDA),
    ])
    systems = {System(device("gpu", cuda=True)), System(device("arm")), System(device("intel", "x86_64"))}
    with pytest.raises(FleetValidationError, match="distinct devices"):
        BlitzNetworkDeployer._validate_fleet(options, systems)


def test_overlapping_profiles_can_be_matched_without_greedy_misassignment():
    options = BlitzNetworkDeployer.Options().require_device_profiles([
        ExpectedSystemType("ARM", 1, ARM), ExpectedSystemType("CUDA", 1, CUDA),
    ])
    BlitzNetworkDeployer._validate_fleet(options, {System(device("gpu", cuda=True)), System(device("arm"))})


def test_overlapping_capabilities_can_reassign_several_existing_matches():
    systems = [device("one"), device("two"), device("three")]
    systems[0].capabilities = {"cuda": "12.2", "v4l2": "present"}
    systems[1].capabilities = {"cuda": "12.2", "v4l2": "present", "gpio": "present"}
    systems[2].capabilities = {"gpio": "present"}
    validate_fleet_profiles([system.to_system_id() for system in systems], [
        ExpectedSystemType("CUDA", 1, CUDA),
        ExpectedSystemType("GPIO", 1, TargetRequirements(capabilities=(CapabilityRequirement(Capability.GPIO),))),
        ExpectedSystemType("Video", 1, TargetRequirements(capabilities=(CapabilityRequirement(Capability.V4L2),))),
    ])


def test_full_profile_constraints_and_unclassified_remaining_slots():
    targets = TargetRequirements(architectures=(Architecture.AARCH64,), distros=(LinuxDistro.DEBIAN_12,), python_versions=((3, 11),), capabilities=CUDA.capabilities)
    options = BlitzNetworkDeployer.Options().require_fleet_size(3).require_device_profiles([
        ExpectedSystemType("ARM CUDA Python 3.11", 1, targets),
    ])
    systems = {System(device("gpu", cuda=True)), System(device("arm")), System(device("intel", "x86_64"))}
    BlitzNetworkDeployer._validate_fleet(options, systems)
    next(system for system in systems if system.general_info.system_name == "gpu").general_info.python_minor_version = 12
    with pytest.raises(FleetValidationError, match="0/1 matched"):
        BlitzNetworkDeployer._validate_fleet(options, systems)


@pytest.mark.parametrize("count", [0, -1, True, 2.5, "3"])
def test_invalid_expected_count_is_rejected_without_discovery(count):
    with pytest.raises(ValueError, match="positive integer"):
        BlitzNetworkDeployer.Options().require_fleet_size(count)


def test_type_counts_cannot_exceed_total():
    with pytest.raises(ValueError, match="exceeding expected count"):
        BlitzNetworkDeployer.Options().require_fleet_size(1).require_device_profiles([ExpectedSystemType("ARM", 2, ARM)])


def test_fleet_count_and_profiles_are_optional():
    BlitzNetworkDeployer._validate_fleet(BlitzNetworkDeployer.Options(), {System(device("one")), System(device("two"))})


def test_types_only_configuration_derives_an_exact_count():
    options = BlitzNetworkDeployer.Options().require_device_profiles([ExpectedSystemType("ARM", 2, ARM)])
    with pytest.raises(FleetValidationError, match="expected exactly 2"):
        BlitzNetworkDeployer._validate_fleet(options, {System(device("one"))})


def test_previous_option_names_remain_compatible():
    profiles = [ExpectedSystemType("ARM", 2, ARM)]
    options = BlitzNetworkDeployer.Options()
    assert options.set_expected_system_count(2) is options
    assert options.set_expected_system_types(profiles) is options
    BlitzNetworkDeployer._validate_fleet(options, {System(device("one")), System(device("two"))})
    with pytest.raises(FleetValidationError, match="expected exactly 2"):
        BlitzNetworkDeployer._validate_fleet(options, {System(device("one"))})
