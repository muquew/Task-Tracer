#!/usr/bin/env python3
"""Verify actual precache URLs against a disposable local HTTP deployment."""
from __future__ import annotations

import http.server
import json
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.error import HTTPError

import verify_deployment as deployment


def run() -> None:
    original_root = deployment.ROOT
    declared = deployment.deployment_assets()
    with tempfile.TemporaryDirectory(prefix='task-tracer-deployment-test-') as folder:
        root = Path(folder)
        sources = {original_root / name for name in ('index.html', 'sw.js', 'vercel.json')}
        sources.update(declared.values())
        for source in sources:
            target = root / source.relative_to(original_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        deployment.ROOT = root
        try:
            assets = deployment.deployment_assets()
            query = next(path for path in assets if path.startswith('resources/') and '?' in path)
            icon = next(path for path in assets if path.startswith('fav/'))
            configured = json.loads((root / 'vercel.json').read_text())
            headers = [header for route in configured['headers'] if route['source'] == '/(.*)' for header in route['headers']]
            state = {'path':None, 'status':200}
            requested = []

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(root), **kwargs)

                def log_message(self, *_args):
                    pass

                def do_GET(self):
                    requested.append(self.path)
                    if self.path.removeprefix('/') == state['path']:
                        payload = b'Synthetic stale or unavailable deployment resource'
                        self.send_response(state['status'])
                        self.send_header('Content-Type', 'application/octet-stream')
                        self.send_header('Content-Length', str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                    super().do_GET()

                def end_headers(self):
                    for header in headers:
                        self.send_header(header['key'], header['value'])
                    super().end_headers()

            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/'
                result = deployment.verify(url)
                assert result['passed']
                assert set(assets).issubset(result['checked']), 'A declared precache URL was not verified'
                assert f'/{query}' in requested, 'The versioned language URL was not actually requested'
                assert f'/{icon}' in requested, 'The required icon URL was not actually requested'
                assert 'resources/en.json' in result['checked'] and 'resources/zh-CN.json' in result['checked']
                print('Deployment verification passed: healthy exact-query precache assets, HTML and configured headers')

                for label, path, status in (
                    ('versioned language HTTP 503', query, 503),
                    ('versioned language stale HTTP 200', query, 200),
                    ('required icon HTTP 503', icon, 503),
                    ('required icon stale HTTP 200', icon, 200),
                ):
                    state.update(path=path, status=status)
                    requested.clear()
                    try:
                        deployment.verify(url)
                    except HTTPError as error:
                        assert status == 503 and error.code == 503, (label, error)
                        error.close()
                    except AssertionError as error:
                        assert status == 200 and f'Deployed asset differs: {path}' == str(error), (label, error)
                    else:
                        raise AssertionError(f'Broken deployment was accepted: {label}')
                    assert f'/{path}' in requested, f'The broken URL was not checked: {label}'
                    print(f'Deployment verification rejects: {label}')
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            worker = root / 'sw.js'
            clean_worker = worker.read_text()
            for value in ('https://outside.invalid/asset', '//outside.invalid/asset', '../escape.txt',
                          '/absolute.txt', './%2e%2e/escape.txt', './fav/../escape.txt', './fav\\escape.txt'):
                worker.write_text(clean_worker.replace('const ASSETS_TO_CACHE = [', f'const ASSETS_TO_CACHE = [\n    {json.dumps(value)},', 1))
                try:
                    deployment.deployment_assets()
                except ValueError:
                    pass
                else:
                    raise AssertionError(f'Unsafe deployment asset accepted: {value!r}')
            worker.write_text(clean_worker)
            print('Deployment verification rejects: external, absolute, traversal and backslash asset paths')
        finally:
            deployment.ROOT = original_root


if __name__ == '__main__':
    run()
