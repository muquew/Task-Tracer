#!/usr/bin/env python3
"""Verify release metadata with isolated real static checks and distribution builds."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from scripts.build_release import expected_distribution_files
from scripts.translation_fallback import main_script
from scripts.validate_static import app_version, resource_version
from tests.support.paths import REPO_ROOT
from tests.support.isolated_repo import application_file, copy_release_repository


ROOT = REPO_ROOT


def command(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *arguments], cwd=root, capture_output=True, text=True)


def succeeds(root: Path, *arguments: str) -> None:
    result = command(root, *arguments)
    assert result.returncode == 0, result.stdout + result.stderr


def assert_archive(path: Path, version: str, root: Path) -> None:
    assert path.name == f'task-tracer-{version}.zip'
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = expected_distribution_files(root=root)
        assert len(names) == len(expected) and set(names) == expected
        metadata = json.loads(archive.read('integrity.json'))
        assert metadata['version'] == version
        assert set(metadata['files']) == expected - {'integrity.json'}
        for name, digest in metadata['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.with_suffix('.zip.sha256').read_text() == f'{digest}  {path.name}\n'


def build(root: Path, output: Path, version: str) -> None:
    succeeds(root, '-m', 'scripts.validate_static')
    succeeds(root, '-m', 'scripts.build_release', '--output-dir', str(output))
    archives = list(output.glob('*.zip'))
    assert len(archives) == 1
    assert_archive(archives[0], version, root)


def reject_versions(root: Path, output: Path, label: str) -> None:
    for arguments in (('-m', 'scripts.validate_static'), ('-m', 'scripts.build_release', '--output-dir', str(output))):
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
        sources = copy_release_repository(root, ROOT)
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

        html_file = application_file(root, 'index.html')
        worker_path = application_file(root, 'sw.js')
        original_html = html_file.read_text()
        original_worker = worker_path.read_bytes()
        actual_version = app_version(original_html)
        actual_resources = resource_version(original_html)
        build(root, base / 'normal', actual_version)
        print(f'Release versions passed: current {actual_version} metadata builds exactly {len(expected_distribution_files(root=root))} files')

        workbench_reference = f'./resources/workbench.js?v={actual_version}'
        workbench_tag = re.search(r'<script\b[^>]*\bsrc=[\'"]' + re.escape(workbench_reference) + r'[\'"][^>]*>\s*</script>',
                                  original_html)
        assert workbench_tag, 'Expected one current workbench loader in the source fixture'
        domain_tags = re.findall(r'<script\b[^>]*\bsrc=[\'"]\./app/domain/[^\'"]+[\'"][^>]*>\s*</script>', original_html)
        assert len(domain_tags) >= 2, 'Expected two ordered domain loaders in the source fixture'

        def swap(source, first, second):
            marker = 'SYNTHETIC_RUNTIME_LOADER_SWAP'
            assert marker not in source and source.count(first) == source.count(second) == 1
            return source.replace(first, marker, 1).replace(second, first, 1).replace(marker, second, 1)

        mapped_modules_error = 'index.html must load every mapped runtime JavaScript module in manifest order with the current app version'
        asset_cases = (
            ('stale workbench URL', lambda source: source.replace(workbench_reference, './resources/workbench.js?v=0.0.0', 1), mapped_modules_error),
            ('missing workbench loader', lambda source: source.replace(workbench_tag.group(), '', 1), mapped_modules_error),
            ('deferred workbench loader', lambda source: source.replace(workbench_tag.group(), workbench_tag.group().replace('<script ', '<script defer ', 1), 1),
             'The workbench must load as an ordered classic script'),
            ('late workbench loader', lambda source: source.replace(workbench_tag.group(), '', 1).replace('</body>', workbench_tag.group() + '\n</body>', 1),
             'Ordered classic runtime modules must load before the CONFIG bootstrap'),
            ('reordered domain loaders', lambda source: swap(source, *domain_tags[:2]), mapped_modules_error),
        )
        for index, (label, change, expected_error) in enumerate(asset_cases):
            restore()
            source = original_html
            changed = change(source)
            assert changed != source, label
            html_file.write_text(changed)
            output = base / f'rejected-workbench-{index}'
            for arguments in (('-m', 'scripts.validate_static'), ('-m', 'scripts.build_release', '--output-dir', str(output))):
                result = command(root, *arguments)
                assert result.returncode != 0 and expected_error in result.stdout + result.stderr, (label, result.stdout, result.stderr)
            assert not output.exists(), label
            print(f'Release asset rejection passed: {label}')
        restore()
        domain_urls = [re.search(r'src=[\'"]([^\'"]+)', tag).group(1) for tag in domain_tags[:2]]
        worker_path.write_text(swap(original_worker.decode(), *domain_urls))
        output = base / 'rejected-worker-module-order'
        for arguments in (('-m', 'scripts.validate_static'), ('-m', 'scripts.build_release', '--output-dir', str(output))):
            result = command(root, *arguments)
            assert result.returncode != 0 and 'Service worker runtime module order' in result.stdout + result.stderr, (result.stdout, result.stderr)
        assert not output.exists(), 'Reordered worker modules created release output'
        print('Release asset rejection passed: reordered service worker modules')
        restore()

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
        source = html_file.read_text()
        runtime = main_script(source)
        updated = re.sub(r'''(\bAPP:\s*\{\s*VERSION:\s*)(['"])[^'"]+\2''', lambda match: match[1] + match[2] + '12.34' + match[2],
                         runtime.group('content'), count=1)
        assert updated != runtime.group('content')
        source = source[:runtime.start('content')] + updated + source[runtime.end('content'):]
        source = re.sub(r'("softwareVersion":\s*")[^"]+(")', lambda match: match[1] + '12.34' + match[2], source, count=1)
        versioned_assets = re.findall(r'(?:src|href)=[\'"](\./[^\'"?#]+\.(?:js|css)\?v=' + re.escape(actual_version) + r')[\'"]', source)
        assert len(versioned_assets) >= 2 and len(versioned_assets) == len(set(versioned_assets))
        for previous in versioned_assets:
            source = source.replace(previous, previous.rsplit('=', 1)[0] + '=12.34', 1)
        html_file.write_text(source)
        worker = worker_path.read_text()
        worker = re.sub(r"(const CACHE_NAME = ['\"])[^'\"]+(['\"])",
                        lambda match: match[1] + 'task-tracer-v12.34' + match[2], worker, count=1)
        for previous in versioned_assets:
            assert worker.count(previous) == 1
            worker = worker.replace(previous, previous.rsplit('=', 1)[0] + '=12.34', 1)
        worker_path.write_text(worker)
        write_package(lambda package, lock: (package.update(version='12.34.0'), lock.update(version='12.34.0'),
                                             lock['packages'][''].update(version='12.34.0')))
        succeeds(root, '-m', 'scripts.security_policy', '--write')
        build(root, base / 'two-component-app', '12.34')
        print('Release versions passed: APP X.Y and npm X.Y.0 remain compatible')

        restore()
        diagnostic = ("VERSION: '99.99'; APP: { VERSION: '98.97' }; I18N: { RESOURCE_VERSION: '96.95' }; "
                      "LANGUAGES: [{ code: 'xx' }]; DEFAULTS: { LANG: 'xx' }")
        for language in ('en', 'zh-CN'):
            path = application_file(root, f'resources/{language}.json')
            data = json.loads(path.read_text())
            data['help']['releaseVersionExamples'] = diagnostic
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        succeeds(root, '-m', 'scripts.translation_fallback', '--write')
        succeeds(root, '-m', 'scripts.security_policy', '--write')
        modified = html_file.read_text()
        assert main_script(modified).group('content') == main_script(original_html).group('content')
        assert worker_path.read_bytes() == original_worker
        assert app_version(modified) == actual_version and resource_version(modified) == actual_resources
        build(root, base / 'translation-examples', actual_version)
        print('Release versions passed: legitimate translation VERSION/APP/I18N/LANGUAGES/DEFAULTS examples do not alter parsed release metadata')
    print('Release version checks passed')


if __name__ == '__main__':
    run()
