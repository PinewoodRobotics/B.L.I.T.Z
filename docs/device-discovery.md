# Device discovery and capabilities (BLITZ 3.0)

Discovery has one collection phase for each deployment:

1. Browse all watchdog mDNS announcements, or receive explicit watchdog addresses.
2. Remove devices matching the hostname/IP blacklist.
3. Fetch one HTTP system catalog from every remaining watchdog.
4. Validate the complete result before preparing builds or transferring files.
5. Reuse that in-memory catalog for compatibility, bundling, and deployment.

A missing or invalid catalog fails the phase; BLITZ does not silently deploy to
a partial fleet. The client does not ask the same watchdog for its system profile
again during that deployment. Catalog requests use a ten-second timeout, allowing
the bounded hardware probes to finish on the first uncached request.

## Lightweight mDNS

The service type is `_watchdog._tcp.local.`. The service record's port is the
advertised watchdog HTTP port, not a hardcoded default. Address records identify
the reachable machine. The TXT metadata contains only connection information:

| Field | Meaning |
| --- | --- |
| `schema_version` | `3`; watchdog and client must agree on the protocol. |
| `hostname` | Advertised device hostname. |
| `system_name` | BLITZ application/process-placement name. |
| `watchdog_port` | Reachable HTTP API port. |
| `autobahn_port` | Reachable Autobahn port. |
| `ssh_port` | Reachable SSH port used for bundle transfer. |
| `watchdog_host` | Host serving the watchdog API. |
| `autobahn_host` | Host serving Autobahn; may differ from the device host. |
| `ssh_host` | Host serving SSH; may differ from the device host. |

mDNS does not collect or advertise architecture, OS, Python, installation paths,
or capabilities. Its advertising loop never runs hardware probes.

## One HTTP catalog

`GET /get/system/catalog` returns a versioned envelope:

```json
{
  "schema_version": 3,
  "system": {
    "hostname": "robot-one.local",
    "system_name": "robot-one",
    "watchdog_host": "robot-one.local",
    "watchdog_port": 5000,
    "autobahn_host": "robot-one.local",
    "autobahn_port": 8080,
    "ssh_host": "robot-one.local",
    "ssh_port": 22,
    "blitz_path": "/opt/blitz",
    "machine_architecture": "aarch64",
    "platform_description": "Linux-with-glibc2.36",
    "python_major_version": 3,
    "python_minor_version": 11,
    "os_distribution_id": "debian",
    "os_distribution_family": null,
    "os_distribution_version_id": "12",
    "capabilities": {}
  }
}
```

Values above are illustrative. The profile contains the same identity/endpoint
fields plus build specifications. `capabilities` is a native JSON object. The
watchdog and client share `SystemCatalog` in `network_api/catalog.py`; HTTP
parsing validates JSON types directly. `/get/system/catalog` is the sole catalog
route; the old identity route and unversioned response are removed.

The watchdog caches the expensive system/capability snapshot in memory. The
first request collects it; the first request after the configured refresh
interval collects it again. The default is 300 seconds. A lock prevents
concurrent callers from launching duplicate probes, and callers receive a
complete snapshot rather than partial probe results. Cheap identity and service
endpoint metadata is read from the current configuration on each HTTP request,
so updating port mappings does not wait for the hardware refresh interval.

## Selecting and excluding targets

```bash
# Automatic endpoint discovery, excluding specific devices before HTTP requests:
python3 backend/deploy.py --blacklist spare.local --blacklist 192.168.1.90

# Known simulator addresses use the same catalog path:
python3 backend/deploy.py --device 127.0.0.1:15000 --device 127.0.0.1:25000

# IPv6 addresses in HOST:PORT arguments need brackets:
python3 backend/deploy.py --device '[::1]:15000'
```

Blacklists match the machine hostnames and IP addresses available during endpoint
discovery, including advertised address records. Matching normalizes hostnames
and IP spelling. When an IP blacklist is present, pinned hostname targets are
resolved before any catalog requests; any matching address excludes the target.
If that required resolution fails, collection stops before HTTP. An explicit
IP-only target cannot reveal an otherwise unknown
hostname until its catalog is fetched; blacklist that known IP to exclude it
before the request. No empty selection falls back to other devices.

