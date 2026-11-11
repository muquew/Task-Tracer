#!/usr/bin/env python3
"""Exercise distribution boundaries with real builds in an isolated repository."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
import zipfile

import build_release as release


def assert_archive(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = release.expected_distribution_files()
        assert len(names) == 24 and len(names) == len(expected) and set(names) == expected
        assert 'THIRD_PARTY_NOTICES.md' in names
        assert archive.read('THIRD_PARTY_NOTICES.md') == (release.ROOT / 'THIRD_PARTY_NOTICES.md').read_bytes()
        for name in ('README.md', 'README_zh_cn.md'):
            content = archive.read(name)
            assert content == (release.ROOT / name).read_bytes(), f'{name} differs from the shared project documentation'
            for link in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', content.decode('utf-8')):
                target = urlsplit(link)
                if target.scheme or target.netloc or not target.path:
                    continue
                assert unquote(target.path) in expected, f'{name} links to an unpackaged file: {link}'
        manifest = json.loads(archive.read('integrity.json'))
        assert set(manifest['files']) == expected - {'integrity.json'}
        for name, digest in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.with_suffix('.zip.sha256').read_text() == f'{digest}  {path.name}\n'
    return path.read_bytes()


def rejects(label, operation):
    try:
        operation()
    except AssertionError:
        print(f'Release payload rejection passed: {label}')
    else:
        raise AssertionError(f'Unsafe distribution input was accepted: {label}')


def run() -> None:
    original_root = release.ROOT
    with tempfile.TemporaryDirectory(prefix='task-tracer-release-payload-') as folder:
        base = Path(folder)
        root = base / 'repository'
        root.mkdir()
        for name in set(release.DISTRIBUTION_SOURCES.values()) | {'package.json', 'package-lock.json'}:
            source = release.validated_source(original_root, name)
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (root / 'tools').mkdir()
        for name in ('validate_static.py', 'translation_fallback.py', 'security_policy.py'):
            shutil.copy2(original_root / 'tools' / name, root / 'tools' / name)
        subprocess.run(['git', 'init', '--quiet'], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.name=Synthetic release test', '-c', 'user.email=release-test@example.invalid',
                        '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty', '-m', 'Isolated release fixture'],
                       cwd=root, check=True)
        with patch.object(release, 'ROOT', root):
            normal = assert_archive(release.build(base / 'normal'))
            sentinels = {
                'screenshots/private-task-backup.json': b'{"tasks":[{"name":"SYNTHETIC_PRIVATE_TASK"}]}\n',
                'resources/operator-notes.txt': b'SYNTHETIC_OPERATOR_NOTES\n',
                'fav/.local-token': b'SYNTHETIC_NOT_A_REAL_TOKEN\n',
            }
            for name, data in sentinels.items():
                (root / name).write_bytes(data)
            first = assert_archive(release.build(base / 'with-unrelated-files'))
            second = assert_archive(release.build(base / 'repeat'))
            assert normal == first == second, 'Unrelated files changed the distribution or repeated builds differ'
            print('Release payload passed: three unrelated synthetic files are excluded; exact manifest and repeated bytes match')

            rejected_output = base / 'must-not-be-created'
            required = root / 'fav/favicon-48x48.png'
            content = required.read_bytes()
            required.unlink()
            try:
                rejects('missing required asset', lambda: release.build(rejected_output))
            finally:
                required.write_bytes(content)

            outside = base / 'outside-source.txt'
            outside.write_text('SYNTHETIC_OUTSIDE_SOURCE\n')
            for name in ('index.html', 'README.md', 'README_zh_cn.md'):
                source = root / name
                content = source.read_bytes()
                source.unlink()
                source.symlink_to(outside)
                try:
                    rejects(f'source symbolic link {name}', lambda: release.build(rejected_output))
                finally:
                    source.unlink()
                    source.write_bytes(content)

            icons = root / 'fav'
            moved = base / 'outside-icons'
            icons.rename(moved)
            icons.symlink_to(moved, target_is_directory=True)
            try:
                rejects('source directory symbolic link', lambda: release.build(rejected_output))
            finally:
                icons.unlink()
                moved.rename(icons)

            for name in ('../outside-source.txt', '/outside-source.txt', 'resources/../index.html',
                         'resources\\en.json', 'resources//en.json', '', '.'):
                rejects(f'unsafe source {name!r}', lambda name=name: release.validated_source(root, name))
            for name in ('../outside.txt', '/outside.txt', 'resources\\extra.txt', 'integrity.json'):
                with patch.dict(release.DISTRIBUTION_SOURCES, {name: 'index.html'}):
                    rejects(f'unsafe archive target {name!r}', lambda: release.build(rejected_output))
            assert not rejected_output.exists(), 'Rejected input created release output'
    print('Release payload checks passed')


if __name__ == '__main__':
    run()
