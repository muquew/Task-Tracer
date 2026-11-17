"""Shared service worker update fixtures and assertions; no test entry point."""
from __future__ import annotations
from dataclasses import dataclass
from tests.support.paths import ensure_site
import hashlib
import json
import re
import socket
import threading
from urllib.parse import urlsplit
from tests.support.http import StaticHandler, ThreadingHTTPServer
from scripts.validate_static import (
    app_version as configured_app_version,
    resource_version,
    service_worker_assets,
)

@dataclass
class Bundle:
    files: dict[str, bytes]
    version: str
    resources: str

    @property
    def cache(self) -> str:
        return f'task-tracer-v{self.version}'

def bundle(files: dict[str, bytes]) -> Bundle:
    html = files['index.html'].decode()
    version = re.search(r'"softwareVersion":\s*"([\d.]+)"', html).group(1)
    assert version == configured_app_version(html), 'Application and HTML metadata versions disagree'
    resources = resource_version(html)
    return Bundle(files, version, resources)

def current_bundle() -> Bundle:
    site = ensure_site()
    paths = {'index.html', 'sw.js', 'manifest.json', 'resources/en.json', 'resources/zh-CN.json'}
    for asset in service_worker_assets((site / 'sw.js').read_text(encoding='utf-8')):
        paths.add(urlsplit(asset).path.removeprefix('./') or 'index.html')
    paths.update(path.relative_to(site).as_posix() for path in (site / 'fav').glob('*') if path.is_file())
    return bundle({path: (site / path).read_bytes() for path in sorted(paths)})

def next_number(version: str) -> str:
    values = version.split('.')
    values[-1] = str(int(values[-1]) + 1)
    return '.'.join(values)

def next_bundle(previous: Bundle) -> Bundle:
    version, resources = next_number(previous.version), next_number(previous.resources)
    files = dict(previous.files)
    html = files['index.html'].decode()
    html = html.replace(f'"softwareVersion": "{previous.version}"', f'"softwareVersion": "{version}"')
    html = html.replace(f"VERSION: '{previous.version}'", f"VERSION: '{version}'")
    html = html.replace(f"RESOURCE_VERSION: '{previous.resources}'", f"RESOURCE_VERSION: '{resources}'")
    app_assets = [asset for asset in service_worker_assets(files['sw.js'].decode())
                  if urlsplit(asset).query == f'v={previous.version}'
                  and urlsplit(asset).path.endswith(('.js', '.css'))]
    assert app_assets, 'Missing versioned application assets'
    for old_reference in app_assets:
        assert html.count(old_reference) == 1, f'Missing synthetic app asset: {old_reference}'
        html = html.replace(old_reference, old_reference.rsplit('=', 1)[0] + f'={version}', 1)
    languages = {}
    for language in ('en', 'zh-CN'):
        data = json.loads(files[f'resources/{language}.json'])
        data['app']['title'] = f'Task Tracer bundle {version}'
        files[f'resources/{language}.json'] = json.dumps(data, ensure_ascii=False).encode()
        languages[language] = data
    fallback = re.compile(r'(<script\b[^>]*\bid="bundledTranslations"[^>]*>).*?(</script>)', re.DOTALL)
    payload = json.dumps({'resourceVersion': resources, 'languages': languages}, ensure_ascii=False,
                         separators=(',', ':')).replace('<', '\\u003c')
    html = fallback.sub(lambda match: match.group(1) + payload + match.group(2), html)
    files['index.html'] = html.encode()
    worker = files['sw.js'].decode().replace(previous.cache, f'task-tracer-v{version}')
    for language in ('en', 'zh-CN'):
        worker = worker.replace(f'./resources/{language}.json?v={previous.resources}', f'./resources/{language}.json?v={resources}')
    for old_reference in app_assets:
        assert worker.count(old_reference) == 1, f'Missing synthetic cached app asset: {old_reference}'
        worker = worker.replace(old_reference, old_reference.rsplit('=', 1)[0] + f'={version}', 1)
    files['sw.js'] = worker.encode()
    return bundle(files)

class UpdateServer:
    """Serve one release at a time; stopping actually closes the TCP listener."""
    def __init__(self, initial: Bundle):
        self.bundle = initial
        self.worker_fails = False
        self.resources_fail = False
        self.shell_bundle = None
        self.block_resource = False
        self.drop_resource = False
        self.resource_requested = threading.Event()
        self.release_resource = threading.Event()
        self.requests: list[tuple[str, str, int]] = []
        self.server = None
        self.port = 0
        self.connections = set()
        self.connection_lock = threading.Lock()
        owner = self

        class Server(ThreadingHTTPServer):
            def get_request(self):
                connection, address = super().get_request()
                with owner.connection_lock:
                    owner.connections.add(connection)
                return connection, address

            def shutdown_request(self, connection):
                try:
                    super().shutdown_request(connection)
                finally:
                    with owner.connection_lock:
                        owner.connections.discard(connection)

        class Handler(StaticHandler):
            def do_GET(self):
                part = urlsplit(self.path)
                path = part.path.lstrip('/') or 'index.html'
                current = owner.bundle
                content = owner.shell_bundle if owner.shell_bundle and path in ('index.html', '') else current
                status = 503 if ((path == 'sw.js' and owner.worker_fails) or
                                 (path.startswith('resources/') and owner.resources_fail)) else 200
                if owner.block_resource and path == 'resources/zh-CN.json':
                    owner.resource_requested.set()
                    if not owner.release_resource.wait(45):
                        status = 503
                    if owner.drop_resource:
                        owner.requests.append((current.version, self.path, 0))
                        self.close_connection = True
                        return
                owner.requests.append((current.version, self.path, status))
                if status == 503:
                    data = b'Synthetic interrupted deployment'
                elif path in content.files:
                    data = content.files[path]
                else:
                    return super().do_GET()
                self.send_response(status)
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.handler = Handler
        self.server_type = Server

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}/'

    def start(self):
        self.server = self.server_type(('127.0.0.1', self.port), self.handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            with self.connection_lock:
                connections = tuple(self.connections)
                self.connections.clear()
            for connection in connections:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()
            self.thread.join(timeout=2)
            assert not self.thread.is_alive(), 'Update fixture server did not stop'
            self.server = None

def app_version(page):
    return page.evaluate("JSON.parse(document.querySelector('script[type=\"application/ld+json\"]').textContent).softwareVersion")

def workspace(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const views = tx.objectStore('config').get('savedViews');
            tx.oncomplete = () => { db.close(); resolve({tasks: tasks.result, views: views.result?.value || []}); };
            tx.onabort = () => reject(tx.error);
        };
    })""")

def installed_bundle(page, release):
    paths = sorted(service_worker_assets(release.files['sw.js'].decode()))
    assert paths, 'An installed bundle must declare its precache assets'
    result = page.evaluate("""async ({name, paths}) => {
        const cache = await caches.open(name);
        const result = {};
        for (const path of paths) {
            const response = await cache.match(path);
            if (!response) { result[path] = null; continue; }
            const hash = await crypto.subtle.digest('SHA-256', await response.arrayBuffer());
            result[path] = Array.from(new Uint8Array(hash), value => value.toString(16).padStart(2, '0')).join('');
        }
        return result;
    }""", {'name': release.cache, 'paths': paths})
    for path, actual in result.items():
        source = urlsplit(path).path.removeprefix('./') or 'index.html'
        assert actual == hashlib.sha256(release.files[source]).hexdigest(), f'Installed bundle asset missing or stale: {path}'
    return result
