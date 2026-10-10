from __future__ import annotations

from dataclasses import dataclass, fields, replace
from collections.abc import Sequence
import re
import json
import time
from urllib.parse import urlsplit
import ipaddress
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    PythonVersion,
    SystemId,
)
from backend.deployment.fleet import validate_fleet_count
from backend.deployment.network_api.utils import (
    FolderPath,
    ZeroconfPropertySchema,
    decode_zeroconf_hostname,
    decode_zeroconf_properties,
)
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf


SERVICE = "_watchdog._tcp.local."
CATALOG_SCHEMA_VERSION = 2


@dataclass
class DiscoveredNetworkSystem(ZeroconfPropertySchema):
    hostname: str  # EG: "nathan-hale.local"
    system_name: str  # EG: "nathan-hale"
    watchdog_port: int  # EG: 9999
    autobahn_port: int  # EG: 9999

    blitz_path: FolderPath  # EG: "/opt/blitz/B.L.I.T.Z"

    machine_architecture: str
    platform_description: str
    python_major_version: int
    python_minor_version: int
    os_distribution_id: str | None = None
    os_distribution_family: str | None = None
    os_distribution_version_id: str | None = None
    capabilities_json: str = "{}"
    ssh_port: int = 22
    watchdog_host: str | None = None
    autobahn_host: str | None = None
    ssh_host: str | None = None

    def _platform_text(self) -> str:
        return " ".join(
            value
            for value in [
                self.platform_description,
                self.os_distribution_id,
                self.os_distribution_family,
                self.os_distribution_version_id,
            ]
            if value
        ).lower()

    def to_system_id(self) -> SystemId:
        platform_text = self._platform_text()
        glibc_match = re.search(r"glibc(?P<version>\d+(?:\.\d+)*)", platform_text)
        if glibc_match is None:
            raise ValueError("Could not infer glibc version: " + str(self))

        glibc_version = glibc_match.group("version")

        try:
            architecture = Architecture.from_machine(self.machine_architecture)
        except ValueError as error:
            raise ValueError(str(error) + " for " + str(self)) from error

        try:
            linux_distro = LinuxDistro.from_os_release(
                os_id=self.os_distribution_id,
                os_id_like=self.os_distribution_family,
                version_id=self.os_distribution_version_id,
                platform_text=platform_text,
            )
        except ValueError as error:
            raise ValueError(str(error) + " for " + str(self)) from error

        return SystemId(
            capabilities=tuple(sorted(json.loads(self.capabilities_json).items())),
            c_lib_version=glibc_version,
            linux_distro=linux_distro,
            architecture=architecture,
            python_version=PythonVersion(
                major=self.python_major_version,
                minor=self.python_minor_version,
            ),
        )

    def __str__(self) -> str:
        lines: list[str] = []
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not None:
                lines.append(f"{field.name}: {value}")
        return "\n".join(lines)

    def __hash__(self) -> int:
        return hash((self.watchdog_host or self.hostname, self.watchdog_port))


def canonical_host(host: str) -> str:
    """Normalize equivalent hostname and IP spellings without querying devices."""
    value = host.strip().strip("[]").rstrip(".").lower()
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(address).split("%", 1)[0]
    except ValueError:
        return value.removesuffix(".local")


def http_authority(host: str, port: int) -> str:
    escaped_host = host.replace("%", "%25")
    return f"[{escaped_host}]:{port}" if ":" in host else f"{host}:{port}"


def _connection_host_key(host: str) -> str:
    """Identify a destination without conflating DNS names or IPv6 links."""
    value = host.strip().strip("[]").rstrip(".")
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(address)
    except ValueError:
        return value.lower()


