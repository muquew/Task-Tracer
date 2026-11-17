#!/usr/bin/env python3
"""Exercise distribution boundaries with real builds in an isolated repository."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
import zipfile

from scripts import build_release as release
from scripts.project_layout import site_sources
from tests.support.isolated_repo import application_file, copy_release_repository


def assert_archive(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = release.expected_distribution_files(root=release.ROOT)
        assert len(names) == len(expected) and set(names) == expected
        assert archive.read('resources/workspace.css') == application_file(release.ROOT, 'resources/workspace.css').read_bytes()
        assert archive.read('resources/workbench.js') == application_file(release.ROOT, 'resources/workbench.js').read_bytes()
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
    except (AssertionError, ValueError):
        print(f'Release payload rejection passed: {label}')
    else:
        raise AssertionError(f'Unsafe distribution input was accepted: {label}')


def check_site_build(root: Path, base: Path) -> None:
    config_path = root / 'config/site-files.json'
    original_config = config_path.read_bytes()
    configuration = json.loads(original_config)
    download = b'PK\x03\x04SYNTHETIC_DOWNLOAD_BYTES\x00\xff\n'
    downloads = {
        'public/downloads/synthetic.zip': download,
        'public/downloads/synthetic.zip.sha256': (hashlib.sha256(download).hexdigest() + '  synthetic.zip\n').encode(),
    }
    for source, data in downloads.items():
        path = root / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        configuration['downloads'][source] = source.removeprefix('public/')
    config_path.write_text(json.dumps(configuration) + '\n')
    configured = config_path.read_bytes()
    site = root / 'dist/site'

    def build(expected_error: str | None = None) -> None:
        result = subprocess.run(['node', 'scripts/build-site.mjs'], cwd=root, capture_output=True, text=True)
        output = result.stdout + result.stderr
        if expected_error is None:
            assert result.returncode == 0, output
        else:
            assert result.returncode != 0 and expected_error in output, output

    def assert_site() -> None:
        expected = {name: release.validated_source(root, source).read_bytes()
                    for name, source in site_sources(root).items()}
        actual = {path.relative_to(site).as_posix(): path.read_bytes()
                  for path in site.rglob('*') if path.is_file()}
        assert actual == expected, 'Built site differs from the exact configured application/download files'

    def metadata() -> dict:
        return {path.relative_to(site).as_posix(): (path.stat().st_ino, path.stat().st_mtime_ns)
                for path in (site, *site.rglob('*'))}

    def rejected_build(expected_error: str) -> None:
        build(expected_error)
        assert metadata() == stable, 'A rejected site build changed the installed output'

    try:
        build()
        assert_site()
        stable = metadata()
        build()
        assert metadata() == stable, 'An unchanged site build rewrote output files or directories'
        (site / 'stale-unmapped.txt').write_text('SYNTHETIC_STALE_OUTPUT\n')
        build()
        assert_site()
        stable = metadata()

        required = application_file(root, 'resources/workbench.js')
        original = required.read_bytes()
        required.unlink()
        try:
            rejected_build('ENOENT')
        finally:
            required.write_bytes(original)

        outside = base / 'site-outside-source.txt'
        outside.write_bytes(b'SYNTHETIC_OUTSIDE_SITE_SOURCE\n')
        required = application_file(root, 'index.html')
        original = required.read_bytes()
        required.unlink()
        required.symlink_to(outside)
        try:
            rejected_build('Site source is a symlink')
        finally:
            required.unlink()
            required.write_bytes(original)

        icons = application_file(root, 'fav/favicon.ico').parent
        moved_icons = base / 'site-outside-icons'
        icons.rename(moved_icons)
        icons.symlink_to(moved_icons, target_is_directory=True)
        try:
            rejected_build('Site source is a symlink')
        finally:
            icons.unlink()
            moved_icons.rename(icons)

        index_source = release.distribution_sources(root)['index.html']
        for target in ('../outside.html', '/outside.html', 'resources\\outside.js', 'scripts/private.py'):
            changed = json.loads(configured)
            changed['application'][index_source] = target
            config_path.write_text(json.dumps(changed) + '\n')
            try:
                rejected_build('Developer path cannot be published' if target.startswith('scripts/') else 'Unsafe site path')
            finally:
                config_path.write_bytes(configured)
        changed = json.loads(configured)
        changed['application']['../outside-source.txt'] = changed['application'].pop(index_source)
        config_path.write_text(json.dumps(changed) + '\n')
        try:
            rejected_build('Unsafe site path')
        finally:
            config_path.write_bytes(configured)

        dist = root / 'dist'
        moved_dist = base / 'site-outside-dist'
        dist.rename(moved_dist)
        dist.symlink_to(moved_dist, target_is_directory=True)
        try:
            build('Site build directory must be a regular directory')
        finally:
            dist.unlink()
            moved_dist.rename(dist)
        assert metadata() == stable, 'A rejected symlink build changed external output'
        assert_site()
    finally:
        config_path.write_bytes(original_config)
    print('Site build passed: exact application/download bytes, excluded sentinels, unchanged inodes/mtime, stale cleanup and rejected unsafe sources/targets/output')


def run() -> None:
    original_root = release.ROOT
    with tempfile.TemporaryDirectory(prefix='task-tracer-release-payload-') as folder:
        base = Path(folder)
        root = base / 'repository'
        root.mkdir()
        copy_release_repository(root, original_root)
        subprocess.run(['git', 'init', '--quiet'], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.name=Synthetic release test', '-c', 'user.email=release-test@example.invalid',
                        '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty', '-m', 'Isolated release fixture'],
                       cwd=root, check=True)
        with patch.object(release, 'ROOT', root):
            normal = assert_archive(release.build(base / 'normal'))
            sentinels = {
                'public/screenshots/private-task-backup.json': b'{"tasks":[{"name":"SYNTHETIC_PRIVATE_TASK"}]}\n',
                'public/resources/operator-notes.txt': b'SYNTHETIC_OPERATOR_NOTES\n',
                'public/fav/.local-token': b'SYNTHETIC_NOT_A_REAL_TOKEN\n',
            }
            for name, data in sentinels.items():
                (root / name).write_bytes(data)
            first = assert_archive(release.build(base / 'with-unrelated-files'))
            second = assert_archive(release.build(base / 'repeat'))
            assert normal == first == second, 'Unrelated files changed the distribution or repeated builds differ'
            print('Release payload passed: three unrelated synthetic files are excluded; exact manifest and repeated bytes match')

            rejected_output = base / 'must-not-be-created'
            for name in ('fav/favicon-48x48.png', 'resources/workspace.css', 'resources/workbench.js'):
                required = application_file(root, name)
                content = required.read_bytes()
                required.unlink()
                try:
                    rejects(f'missing required asset {name}', lambda: release.build(rejected_output))
                finally:
                    required.write_bytes(content)

            outside = base / 'outside-source.txt'
            outside.write_text('SYNTHETIC_OUTSIDE_SOURCE\n')
            for name in ('index.html', 'README.md', 'README_zh_cn.md', 'resources/workspace.css', 'resources/workbench.js'):
                source = application_file(root, name)
                content = source.read_bytes()
                source.unlink()
                source.symlink_to(outside)
                try:
                    rejects(f'source symbolic link {name}', lambda: release.build(rejected_output))
                finally:
                    source.unlink()
                    source.write_bytes(content)

            icons = application_file(root, 'fav/favicon.ico').parent
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
            config_path = root / 'config/site-files.json'
            original_config = config_path.read_bytes()
            for name in ('../outside.txt', '/outside.txt', 'resources\\extra.txt', 'integrity.json'):
                configuration = json.loads(original_config)
                configuration['application'][release.distribution_sources(root)['index.html']] = name
                config_path.write_text(json.dumps(configuration) + '\n')
                try:
                    rejects(f'unsafe archive target {name!r}', lambda: release.build(rejected_output))
                finally:
                    config_path.write_bytes(original_config)
            assert not rejected_output.exists(), 'Rejected input created release output'
            check_site_build(root, base)
    print('Release payload checks passed')


if __name__ == '__main__':
    run()
