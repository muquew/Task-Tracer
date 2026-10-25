#!/usr/bin/env python3
"""Optional read-only deployment verification; never a prerequisite for local tests."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import urlopen

from validate_static import app_version, service_worker_assets

ROOT = Path(__file__).resolve().parents[1]


def deployment_assets() -> dict[str, Path]:
    declared = service_worker_assets((ROOT / 'sw.js').read_text(encoding='utf-8'))
    declared.update({'sw.js', 'manifest.json', 'resources/en.json', 'resources/zh-CN.json'})
    assets = {}
    for asset in sorted(declared):
        parsed = urlsplit(asset)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise ValueError(f'Deployment assets must use local paths: {asset!r}')
        name = unquote(parsed.path).removeprefix('./')
        if not name:
            if not parsed.query:
                continue
            name = 'index.html'
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix() != name or any(value in name for value in ('\\', '\x00', ':')):
            raise ValueError(f'Unsafe deployment asset path: {asset!r}')
        source = ROOT / name
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f'Missing or unsafe deployment source: {name}')
        request_path = parsed.path.removeprefix('./') + (f'?{parsed.query}' if parsed.query else '')
        assets[request_path] = source
    return assets


def verify(base: str) -> dict:
    parsed = urlsplit(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a site root URL without credentials, query or fragment')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
        raise ValueError('Deployment verification requires HTTPS (local fixtures may use HTTP)')
    base = base.rstrip('/') + '/'
    checked = []
    def read(path: str):
        with urlopen(urljoin(base, path), timeout=20) as response:
            payload = response.read()
            checked.append(path or '/')
            return payload, response.headers
    index, headers = read('')
    expected = (ROOT / 'index.html').read_bytes()
    if hashlib.sha256(index).digest() != hashlib.sha256(expected).digest():
        actual = re.search(rb"VERSION:\s*'([\d.]+)'", index)
        raise AssertionError(f'Deployed HTML differs from this checkout (reported version: {actual.group(1).decode() if actual else "unknown"})')
    config = json.loads((ROOT / 'vercel.json').read_text())
    for route in config['headers']:
        if route['source'] != '/(.*)':
            continue
        for header in route['headers']:
            actual = headers.get(header['key'])
            wanted = header['value']
            if actual is None:
                raise AssertionError(f'Missing deployed header: {header["key"]}')
            if header['key'].lower() == 'content-security-policy':
                normalize = lambda value: {part.split()[0]: set(part.split()[1:]) for part in value.split(';') if part.strip()}
                if normalize(actual) != normalize(wanted):
                    raise AssertionError('Deployed CSP differs from this checkout')
            elif actual.strip() != wanted.strip():
                raise AssertionError(f'Deployed header differs: {header["key"]}')
    for path, source in deployment_assets().items():
        data, _ = read(path)
        if data != source.read_bytes():
            raise AssertionError(f'Deployed asset differs: {path}')
    version = app_version(expected.decode('utf-8'))
    return {'site': base, 'version': version, 'checked': checked, 'passed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='https://todo.muquew.com/')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.url), indent=2))
    except Exception as error:
        raise SystemExit(f'Deployment verification failed: {type(error).__name__}: {error}')