def _port(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {name}: {value}")
    if not isinstance(value, (int, str)) or (isinstance(value, str) and not value.isdecimal()):
        raise ValueError(f"Invalid {name}: {value}")
    try:
        port = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {name}: {value}") from error
    if not 1 <= port <= 65535:
        raise ValueError(f"Invalid {name}: {value}")
    return port


@dataclass(frozen=True)
class DiscoveredEndpoint:
    """Connection data only. System probes happen after fleet-wide filtering."""

    hostname: str
    watchdog_port: int
    system_name: str | None = None
    autobahn_port: int | None = None
    ssh_port: int | None = None
    watchdog_host: str | None = None
    autobahn_host: str | None = None
    ssh_host: str | None = None
    addresses: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    @property
    def contact_host(self) -> str:
        host = self.watchdog_host or self.hostname
        if canonical_host(host) == canonical_host(self.hostname) and self.addresses:
            return self.addresses[0]
        return host

    @property
    def authority(self) -> str:
        return http_authority(self.contact_host, self.watchdog_port)

    def is_blacklisted(self, blacklist: Sequence[str]) -> bool:
        blocked = {canonical_host(value) for value in blacklist}
        candidates = (self.hostname, self.watchdog_host, *self.addresses, *self.aliases)
        return any(canonical_host(value) in blocked for value in candidates if value)

    @classmethod
    def from_service_info(cls, info: ServiceInfo) -> "DiscoveredEndpoint":
        properties = decode_zeroconf_properties(info.properties)
        if properties.get("schema_version") != str(CATALOG_SCHEMA_VERSION):
            raise ValueError("Watchdog discovery schema is incompatible; upgrade watchdog and deployer together to BLITZ 2")
        for name in ("hostname", "system_name", "watchdog_port", "autobahn_port", "ssh_port"):
            if not properties.get(name):
                raise ValueError(f"Missing required discovery property: {name}")
        hostname = str(properties["hostname"])
        server = decode_zeroconf_hostname(info)
        addresses = tuple(info.parsed_scoped_addresses())
        return cls(
            hostname=hostname,
            system_name=properties["system_name"],
            watchdog_port=_port(properties["watchdog_port"], "watchdog_port"),
            autobahn_port=_port(properties["autobahn_port"], "autobahn_port"),
            ssh_port=_port(properties["ssh_port"], "ssh_port"),
            watchdog_host=properties.get("watchdog_host"),
            autobahn_host=properties.get("autobahn_host"),
            ssh_host=properties.get("ssh_host"),
            addresses=addresses,
            aliases=(server,),
        )


def endpoints_at_addresses(addresses: Sequence[str]) -> set[DiscoveredEndpoint]:
    endpoints: set[DiscoveredEndpoint] = set()
    for address in addresses:
        if "://" in address:
            raise ValueError(f"Use HOST:PORT for --device, without a URL scheme: {address}")
        parsed = urlsplit(f"//{address}")
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError(f"Invalid --device address: {address}") from error
        if not parsed.hostname or port is None or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError(f"Use HOST:PORT for --device: {address}")
        endpoints.add(DiscoveredEndpoint(hostname=parsed.hostname, watchdog_port=_port(port, "watchdog_port")))
    return endpoints


def _fetch_catalog(endpoint: DiscoveredEndpoint) -> DiscoveredNetworkSystem:
    try:
        # A cold catalog can run SMI plus a driver-API fallback, each bounded
        # to three seconds. Allow that collection to finish on the first call.
        response = requests.get(f"http://{endpoint.authority}/get/system/catalog", timeout=10, allow_redirects=False)
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Catalog endpoint must return HTTP 200 without redirects")
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise ValueError(f"Could not collect watchdog catalog at {endpoint.authority}: {error}") from error
    if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int or payload.get("schema_version") != CATALOG_SCHEMA_VERSION or not isinstance(payload.get("system"), dict):
        raise ValueError(f"Incompatible watchdog catalog at {endpoint.authority}; expected schema_version={CATALOG_SCHEMA_VERSION}. Upgrade watchdog and deployer together.")
    profile = payload["system"]
    try:
        # Require the complete catalog, including explicit capability results.
        required = ("hostname", "system_name", "blitz_path", "machine_architecture", "platform_description", "capabilities_json", "python_major_version", "python_minor_version", "watchdog_port", "autobahn_port", "ssh_port")
        for name in required:
            if name not in profile or profile[name] is None:
                raise ValueError(f"Missing required catalog field: {name}")
        for name in ("hostname", "system_name", "blitz_path", "machine_architecture", "platform_description"):
            if not isinstance(profile[name], str) or not profile[name].strip():
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("python_major_version", "python_minor_version"):
            if type(profile[name]) is not int or profile[name] < 0:
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("watchdog_port", "autobahn_port", "ssh_port"):
            profile[name] = _port(profile[name], name)
        for name in ("hostname", "watchdog_host", "autobahn_host", "ssh_host"):
            host = profile.get(name)
            if host is not None and (not isinstance(host, str) or not host.strip() or (any(character in host for character in "/\\?#@[]") or any(character.isspace() for character in host))):
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("os_distribution_id", "os_distribution_family", "os_distribution_version_id"):
            value = profile.get(name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Invalid catalog field: {name}")
        capabilities = json.loads(profile["capabilities_json"])
        if not isinstance(capabilities, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in capabilities.items()):
            raise ValueError("Invalid capabilities_json")
        properties = {key: str(value) if value is not None else None for key, value in profile.items()}
        system = DiscoveredNetworkSystem.from_zeroconf_properties(properties)
        if endpoint.system_name is not None:
            if system.system_name != endpoint.system_name or canonical_host(system.hostname) != canonical_host(endpoint.hostname):
                raise ValueError("Catalog identity differs from mDNS announcement")
            for name in ("watchdog_port", "autobahn_port", "ssh_port"):
                if getattr(system, name) != getattr(endpoint, name):
                    raise ValueError(f"Catalog {name} differs from mDNS announcement")
            for name in ("watchdog_host", "autobahn_host", "ssh_host"):
                host = getattr(endpoint, name)
                catalog_host = getattr(system, name)
                if host and (not catalog_host or canonical_host(host) != canonical_host(catalog_host)):
                    raise ValueError(f"Catalog {name} differs from mDNS announcement")
        # The endpoint we contacted stays authoritative for watchdog requests;
        # a catalog cannot silently redirect deployment to another watchdog.
        system.watchdog_host = endpoint.contact_host
        system.watchdog_port = endpoint.watchdog_port
        if not system.ssh_host or canonical_host(system.ssh_host) == canonical_host(system.hostname):
            system.ssh_host = endpoint.contact_host
        if not system.autobahn_host or canonical_host(system.autobahn_host) == canonical_host(system.hostname):
            system.autobahn_host = endpoint.contact_host
        # Validate build compatibility now, before any build/transfer starts.
        system.to_system_id()
        return system
    except (TypeError, ValueError, KeyError) as error:
        raise ValueError(f"Invalid watchdog catalog at {endpoint.authority}: {error}") from error


def collect_system_catalogs(
    endpoints: Sequence[DiscoveredEndpoint], blacklist: Sequence[str] = (),
    expected_count: int | None = None,
) -> set[DiscoveredNetworkSystem]:
    """Filter the whole fleet, then collect one complete catalog per endpoint."""
    selected = {(_connection_host_key(endpoint.contact_host), endpoint.watchdog_port): endpoint for endpoint in endpoints if not endpoint.is_blacklisted(blacklist)}
    validate_fleet_count(len(selected), expected_count, ())
    if not selected:
        return set()
    with ThreadPoolExecutor(max_workers=min(16, len(selected))) as executor:
        futures = [executor.submit(_fetch_catalog, endpoint) for endpoint in selected.values()]
        systems = []
        errors = []
        for future in futures:
            try:
                systems.append(future.result())
            except Exception as error:
                errors.append(str(error))
    if errors:
        raise ValueError("Device catalog collection failed; no deployment will proceed:\n" + "\n".join(errors))
    return set(systems)


def _pinned_endpoints_with_blacklist(
    addresses: Sequence[str], blacklist: Sequence[str]
) -> set[DiscoveredEndpoint]:
    """Resolve hostname seeds only when needed to enforce an IP exclusion."""
    endpoints = endpoints_at_addresses(addresses)
    ip_exclusions: set[str] = set()
    for value in blacklist:
        normalized = canonical_host(value)
        try:
            ipaddress.ip_address(normalized)
        except ValueError:
            continue
        ip_exclusions.add(normalized)

    selected: set[DiscoveredEndpoint] = set()
    resolved_hosts: dict[str, tuple[str, ...]] = {}
    for endpoint in endpoints:
        if endpoint.is_blacklisted(blacklist):
            continue
        if ip_exclusions:
            try:
                ipaddress.ip_address(endpoint.hostname)
            except ValueError:
                hostname = _connection_host_key(endpoint.hostname)
                if hostname not in resolved_hosts:
                    try:
                        records = socket.getaddrinfo(
                            endpoint.hostname, endpoint.watchdog_port,
                            type=socket.SOCK_STREAM,
                        )
                        resolved = tuple({record[4][0] for record in records})
                        if not resolved:
                            raise OSError("hostname resolved to no addresses")
                    except OSError as error:
                        raise ValueError(
                            f"Cannot enforce IP blacklist for pinned watchdog "
                            f"{endpoint.authority}: hostname resolution failed: {error}. "
                            "No device catalogs were requested."
                        ) from error
                    resolved_hosts[hostname] = resolved
                # DNS addresses are exclusion aliases, not replacements for the
                # user's chosen connection hostname or persistent destinations.
                endpoint = replace(
                    endpoint, aliases=endpoint.aliases + resolved_hosts[hostname]
                )
                if endpoint.is_blacklisted(blacklist):
                    continue
        selected.add(endpoint)
    return selected


def discover_at_addresses(
    addresses: Sequence[str], blacklist: Sequence[str] = (), expected_count: int | None = None,
) -> set[DiscoveredNetworkSystem]:
    endpoints = _pinned_endpoints_with_blacklist(addresses, blacklist)
    return collect_system_catalogs(tuple(endpoints), blacklist, expected_count)


def discover_endpoints_on_network(timeout_seconds: float = 5.0, blacklist: Sequence[str] = ()) -> set[DiscoveredEndpoint]:
    discovered: dict[str, DiscoveredEndpoint] = {}
    errors: dict[str, str] = {}
    lock = threading.Lock()
    zc = Zeroconf()

    class _Listener(ServiceListener):
        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info is None:
                return
            try:
                # Address/server records can filter a malformed TXT payload too.
                candidate = DiscoveredEndpoint(
                    hostname=info.server or "",
                    watchdog_port=info.port or 1,
                    addresses=tuple(info.parsed_scoped_addresses()),
                )
                if candidate.is_blacklisted(blacklist):
                    with lock:
                        discovered.pop(name, None)
                        errors.pop(name, None)
                    return
                properties = decode_zeroconf_properties(info.properties)
                candidate = DiscoveredEndpoint(
                    hostname=properties.get("hostname") or (info.server or ""),
                    watchdog_port=info.port or 1,
                    watchdog_host=properties.get("watchdog_host"),
                    addresses=candidate.addresses,
                    aliases=(info.server or "",),
                )
                if candidate.is_blacklisted(blacklist):
                    with lock:
                        discovered.pop(name, None)
                        errors.pop(name, None)
                    return
                endpoint = DiscoveredEndpoint.from_service_info(info)
                with lock:
                    discovered[name] = endpoint
                    errors.pop(name, None)
            except Exception as error:
                with lock:
                    errors[name] = str(error)

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            self.add_service(zc, type_, name)

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            with lock:
                discovered.pop(name, None)
                errors.pop(name, None)

    try:
        browser = ServiceBrowser(zc, SERVICE, listener=_Listener())
        time.sleep(timeout_seconds)
        browser.cancel()
    finally:
        zc.close()
    if errors:
        raise ValueError("Invalid watchdog discovery announcements; no deployment will proceed: " + str(errors))
    return set(discovered.values())


def discover_all_on_network(
    timeout_seconds: float = 5.0, blacklist: Sequence[str] = (), expected_count: int | None = None,
) -> set[DiscoveredNetworkSystem]:
    endpoints = discover_endpoints_on_network(timeout_seconds, blacklist)
    return collect_system_catalogs(tuple(endpoints), blacklist, expected_count)
