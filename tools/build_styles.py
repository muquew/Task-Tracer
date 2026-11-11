#!/usr/bin/env python3
"""Compile the checked-in stylesheet with the locally installed Tailwind CLI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'styles/workspace.css'
OUTPUT = ROOT / 'resources/workspace.css'
CLI = ROOT / 'node_modules/@tailwindcss/cli/dist/index.mjs'


def build(*, check: bool = False) -> None:
    node = shutil.which('node')
    if not node or not CLI.is_file():
        raise AssertionError('Install the locked development dependencies with npm ci --ignore-scripts before compiling styles')
    if not SOURCE.is_file():
        raise AssertionError(f'Missing stylesheet source: {SOURCE.relative_to(ROOT)}')
    original = SOURCE.read_bytes()
    with tempfile.TemporaryDirectory(prefix='task-tracer-styles-') as folder:
        compiled = Path(folder) / 'workspace.css'
        subprocess.run([node, str(CLI), '--input', str(SOURCE), '--output', str(compiled), '--minify'],
                       cwd=ROOT, check=True)
        data = compiled.read_bytes()
        if not data:
            raise AssertionError('Stylesheet compilation produced an empty file')
        if SOURCE.read_bytes() != original:
            raise AssertionError('Stylesheet source changed during compilation; retry after edits finish')
    if check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise AssertionError('resources/workspace.css differs from its source; run npm run styles')
        print('Checked-in stylesheet matches the local Tailwind build')
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
        with tempfile.NamedTemporaryFile(prefix='.workspace-', suffix='.css', dir=OUTPUT.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.replace(temporary, OUTPUT)
        finally:
            temporary.unlink(missing_ok=True)
    print(f'Compiled {SOURCE.relative_to(ROOT)} to {OUTPUT.relative_to(ROOT)} ({len(data)} bytes)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare a temporary build with the checked-in stylesheet without writing it')
    arguments = parser.parse_args()
    try:
        build(check=arguments.check)
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Stylesheet build failed: {error}')
