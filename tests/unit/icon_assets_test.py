#!/usr/bin/env python3
"""Reject stale brand assets and incorrect install metadata without a browser."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

from scripts import build_icons
from scripts.project_layout import distribution_sources
from scripts import validate_static as validation
from tests.support.paths import REPO_ROOT, read_source_html
from tests.support.isolated_repo import application_file


ROOT = REPO_ROOT


def rejected(operation, expected: str) -> None:
    try:
        operation()
    except AssertionError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError(f'Invalid icon fixture was accepted: {expected}')


def run() -> None:
    manifest = json.loads(application_file(ROOT, 'manifest.json').read_text())
    runtime_icons = {icon['src'] for icon in manifest['icons']} | {'fav/task-tracer.svg'}
    cached = validation.service_worker_assets(application_file(ROOT, 'sw.js').read_text())
    assert runtime_icons <= distribution_sources(ROOT).keys(), 'Runtime brand assets are missing from the distribution'
    assert {f'./{name}' for name in runtime_icons} <= cached, 'Runtime brand assets are not precached'
    with tempfile.TemporaryDirectory(prefix='task-tracer-icon-assets-') as folder:
        root = Path(folder)
        paths = {f'fav/{name}' for name in build_icons.OUTPUTS}
        paths.add('fav/task-tracer.svg')
        paths.update(image['src'] for image in manifest['screenshots'])
        paths = {distribution_sources(ROOT)[name] for name in paths}
        paths.update(('scripts/build_icons.py', 'scripts/icon-assets.json', 'config/site-files.json'))
        for name in paths:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        with patch.object(build_icons, 'ROOT', root), patch.object(build_icons, 'SOURCE', root / 'public/fav/task-tracer.svg'), \
                patch.object(build_icons, 'RECEIPT', root / 'scripts/icon-assets.json'), \
                patch.object(build_icons, '__file__', str(root / 'scripts/build_icons.py')), patch.object(validation, 'REPO_ROOT', root):
            build_icons.check()
            source = application_file(root, 'fav/task-tracer.svg')
            generator = root / 'scripts/build_icons.py'
            original_source = source.read_bytes()
            original_generator = generator.read_bytes()
            source.write_bytes(source.read_text(encoding='utf-8').replace('\n', '\r\n').encode('utf-8'))
            generator.write_bytes(generator.read_text(encoding='utf-8').replace('\n', '\r\n').encode('utf-8'))
            build_icons.check()
            source.write_bytes(original_source)
            generator.write_bytes(original_generator)
            errors: list[str] = []
            validation.validate_manifest_images(manifest, errors)
            validation.validate_brand_mark(read_source_html(ROOT), errors)
            assert not errors, errors

            changed = deepcopy(manifest)
            changed['screenshots'][0]['sizes'] = '1365x1227'
            validation.validate_manifest_images(changed, errors)
            assert any('screenshot sizes do not match' in error for error in errors), errors
            errors.clear()

            changed = deepcopy(manifest)
            changed['icons'][-1]['purpose'] = 'any maskable'
            validation.validate_manifest_images(changed, errors)
            assert any('separate maskable icon' in error for error in errors), errors
            errors.clear()

            favicon = application_file(root, 'fav/favicon-32x32.png')
            original = favicon.read_bytes()
            favicon.write_bytes(application_file(root, 'fav/favicon-16x16.png').read_bytes())
            rejected(build_icons.check, 'Incorrect icon dimensions')
            favicon.write_bytes(original)

            ico = application_file(root, 'fav/favicon.ico')
            original = ico.read_bytes()
            ico.write_bytes(original[:6])
            rejected(build_icons.check, 'favicon.ico must contain')
            ico.write_bytes(original)

            source = application_file(root, 'fav/task-tracer.svg')
            original = source.read_bytes()
            source.write_bytes(original + b'\n')
            rejected(build_icons.check, 'Brand source, generator or generated assets changed')
            source.write_bytes(original)
            build_icons.check()
    assert not any(name == 'playwright' or name.startswith('playwright.') for name in sys.modules), \
        'Static brand validation must not import Playwright'
    print('Brand asset checks passed: valid files, LF/CRLF text equivalence, stale source, wrong PNG size, broken ICO, screenshot dimensions and separate maskable purpose.')


if __name__ == '__main__':
    run()
