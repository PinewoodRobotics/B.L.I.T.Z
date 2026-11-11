"""Redeployments send only changed files and skip unchanged dependencies."""
from pathlib import Path
import json
import shutil

import pytest

from __tests__.rsyncer_retention_tests import LocalTarget, target
from backend.deployment.bundle_manifest import (
    MANIFEST_NAME,
    BundleManifest,
    add_manifest,
    compare,
    read_manifest,
)
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.rsyncer import Rsyncer


WHEEL = "deps/python/numpy-2.4.6-cp311-cp311-manylinux_2_28_aarch64.whl"


def bundle(output: Path, system: LocalTarget, files: dict[str, str]) -> BundleManifest:
    """Archive a bundle tree exactly as CodeBundler does, directory entries included."""
    key = system.general_info.to_system_id().to_build_key()
    tree = output / "tree"
    shutil.rmtree(tree, ignore_errors=True)
    for name, contents in files.items():
        (tree / key / name).parent.mkdir(parents=True, exist_ok=True)
        (tree / key / name).write_text(contents)
    output.mkdir(exist_ok=True)
    archive = Path(shutil.make_archive(str(output / key), "zip", root_dir=tree, base_dir=key))
    shutil.rmtree(tree)
    return add_manifest(archive, key)


def backend(system: LocalTarget) -> Path:
    return Path(system.general_info.blitz_path) / "backend"


def transferred(system: LocalTarget) -> set[str]:
    """Files (not directories or delta metadata) in the most recent transfer."""
    return {
        name.split("/", 1)[1] for name in system.transfers[-1]
        if not name.endswith("/") and "/.blitz-delta/" not in name
    } - {MANIFEST_NAME}


@pytest.fixture
def deployment(tmp_path: Path) -> tuple[LocalTarget, Path, Rsyncer]:
    system = target(tmp_path / "target with spaces")
    output = tmp_path / "outputs"
    return system, output, Rsyncer([], FolderPath(str(output)), FolderPath("bundles"), {system})


def test_manifest_records_contents_and_survives_round_trip(tmp_path: Path) -> None:
    system = target(tmp_path / "target")
    manifest = bundle(tmp_path / "outputs", system, {"python/app/main.py": "print(1)", "__init__.py": ""})
    archive = next((tmp_path / "outputs").glob("*.zip"))
    assert read_manifest(archive, archive.stem) == manifest
    assert set(manifest.files) == {"python/app/main.py"}
    assert BundleManifest.from_json(manifest.to_json()) == manifest


@pytest.mark.parametrize("path", ["../escape", "/etc/passwd", "python/../../escape", "a\\b", ""])
def test_untrusted_manifest_paths_are_rejected(path: str) -> None:
    manifest = {"version": 1, "system": "key", "directories": [],
                "files": {path: {"sha256": "0", "mode": 420, "size": 1}}}
    assert BundleManifest.from_json(json.dumps(manifest)) is None


def test_redeploy_transfers_only_changed_files(deployment) -> None:
    system, output, sync = deployment
    bundle(output, system, {
        "python/app/main.py": "v1", "python/app/old.py": "old",
        "resources/old/data.txt": "old resource", WHEEL: "wheel bytes", "deploy.py": "declarations",
    })
    sync.deploy()
    assert transferred(system) == {"python/app/main.py", "python/app/old.py",
                                   "resources/old/data.txt", WHEEL, "deploy.py"}
    installed = backend(system) / MANIFEST_NAME
    assert installed.is_file()

    new = bundle(output, system, {
        "python/app/main.py": "v2", "python/app/new.py": "new",
        WHEEL: "wheel bytes", "deploy.py": "declarations",
    })
    sync.deploy()
    assert transferred(system) == {"python/app/main.py", "python/app/new.py"}
    assert (backend(system) / "python/app/main.py").read_text() == "v2"
    assert (backend(system) / "python/app/new.py").read_text() == "new"
    assert (backend(system) / WHEEL).read_text() == "wheel bytes"
    assert not (backend(system) / "python/app/old.py").exists()
    assert not (backend(system) / "resources/old").exists()
    assert BundleManifest.from_json(installed.read_text()) == new
    assert not list((Path(system.general_info.blitz_path) / "bundles").iterdir())
    assert not list((output / "incremental").iterdir())


