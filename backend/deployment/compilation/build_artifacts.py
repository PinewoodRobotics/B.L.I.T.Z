"""Export declared artifacts and validate each process's native dependency closure.

Runs inside the compilation container. This never downloads dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import zipfile

def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


ROOT = Path('/artifacts')
LIBRARY_SUFFIXES = ('.so', '.a', '.rlib', '.dylib', '.dll', '.lib')


def is_library(path: Path) -> bool:
    return any(path.name.endswith(suffix) for suffix in LIBRARY_SUFFIXES) or '.so.' in path.name


def checked_matches(root: Path, pattern: str) -> list[Path]:
    relative = Path(pattern)
    if relative.is_absolute() or '..' in relative.parts or not pattern:
        raise ValueError(f'Unsafe artifact pattern: {pattern}')
    matches = [path for path in root.glob(pattern) if path.is_file()]
    if not matches:
        raise ValueError(f'Declared output missing: {root}/{pattern}')
    for path in matches:
        if not inside(path, root):
            raise ValueError(f'Artifact escapes module: {path}')
    return matches


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def copy_unique(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        return
    if destination.exists() and file_digest(destination) != file_digest(source):
        raise ValueError(f'Conflicting exported artifact: {destination}')
    shutil.copy2(source, destination)


def build_environment(step: dict[str, Any]) -> dict[str, str]:
    def directories(category: str) -> list[Path]:
        roots = [ROOT / category / name for name in step.get('dependencies', ())]
        return list(dict.fromkeys([*roots, *(path for root in roots for path in root.rglob('*') if path.is_dir())]))
    libraries = directories('lib')
    validate_collisions(libraries, step['module'])
    return {
        'libraries': os.pathsep.join(str(path) for path in libraries),
        'headers': os.pathsep.join(str(path) for path in directories('include')),
    }


def validate_toolkit(step: dict[str, Any], plan: dict[str, Any]) -> None:
    for requirement in step.get('target_capabilities', ()):
        if requirement['name'] != 'cuda':
            continue
        import re
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            raise ValueError(f"Module {step['module']} requires CUDA compilation, but the cached image has no usable nvcc. Configure CUDA provisioning and cache dependencies online.") from error
        match = re.search(r'release (\d+\.\d+)', result.stdout)
        if not match:
            raise ValueError('Cannot determine cached CUDA toolkit version')
        def version(value: str) -> tuple[int, ...]:
            parts = tuple(int(part) for part in value.split('.'))
            return parts + (0,) * (3 - len(parts))
        actual = version(match.group(1))
        minimum = requirement.get('minimum_version')
        supported = dict(plan['system'].get('capabilities', {})).get('cuda')
        if minimum and actual < version(minimum):
            raise ValueError(f"Cached CUDA toolkit {match.group(1)} is below required {minimum} for {step['module']}")
        if not supported or actual > version(supported):
            raise ValueError(f"CUDA toolkit {match.group(1)} exceeds target driver support {supported}")


def export(step: dict[str, Any]) -> None:
    name, language = step['module'], step['language']
    artifacts = ROOT / language / name
    source = Path(step['source'])
    outputs = step.get('outputs') or {}
    libraries = outputs.get('libraries') or ()
    paths = [path for pattern in libraries for path in checked_matches(artifacts, pattern)] if libraries else [path for path in artifacts.rglob('*') if path.is_file() and is_library(path)]
    for path in paths:
        copy_unique(path, ROOT / 'lib' / name / path.relative_to(artifacts))
    for category in ('headers', 'resources'):
        for pattern in outputs.get(category, ()):
            for path in checked_matches(source, pattern):
                copy_unique(path, ROOT / ('include' if category == 'headers' else 'resources') / name / path.relative_to(source))
                if category == 'resources':
                    copy_unique(path, artifacts / path.relative_to(source))
    for pattern in outputs.get('executables', ()):
        for path in checked_matches(artifacts, pattern):
            if not os.access(path, os.X_OK):
                raise ValueError(f'Declared executable is not executable: {path}')
    if step.get('binary'):
        paths = checked_matches(artifacts, step['binary'])
        if len(paths) != 1 or not os.access(paths[0], os.X_OK):
            raise ValueError(f'Invalid native entrypoint: {step["binary"]}')
    if step.get('entry_file'):
        checked_matches(artifacts, step['entry_file'])
    if step.get('entry_package'):
        package = artifacts.joinpath(*step['entry_package'].split('.'))
        if not package.with_suffix('.py').is_file() and not (package / '__main__.py').is_file():
            raise ValueError(f'Runnable Python package missing: {package}')
    (ROOT / 'lib' / name).mkdir(parents=True, exist_ok=True)
    (ROOT / 'resources' / name).mkdir(parents=True, exist_ok=True)


def validate_collisions(paths: list[Path], module: str) -> None:
    names: dict[str, tuple[str, Path]] = {}
    for directory in paths:
        for path in (directory.glob('*') if directory == ROOT / 'deps' / 'native' else directory.rglob('*')):
            if not path.is_file() or not is_library(path):
                continue
            digest = file_digest(path)
            keys = [path.name]
            with path.open('rb') as stream:
                elf = stream.read(4) == b'\x7fELF'
            if elf:
                import re
                metadata = subprocess.run(['readelf', '-d', str(path)], capture_output=True, text=True)
                soname = re.search(r'\(SONAME\).*\[(.*?)\]', metadata.stdout)
                if soname:
                    keys.append(soname.group(1))
            for key in keys:
                if key in names and names[key][0] != digest:
                    raise ValueError(f'Conflicting library {key} in dependency closure of {module}: {names[key][1]} and {path}')
                names[key] = digest, path


def collect_native(files: list[Path], paths: list[Path], destination: Path, cuda_supported: bool = False) -> None:
    environment = os.environ.copy()
    environment['LD_LIBRARY_PATH'] = os.pathsep.join(str(path) for path in [*paths, destination])
    pending = list(files)
    visited: set[Path] = set()
    while pending:
        artifact = pending.pop()
        if artifact.resolve() in visited:
            continue
        visited.add(artifact.resolve())
        with artifact.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        result = subprocess.run(['ldd', str(artifact)], capture_output=True, text=True, env=environment)
        output = result.stdout + result.stderr
        if 'statically linked' in output or 'not a dynamic executable' in output:
            continue
        if result.returncode:
            raise ValueError(f'Cannot inspect {artifact}: {output.strip()}')
        for line in output.splitlines():
            tokens = line.split()
            if len(tokens) < 3 or tokens[1] != '=>':
                continue
            soname, _, location = tokens[:3]
            if soname.startswith(('libcuda.so.', 'libnvidia-')) and cuda_supported:
                continue
            if location == 'not':
                raise ValueError(f'Unresolved native library {soname} required by {artifact}')
            if soname.startswith(('libc.so.', 'libm.so.', 'libpthread.so.', 'libdl.so.', 'librt.so.', 'ld-linux')):
                continue  # libc and hardware drivers belong to the target.
            dependency = Path(location)
            if not dependency.is_absolute():
                continue
            if not inside(dependency, ROOT / 'lib'):
                copy_unique(dependency, destination / soname)
            pending.append(dependency)


def finalize(plan: dict[str, Any]) -> None:
    steps = [step for step in plan['steps'] if step['kind'] in ('cpp-build', 'rust-build', 'copy-module')]
    wheel_root = Path('/tmp/blitz-wheel-native')
    for wheel in (ROOT / 'deps' / 'python').glob('*.whl'):
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                if '.so' not in Path(member).name:
                    continue
                relative = Path(member)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError(f'Unsafe wheel member: {member}')
                destination = wheel_root / wheel.stem / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
    cuda_supported = 'cuda' in plan['system'].get('capabilities', {})
    collect_native([path for path in wheel_root.rglob('*') if path.is_file()], [], ROOT / 'deps' / 'native', cuda_supported)
    manifest: dict = {'modules': {}, 'system': plan['system']}
    by_name = {step['module']: step for step in steps}
    for step in steps:
        name = step['module']
        closure = [name, *step.get('dependencies', ())]
        paths = [ROOT / 'lib' / dependency for dependency in closure]
        # Nested outputs are permitted; include each directory containing a library.
        paths = list(dict.fromkeys([*paths, *(p.parent for root in paths for p in root.rglob('*') if p.is_file() and is_library(p))]))
        validate_collisions(paths, name)
        files = [path for path in (ROOT / step['language'] / name).rglob('*') if path.is_file()]
        collect_native(files, paths, ROOT / 'deps' / 'native' / name, cuda_supported)
        paths += [ROOT / 'deps' / 'native' / dependency for dependency in closure]
        validate_collisions([*paths, ROOT / 'deps' / 'native'], name)
        manifest['modules'][name] = {
            'dependencies': step.get('dependencies', []),
            'module_paths': [f"{by_name[dependency]['language']}/{dependency}" for dependency in closure],
            'library_paths': [str(path.relative_to(ROOT)) for path in paths],
            'resources': f'resources/{name}',
        }
    (ROOT / 'runtime-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'build-environment':
            print(json.dumps(build_environment(json.loads(sys.argv[2]))))
        elif sys.argv[1] == 'validate-toolkit':
            validate_toolkit(json.loads(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text()))
        elif sys.argv[1] == 'export':
            export(json.loads(sys.argv[2]))
        else:
            finalize(json.loads(Path(sys.argv[2]).read_text()))
    except Exception as error:
        print(f'[blitz] Artifact validation failed: {error}', file=sys.stderr)
        raise