The contacted address remains the watchdog destination. SSH and Autobahn hosted
on that same machine use the contacted address too; separate service hosts stay
as advertised. Connection deduplication preserves full DNS names and IPv6 scope
identifiers, so devices on different network links are not merged.

Only distinct system build-profile keys are stored in
`build/backend-bundle/systems.json`. These describe architecture, distribution,
runtime ABI, and capabilities for offline cache preparation. They are not device
IDs or remembered destinations. Legacy stored `devices` entries are ignored and
removed when inventory is rewritten. Live hostnames, addresses, and ports are
resolved again for each deployment.

## Docker simulation networking

Configure simulation targets directly in `backend/deploy.py`:

```python
SIMULATION_ENABLED = False
SIMULATION_DEVICES = (
    "127.0.0.1:15000",
    "127.0.0.1:25000",
    "127.0.0.1:35000",
)
```

Then run `python3 backend/deploy.py --simulation`, or set `SIMULATION_ENABLED`
to `True` to make it the script's default. Simulation is off by default. It skips
mDNS entirely and uses the ordinary blacklist and HTTP catalog path for those
addresses. The Docker containers must already be running and publishing their
watchdog HTTP ports; the flag selects them, rather than launching containers.
An empty simulation list is an error and never falls back to physical devices.
Simulation mode also rejects a separately configured physical pinned-device list.

For a temporary simulation address override:

```bash
python3 backend/deploy.py --simulation --device 127.0.0.1:15000
```

Use `--simulation` with the live `discover`, `deploy` (default), or `distribute`
phases. Offline `build` and `cache` use recorded build profiles and do not contact
any fleet, so live fleet expectations do not apply to those phases.

Run the ordinary watchdog in the container. Configure externally reachable
endpoints through the optional `discovery` section in its existing basic system
configuration. For a simulator reached by a client on the Docker host:

```json
{
  "discovery": {
    "hostname": "sim-one.local",
    "addresses": ["127.0.0.1"],
    "watchdog_host": "127.0.0.1",
    "watchdog_port": 15000,
    "autobahn_host": "127.0.0.1",
    "autobahn_port": 18080,
    "ssh_host": "127.0.0.1",
    "ssh_port": 12222,
    "catalog_refresh_interval_seconds": 300
  }
}
```

This is a configuration fragment, not a complete basic system configuration.
The simulation launcher must publish matching Docker ports and provide each
watchdog address to the client. Listening ports inside the container stay in
the ordinary watchdog/Autobahn configuration; advertised ports describe what
the client can reach. Use a reachable host address rather than loopback when
the client is on another machine. No mDNS bridge is needed for `--device`.

System specifications and capabilities describe what the container can actually
execute and access. Naming a container after a Jetson does not grant ARM or CUDA
support. Installation and process management use the ordinary watchdog paths.

## Optional fleet expectations

In `backend/deploy.py`, set `FLEET_SIZE = 3` to require exactly three
devices. `None` disables this check. `--expected-systems 3` overrides the script's
count for one command. Blacklisted endpoints and duplicate addresses do not
count; too few or too many devices stops collection before any HTTP catalogs,
build preparation, inventory writes, process assignment, or transfer.

For optional system-type checks, reuse `TargetRequirements`. For example:

```python
from backend.deployment.fleet import ExpectedSystemType
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro
from backend.deployment.compilation.util.capabilities import Capability
from backend.deployment.module.contracts import TargetRequirements, CapabilityRequirement

FLEET_SIZE = 3
DEVICE_PROFILES = (
    ExpectedSystemType("ARM Debian", 2, TargetRequirements(
        architectures=(Architecture.AARCH64,),
        distros=(LinuxDistro.DEBIAN_11, LinuxDistro.DEBIAN_12),
    )),
    ExpectedSystemType("ARM CUDA", 1, TargetRequirements(
        architectures=(Architecture.AARCH64,),
        capabilities=(CapabilityRequirement(Capability.CUDA),),
    )),
)
```

