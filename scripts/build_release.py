#!/usr/bin/env python3
"""Build a deterministic static distribution with an integrity manifest; never publish it."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

from .validate_static import app_version
from .project_layout import distribution_sources

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2025, 1, 1, 0, 0, 0)
DISTRIBUTION_SOURCES = distribution_sources()


def relative_distribution_path(name: str, label: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or any(character in name for character in ('\\', '\x00', ':')):
        raise AssertionError(f'Unsafe distribution {label}: {name!r}')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != name or name == '.':
        raise AssertionError(f'Unsafe distribution {label}: {name!r}')
    return path


def validated_source(root: Path, name: str) -> Path:
    relative = relative_distribution_path(name, 'source')
    anchor = root.resolve(strict=True)
    path = anchor
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise AssertionError(f'Unsafe distribution source: {name!r} is a symbolic link')
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise AssertionError(f'Missing required distribution source: {name}') from error
    if not resolved.is_relative_to(anchor) or not resolved.is_file():
        raise AssertionError(f'Unsafe distribution source: {name!r}')
    return resolved


def expected_distribution_files(root: Path | None = None) -> frozenset[str]:
    sources = distribution_sources(ROOT if root is None else root)
    for name in sources:
        relative_distribution_path(name, 'target')
        if name == 'integrity.json':
            raise AssertionError('integrity.json is reserved for generated metadata')
    return frozenset(sources) | {'integrity.json'}


def build(output_dir: Path, *, root: Path | None = None) -> Path:
    base = ROOT if root is None else Path(root)
    sources = distribution_sources(base)
    expected = expected_distribution_files(base)
    for name in sources.values():
        validated_source(base, name)
    for tool in ('validate_static.py', 'security_policy.py'):
        subprocess.run([sys.executable, '-m', 'scripts.' + tool[:-3]], check=True, cwd=base)
    payload: dict[str, bytes] = {}
    for target, source in sorted(sources.items()):
        data = validated_source(base, source).read_bytes()
        payload[target] = data
    version = app_version(payload['index.html'].decode('utf-8'))
    manifest = {'app': 'Task Tracer', 'version': version,
                'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=base, text=True).strip(),
                'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=base, text=True).strip()),
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())}}
    payload['integrity.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f'task-tracer-{version}.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{digest}  {target.name}\n')
    with zipfile.ZipFile(target) as archive:
        for name, expected_digest in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected_digest:
                raise AssertionError(f'Distribution integrity mismatch: {name}')
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
            raise AssertionError('Unexpected files in distribution')
    print(f'Built and verified {target} ({len(payload)} files, SHA-256 {digest})')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().output_dir)
