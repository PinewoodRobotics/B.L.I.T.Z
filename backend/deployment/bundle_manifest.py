"""Content manifests that let redeployments transfer only changed bundle files.

Every bundle archive carries ``bundle-manifest.json``: the SHA-256 and mode of
each file plus the directory list. A successful install leaves that manifest at
``backend/bundle-manifest.json`` on the target, so the next deployment can
compare it with the new bundle and send a delta archive instead of the whole
bundle (mostly unchanged Python wheels and native libraries).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, ZipInfo


MANIFEST_NAME = "bundle-manifest.json"
MANIFEST_VERSION = 1
DELTA_FOLDER = ".blitz-delta"
DEPENDENCIES_PREFIX = "deps/"
# Install never writes these into backend/, so they are not tracked content.
_UNTRACKED_ROOT_FILES = frozenset({"__init__.py", MANIFEST_NAME})


@dataclass(frozen=True)
class FileEntry:
    sha256: str
    mode: int
    size: int


@dataclass(frozen=True)
class BundleManifest:
    system: str
    files: Mapping[str, FileEntry]
    directories: frozenset[str]

    def to_json(self) -> str:
        payload = {
            "version": MANIFEST_VERSION,
            "system": self.system,
            "directories": sorted(self.directories),
            "files": {
                path: {"sha256": entry.sha256, "mode": entry.mode, "size": entry.size}
                for path, entry in sorted(self.files.items())
            },
        }
        return json.dumps(payload, indent=1, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str) -> BundleManifest | None:
        """Parse a manifest, or return None for anything that cannot be trusted."""
        try:
            payload = json.loads(text)
            if payload["version"] != MANIFEST_VERSION or not isinstance(payload["system"], str):
                return None
            files = {
                _checked_path(path): FileEntry(str(entry["sha256"]), int(entry["mode"]), int(entry["size"]))
                for path, entry in payload["files"].items()
            }
            directories = frozenset(_checked_path(path) for path in payload["directories"])
        except (ValueError, KeyError, TypeError, AttributeError):
            return None
        return cls(payload["system"], files, directories)

    def dependency_digest(self) -> str:
        """Identify the bundled dependency set, independent of project sources."""
        digest = hashlib.sha256(self.system.encode())
        for path, entry in sorted(self.files.items()):
            if path.startswith(DEPENDENCIES_PREFIX):
                digest.update(f"\0{path}\0{entry.sha256}".encode())
        return digest.hexdigest()


@dataclass(frozen=True)
class BundleDelta:
    changed: tuple[str, ...]
    removed: tuple[str, ...]
    removed_directories: tuple[str, ...]

    @property
    def empty(self) -> bool:
        return not (self.changed or self.removed or self.removed_directories)


def _checked_path(path: object) -> str:
    """Accept only plain relative paths, because removals run on the target."""
    if not isinstance(path, str) or not path or "\0" in path or "\\" in path:
        raise ValueError(f"Invalid bundle path: {path!r}")
    parts = PurePosixPath(path).parts
    if path.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Invalid bundle path: {path!r}")
    return path


def _relative(info: ZipInfo, root: str) -> str | None:
    if not info.filename.startswith(root):
        raise ValueError(f"Bundle member outside {root}: {info.filename}")
    path = info.filename[len(root):].rstrip("/")
    return path or None


def manifest_for_archive(archive_path: Path, system_key: str) -> BundleManifest:
    root = f"{system_key}/"
    files: dict[str, FileEntry] = {}
    directories: set[str] = set()
    with ZipFile(archive_path) as archive:
        for info in archive.infolist():
            path = _relative(info, root)
            if path is None:
                continue
            _checked_path(path)
            if info.is_dir():
                directories.add(path)
                continue
            if path in _UNTRACKED_ROOT_FILES:
                continue
            digest = hashlib.sha256()
            with archive.open(info) as member:
                for block in iter(lambda: member.read(1024 * 1024), b""):
                    digest.update(block)
            files[path] = FileEntry(digest.hexdigest(), (info.external_attr >> 16) & 0o7777, info.file_size)
    return BundleManifest(system_key, files, frozenset(directories))


def add_manifest(archive_path: Path, system_key: str) -> BundleManifest:
    """Record the archive's contents inside it, so its checksum covers the manifest."""
    manifest = manifest_for_archive(archive_path, system_key)
    with ZipFile(archive_path, "a") as archive:
        archive.writestr(f"{system_key}/{MANIFEST_NAME}", manifest.to_json())
    return manifest


def read_manifest(archive_path: Path, system_key: str) -> BundleManifest | None:
    """Return an archive's manifest; bundles from older BLITZ versions have none."""
    try:
        with ZipFile(archive_path) as archive:
            text = archive.read(f"{system_key}/{MANIFEST_NAME}").decode()
    except (KeyError, BadZipFile, OSError, UnicodeDecodeError):
        # Transfer the archive as-is; installation reports any damage.
        return None
    return BundleManifest.from_json(text)


def compare(installed: BundleManifest, bundle: BundleManifest) -> BundleDelta:
    changed = tuple(sorted(
        path for path, entry in bundle.files.items() if installed.files.get(path) != entry
    ))
    removed = tuple(sorted(set(installed.files) - set(bundle.files)))
    removed_directories = tuple(sorted(installed.directories - bundle.directories))
    return BundleDelta(changed, removed, removed_directories)


def write_delta_archive(
    archive_path: Path,
    destination: Path,
    system_key: str,
    delta: BundleDelta,
    installed_manifest_text: str,
) -> int:
    """Write the changed files, removal lists, and both manifests; return payload bytes.

    The installed manifest travels with the delta so the target can confirm it
    is still in that exact state before applying any change.
    """
    root = f"{system_key}/"
    changed = set(delta.changed)
    payload_bytes = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as source, ZipFile(destination, "w") as target:
        for info in source.infolist():
            path = _relative(info, root)
            if path is None or info.is_dir():
                # Directory entries are tiny and keep new empty folders.
                target.writestr(info, b"")
            elif path in changed or path == MANIFEST_NAME:
                target.writestr(info, source.read(info))
                payload_bytes += info.file_size if path in changed else 0
        delta_root = f"{root}{DELTA_FOLDER}/"
        target.writestr(f"{delta_root}base-manifest.json", installed_manifest_text)
        target.writestr(f"{delta_root}removed", "".join(f"{path}\0" for path in delta.removed))
        target.writestr(
            f"{delta_root}removed-directories",
            "".join(f"{path}\0" for path in delta.removed_directories),
        )
    return payload_bytes