Each type requires distinct devices matching its architecture, distro, Python,
and capability constraints. Matching handles overlapping profiles without
counting the same device twice. These are deployment profiles; labels do not
prove an exact physical board model such as a Raspberry Pi 5 or Jetson Nano.
Checks use the already-collected catalogs and perform no additional probes.

Both settings are optional. If only types are supplied, their counts imply an
exact fleet total. If an explicit total exceeds the sum of the type counts,
the remaining devices may have any supported profile. Type counts exceeding
the explicit total are a configuration error. Expectations apply equally to
physical and simulation discovery, and to distributing already-built bundles.
They do not choose a subset of a larger discovered fleet automatically.

The equivalent typed option setters are `set_simulation`,
`set_simulation_devices`, `require_fleet_size`, and
`require_device_profiles`. Installer-generated deployment scripts expose the
same defaults. Existing customized scripts can add these setters without
changing `get_modules()` or `pi_name_to_process_types()`.

## Official capability registry

Use `Capability` from `backend.deployment.compilation.util.capabilities` in
module declarations. Known legacy names such as `"cuda"` remain accepted;
unknown names are errors.

| Capability | Value | What detection establishes |
| --- | --- | --- |
| `Capability.CUDA` | Numeric version | CUDA driver support for an accessible NVIDIA GPU, reported by `nvidia-smi` or the initialized CUDA driver API; not an installed toolkit. |
| `Capability.NVIDIA_DRIVER` | Numeric version | NVIDIA driver version reported by the same probe. |
| `Capability.V4L2` | `"present"` | At least one readable/writable `/dev/videoN` character device; no camera or codec guarantee. |
| `Capability.I2C` | `"present"` | At least one accessible `/dev/i2c-N` character device; no attached-peripheral guarantee. |
| `Capability.SPI` | `"present"` | At least one accessible `/dev/spidevN.N` character device; no attached-peripheral guarantee. |
| `Capability.GPIO` | `"present"` | At least one accessible `/dev/gpiochipN` character device; no guarantee a particular pin is available. |

Versioned capabilities allow numeric minimum-version requirements. Presence-only
capabilities allow presence requirements and reject minimum versions:

```python
from backend.deployment.compilation.util.capabilities import Capability
from backend.deployment.module.contracts import CapabilityRequirement, TargetRequirements

cuda_targets = TargetRequirements(
    capabilities=(CapabilityRequirement(Capability.CUDA, minimum_version="12.2"),),
)
gpio_targets = TargetRequirements(
    capabilities=(CapabilityRequirement(Capability.GPIO),),
)
```

The existing `LinuxDistro` enum maps target distributions to Docker build images
and candidate detector families. A cheap accessible-device scan gates expensive
probes. The NVIDIA family normally uses one command to report both NVIDIA values;
the Linux-device-interface family obtains several results from one scan.
When `nvidia-smi` is absent, fails, or cannot report CUDA support, a driver-API
subprocess verifies driver initialization and a positive GPU count before
reporting CUDA support. Each command has a three-second timeout, so the NVIDIA
family takes at most two bounded probes. A successful SMI driver version is
retained during fallback; failed SMI output never supplies a driver version.
The fallback does not invent an NVIDIA desktop driver version from a Jetson/L4T
release number.
Distribution and architecture only select applicable checks; they never imply
that hardware is available. Missing permissions, devices, or diagnostic tools
produce absence, not assumed support.

To add support, define a capability's meaning and value type in the registry,
associate it with a detector family, implement a conservative bounded probe,
update applicable profile mappings, and test positive, absent, and failure cases.
Do not introduce private capability names only in an application declaration.

## Upgrading from 1.x or 2.x

Update the deployment backend and watchdogs together. The mDNS service type,
metadata contract, HTTP envelope, and accepted capability names changed in 2.0.
Version 3 replaces string-encoded capabilities with an object and removes the
identity route. Update image provisioning, watchdogs, and application deployment
libraries together; schema version 2 is rejected explicitly.
Old full-profile mDNS announcements and old unversioned HTTP responses are not
valid catalogs. The client reports incompatibility rather than guessing missing
specifications or combining contradictory metadata.
