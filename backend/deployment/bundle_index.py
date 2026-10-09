"""Checksums for bundles prepared while online and used while offline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


INDEX_VERSION = 1


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_bundle_index(path: Path, bundles: dict[str, Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": INDEX_VERSION,
        "bundles": {key: file_digest(bundle) for key, bundle in sorted(bundles.items())},
    }
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def verify_bundles(path: Path, bundles: dict[str, Path]) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Bundle index not found: {path}. Run build first.")
    payload = json.loads(path.read_text())
    if payload.get("version") != INDEX_VERSION or not isinstance(payload.get("bundles"), dict):
        raise ValueError(f"Unsupported bundle index: {path}")
    for key, bundle in bundles.items():
        expected = payload["bundles"].get(key)
        if not bundle.is_file() or expected is None or file_digest(bundle) != expected:
            raise ValueError(f"Missing or changed bundle for {key}: {bundle}. Run build again.")