@pytest.mark.parametrize("changed", [False, True])
def test_redeploy_clears_runtime_bytecode_like_a_complete_install(deployment, changed: bool) -> None:
    system, output, sync = deployment
    bundle(output, system, {"python/app/main.py": "v1", "python/app/util.py": "u"})
    sync.deploy()
    cache = backend(system) / "python/app/__pycache__"
    cache.mkdir()
    (cache / "main.cpython-311.pyc").write_bytes(b"stale")
    if changed:
        bundle(output, system, {"python/app/main.py": "v2", "python/app/util.py": "u"})
    sync.deploy()
    assert len(system.transfers) == (2 if changed else 1)
    assert not cache.exists()
    assert (backend(system) / "python/app/util.py").exists()


@pytest.mark.parametrize("damage", ["missing", "corrupt", "other-system"])
def test_unusable_installed_manifest_falls_back_to_complete_transfer(deployment, damage: str) -> None:
    system, output, sync = deployment
    bundle(output, system, {"python/app/main.py": "v1", WHEEL: "wheel"})
    sync.deploy()
    installed = backend(system) / MANIFEST_NAME
    if damage == "missing":
        installed.unlink()
    elif damage == "corrupt":
        installed.write_text("{")
    else:
        payload = json.loads(installed.read_text())
        payload["system"] = "another-profile"
        installed.write_text(json.dumps(payload))
    sync.deploy()
    assert transferred(system) == {"python/app/main.py", WHEEL}


def test_target_changed_after_comparison_is_not_modified(deployment, monkeypatch) -> None:
    system, output, sync = deployment
    bundle(output, system, {"python/app/main.py": "v1", "python/app/keep.py": "keep"})
    sync.deploy()
    bundle(output, system, {"python/app/main.py": "v2"})
    original = sync.install_delta

    def concurrent_change(*args) -> None:
        # Another deployment finished between the comparison and installation.
        installed = backend(system) / MANIFEST_NAME
        installed.write_text(installed.read_text() + " ")
        original(*args)

    monkeypatch.setattr(sync, "install_delta", concurrent_change)
    with pytest.raises(RuntimeError, match="Failed to install changed files"):
        sync.deploy()
    assert (backend(system) / "python/app/main.py").read_text() == "v1"
    assert (backend(system) / "python/app/keep.py").exists()


def test_full_transfer_option_sends_everything(tmp_path: Path) -> None:
    system = target(tmp_path / "target")
    output = tmp_path / "outputs"
    sync = Rsyncer([], FolderPath(str(output)), FolderPath("bundles"), {system}, incremental=False)
    bundle(output, system, {"python/app/main.py": "v1", WHEEL: "wheel"})
    sync.deploy()
    sync.deploy()
    assert transferred(system) == {"python/app/main.py", WHEEL}


def test_dependencies_install_only_when_bundled_dependencies_change(tmp_path: Path, monkeypatch) -> None:
    system = target(tmp_path / "target")
    (Path(system.general_info.blitz_path) / ".venv").mkdir(parents=True)
    output = tmp_path / "outputs"
    sync = Rsyncer([], FolderPath(str(output)), FolderPath("bundles"), {system}, are_deps_bundled=True)
    installs: list[str] = []
    monkeypatch.setattr(sync, "install_dependencies", lambda target_system: installs.append("pip"))

    bundle(output, system, {"python/app/main.py": "v1", WHEEL: "wheel v1"})
    sync.deploy()
    bundle(output, system, {"python/app/main.py": "v2", WHEEL: "wheel v1"})
    sync.deploy()
    assert installs == ["pip"]

    bundle(output, system, {"python/app/main.py": "v2", WHEEL: "wheel v2"})
    sync.deploy()
    assert installs == ["pip", "pip"]

    # A recreated virtual environment loses its record and reinstalls.
    marker = Path(system.general_info.blitz_path) / ".venv" / ".blitz-dependencies"
    marker.unlink()
    sync.deploy()
    assert installs == ["pip", "pip", "pip"]


def test_compare_reports_mode_changes_and_removed_directories(tmp_path: Path) -> None:
    system = target(tmp_path / "target")
    old = bundle(tmp_path / "old", system, {"lib/a/liba.so": "a", "lib/b/libb.so": "b"})
    new = bundle(tmp_path / "new", system, {"lib/a/liba.so": "a"})
    delta = compare(old, new)
    assert delta.changed == ()
    assert delta.removed == ("lib/b/libb.so",)
    assert "lib/b" in delta.removed_directories
