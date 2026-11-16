#!/usr/bin/env python3
"""Render the original SVG mark; --check verifies checked-in assets without a browser."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'fav/task-tracer.svg'
RECEIPT = ROOT / 'tools/icon-assets.json'
PNG_FILES = {
    'favicon-16x16.png': (16, True),
    'favicon-32x32.png': (32, True),
    'favicon-48x48.png': (48, True),
    'apple-touch-icon.png': (180, False),
    'android-chrome-192x192.png': (192, True),
    'android-chrome-512x512.png': (512, True),
    'android-chrome-maskable-512x512.png': (512, False),
}
OUTPUTS = (*PNG_FILES, 'favicon.ico')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_digest(path: Path) -> str:
    return digest(path.read_text(encoding='utf-8').encode('utf-8'))


def png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise AssertionError('Expected a PNG with an IHDR header')
    return struct.unpack('>II', data[16:24])


def source_tree() -> ET.Element:
    source = ET.fromstring(SOURCE.read_text(encoding='utf-8'))
    if source.tag != '{http://www.w3.org/2000/svg}svg' or source.get('viewBox') != '0 0 64 64':
        raise AssertionError('The brand source must be an SVG with a 64 by 64 viewBox')
    background = source.find('{http://www.w3.org/2000/svg}rect[@id="background"]')
    if background is None or any(background.get(key) != value for key, value in {
        'width': '64', 'height': '64', 'fill': '#315f50',
    }.items()):
        raise AssertionError('The source requires its opaque full-size brand background')
    return source


def render_source(size: int, rounded: bool) -> str:
    source = source_tree()
    source.set('width', str(size))
    source.set('height', str(size))
    if rounded:
        background = source.find('{http://www.w3.org/2000/svg}rect[@id="background"]')
        background.set('rx', '14')
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    return ET.tostring(source, encoding='unicode')


def make_ico(images: list[bytes]) -> bytes:
    offset = 6 + 16 * len(images)
    directory = bytearray(struct.pack('<HHH', 0, 1, len(images)))
    for data in images:
        width, height = png_size(data)
        directory.extend(struct.pack('<BBBBHHII', width % 256, height % 256, 0, 0,
                                     1, 32, len(data), offset))
        offset += len(data)
    return bytes(directory) + b''.join(images)


def validate_outputs(files: dict[str, bytes]) -> None:
    if set(files) != set(OUTPUTS):
        raise AssertionError('The generated icon set is incomplete')
    for name, (size, _rounded) in PNG_FILES.items():
        if png_size(files[name]) != (size, size):
            raise AssertionError(f'Incorrect icon dimensions: {name}')
    expected = make_ico([files[f'favicon-{size}x{size}.png'] for size in (16, 32, 48)])
    if files['favicon.ico'] != expected:
        raise AssertionError('favicon.ico must contain the current 16, 32 and 48px PNGs')


def expected_receipt(files: dict[str, bytes]) -> dict:
    return {
        'source': {'file': 'fav/task-tracer.svg', 'sha256': text_digest(SOURCE)},
        'generator': {'file': 'tools/build_icons.py', 'sha256': text_digest(Path(__file__))},
        'files': {f'fav/{name}': digest(files[name]) for name in sorted(files)},
    }


def check() -> None:
    source_tree()
    files = {name: (ROOT / 'fav' / name).read_bytes() for name in OUTPUTS}
    validate_outputs(files)
    if json.loads(RECEIPT.read_text(encoding='utf-8')) != expected_receipt(files):
        raise AssertionError('Brand source, generator or generated assets changed; run npm run icons')
    print('Brand assets match their source/generator hashes, PNG sizes and ICO frames; no browser launched')


def build() -> None:
    from playwright.sync_api import sync_playwright
    from smoke_playwright import browser_launch_options

    source_tree()
    with tempfile.TemporaryDirectory(prefix='task-tracer-icons-') as folder:
        staging = Path(folder)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**browser_launch_options('chromium'))
            try:
                context = browser.new_context(device_scale_factor=1, color_scheme='light', reduced_motion='reduce')
                page = context.new_page()
                for name, (size, rounded) in PNG_FILES.items():
                    page.set_viewport_size({'width': size, 'height': size})
                    page.set_content('<!doctype html><style>html,body{margin:0;padding:0}svg{display:block}</style>'
                                     + render_source(size, rounded))
                    page.screenshot(path=str(staging / name), animations='disabled', omit_background=rounded)
                context.close()
            finally:
                browser.close()
        files = {name: (staging / name).read_bytes() for name in PNG_FILES}
        files['favicon.ico'] = make_ico([files[f'favicon-{size}x{size}.png'] for size in (16, 32, 48)])
        validate_outputs(files)
        receipt = (json.dumps(expected_receipt(files), indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        for name, data in files.items():
            target = ROOT / 'fav' / name
            if not target.exists() or target.read_bytes() != data:
                target.write_bytes(data)
        RECEIPT.write_bytes(receipt)
    check()
    print(f'Generated {len(files)} icon assets from fav/task-tracer.svg')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify asset hashes and structure without launching Chromium')
    arguments = parser.parse_args()
    try:
        check() if arguments.check else build()
    except (AssertionError, OSError, ValueError, ET.ParseError) as error:
        raise SystemExit(f'Brand asset check failed: {error}')
