#!/usr/bin/env python3
"""Verify release metadata with isolated real static checks and distribution builds."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from build_release import DISTRIBUTION_SOURCES, expected_distribution_files, validated_source
from translation_fallback import main_script
from validate_static import app_version, resource_version


ROOT = Path(__file__).resolve().parents[1]


def command(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *arguments], cwd=root, capture_output=True, text=True)


def succeeds(root: Path, *arguments: str) -> None:
    result = command(root, *arguments)
    assert result.returncode == 0, result.stdout + result.stderr


def assert_archive(path: Path, version: str) -> None:
    assert path.name == f'task-tracer-{version}.zip'
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = expected_distribution_files()
        assert len(names) == 24 and len(names) == len(expected) and set(names) == expected
        metadata = json.loads(archive.read('integrity.json'))
        assert metadata['version'] == version
        assert set(metadata['files']) == expected - {'integrity.json'}
        for name, digest in metadata['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.with_suffix('.zip.sha256').read_text() == f'{digest}  {path.name}\n'


def build(root: Path, output: Path, version: str) -> None:
    succeeds(root, 'tools/validate_static.py')
    succeeds(root, 'tools/build_release.py', '--output-dir', str(output))
    archives = list(output.glob('*.zip'))
    assert len(archives) == 1
    assert_archive(archives[0], version)


def reject_versions(root: Path, output: Path, label: str) -> None:
    for arguments in (('tools/validate_static.py',), ('tools/build_release.py', '--output-dir', str(output))):
        result = command(root, *arguments)
        assert result.returncode != 0, f'{label} was accepted by {arguments[0]}'
        assert 'package' in result.stdout.lower() + result.stderr.lower(), result.stdout + result.stderr
    assert not output.exists(), f'{label} created a release output'
    print(f'Release version rejection passed: {label}')


def run() -> None:
    with tempfile.TemporaryDirectory(prefix='task-tracer-release-versions-') as folder:
        base = Path(folder)
        root = base / 'repository'
        root.mkdir()
        sources = set(DISTRIBUTION_SOURCES.values()) | {'package.json', 'package-lock.json'}
        for name in sources:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(validated_source(ROOT, name), target)
        (root / 'tools').mkdir()
        for name in ('build_release.py', 'validate_static.py', 'translation_fallback.py', 'security_policy.py'):
            shutil.copy2(ROOT / 'tools' / name, root / 'tools' / name)
        subprocess.run(['git', 'init', '--quiet'], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.name=Synthetic release versions', '-c', 'user.email=versions@example.invalid',
                        '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty', '-m', 'Isolated version fixture'],
                       cwd=root, check=True)
        original = {name: (root / name).read_bytes() for name in sources}

        def restore():
            for name, data in original.items():
                (root / name).write_bytes(data)

        def write_package(change):
            package = json.loads(original['package.json'])
            lock = json.loads(original['package-lock.json'])
            change(package, lock)
            (root / 'package.json').write_text(json.dumps(package, indent=2) + '\n')
            (root / 'package-lock.json').write_text(json.dumps(lock, indent=2) + '\n')

        actual_version = app_version(original['index.html'].decode())
        actual_resources = resource_version(original['index.html'].decode())
        build(root, base / 'normal', actual_version)
        print(f'Release versions passed: current {actual_version} metadata builds exactly 24 files')

        drift = '9.9.9' if actual_version != '9.9.9' else '8.8.8'
        stale = '4.7.0' if json.loads(original['package.json'])['version'] != '4.7.0' else '4.6.0'
        cases = {
            'package version drift': lambda package, lock: package.update(version=drift),
            'lock top-level version drift': lambda package, lock: lock.update(version=drift),
            'lock root version drift': lambda package, lock: lock['packages'][''].update(version=drift),
            'all package versions stale': lambda package, lock: (
                package.update(version=stale), lock.update(version=stale), lock['packages'][''].update(version=stale)),
            'missing package version': lambda package, lock: package.pop('version'),
            'missing lock top-level version': lambda package, lock: lock.pop('version'),
            'missing lock root version': lambda package, lock: lock['packages'][''].pop('version'),
            'missing lock root metadata': lambda package, lock: lock['packages'].pop(''),
        }
        for index, (label, change) in enumerate(cases.items()):
            restore()
            write_package(change)
            reject_versions(root, base / f'rejected-{index}', label)
        for name in ('package.json', 'package-lock.json'):
            restore()
            (root / name).unlink()
            reject_versions(root, base / f'rejected-{name}', f'missing {name}')

        restore()
        source = (root / 'index.html').read_text()
        runtime = main_script(source)
        updated = re.sub(r'''(\bAPP:\s*\{\s*VERSION:\s*)(['"])[^'"]+\2''', lambda match: match[1] + match[2] + '12.34' + match[2],
                         runtime.group('content'), count=1)
        assert updated != runtime.group('content')
        source = source[:runtime.start('content')] + updated + source[runtime.end('content'):]
        source = re.sub(r'("softwareVersion":\s*")[^"]+(")', lambda match: match[1] + '12.34' + match[2], source, count=1)
        (root / 'index.html').write_text(source)
        worker = (root / 'sw.js').read_text()
        worker = re.sub(r"(const CACHE_NAME = ['\"])[^'\"]+(['\"])",
                        lambda match: match[1] + 'task-tracer-v12.34' + match[2], worker, count=1)
        (root / 'sw.js').write_text(worker)
        write_package(lambda package, lock: (package.update(version='12.34.0'), lock.update(version='12.34.0'),
                                             lock['packages'][''].update(version='12.34.0')))
        succeeds(root, 'tools/security_policy.py', '--write')
        build(root, base / 'two-component-app', '12.34')
        print('Release versions passed: APP X.Y and npm X.Y.0 remain compatible')

        restore()
        diagnostic = ("VERSION: '99.99'; APP: { VERSION: '98.97' }; I18N: { RESOURCE_VERSION: '96.95' }; "
                      "LANGUAGES: [{ code: 'xx' }]; DEFAULTS: { LANG: 'xx' }")
        for language in ('en', 'zh-CN'):
            path = root / 'resources' / f'{language}.json'
            data = json.loads(path.read_text())
            data['help']['releaseVersionExamples'] = diagnostic
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        succeeds(root, 'tools/translation_fallback.py', '--write')
        succeeds(root, 'tools/security_policy.py', '--write')
        modified = (root / 'index.html').read_text()
        assert main_script(modified).group('content') == main_script(original['index.html'].decode()).group('content')
        assert (root / 'sw.js').read_bytes() == original['sw.js']
        assert app_version(modified) == actual_version and resource_version(modified) == actual_resources
        build(root, base / 'translation-examples', actual_version)
        print('Release versions passed: legitimate translation VERSION/APP/I18N/LANGUAGES/DEFAULTS examples do not alter parsed release metadata')
    print('Release version checks passed')


if __name__ == '__main__':
    run()
