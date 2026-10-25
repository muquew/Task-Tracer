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

from validate_static import app_version

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2025, 1, 1, 0, 0, 0)
DISTRIBUTION_SOURCES = {
    'index.html': 'index.html',
    'sw.js': 'sw.js',
    'manifest.json': 'manifest.json',
    'robots.txt': 'robots.txt',
    'sitemap.xml': 'sitemap.xml',
    'vercel.json': 'vercel.json',
    'LICENSE': 'LICENSE',
    'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'README.md': 'docs/distribution.md',
    'README_zh_cn.md': 'docs/distribution_zh_cn.md',
    'fav/android-chrome-192x192.png': 'fav/android-chrome-192x192.png',
    'fav/android-chrome-512x512.png': 'fav/android-chrome-512x512.png',
    'fav/apple-touch-icon.png': 'fav/apple-touch-icon.png',
    'fav/favicon-16x16.png': 'fav/favicon-16x16.png',
    'fav/favicon-32x32.png': 'fav/favicon-32x32.png',
    'fav/favicon-48x48.png': 'fav/favicon-48x48.png',
    'fav/favicon.ico': 'fav/favicon.ico',
    'resources/en.json': 'resources/en.json',
    'resources/zh-CN.json': 'resources/zh-CN.json',
    'screenshots/add-task-en.png': 'screenshots/add-task-en.png',
    'screenshots/add-task.png': 'screenshots/add-task.png',
    'screenshots/task-list-en.png': 'screenshots/task-list-en.png',
    'screenshots/task-list.png': 'screenshots/task-list.png',
}


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


def expected_distribution_files() -> frozenset[str]:
    for name in DISTRIBUTION_SOURCES:
        relative_distribution_path(name, 'target')
        if name == 'integrity.json':
            raise AssertionError('integrity.json is reserved for generated metadata')
    return frozenset(DISTRIBUTION_SOURCES) | {'integrity.json'}


def build(output_dir: Path) -> Path:
    expected = expected_distribution_files()
    for name in DISTRIBUTION_SOURCES.values():
        validated_source(ROOT, name)
    for tool in ('validate_static.py', 'security_policy.py'):
        subprocess.run([sys.executable, str(ROOT / 'tools' / tool)], check=True, cwd=ROOT)
    payload: dict[str, bytes] = {}
    for target, source in sorted(DISTRIBUTION_SOURCES.items()):
        data = validated_source(ROOT, source).read_bytes()
        if target in ('README.md', 'README_zh_cn.md'):
            data = data.replace(b'](../LICENSE)', b'](LICENSE)')
        payload[target] = data
    version = app_version(payload['index.html'].decode('utf-8'))
    manifest = {'app': 'Task Tracer', 'version': version,
                'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
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
