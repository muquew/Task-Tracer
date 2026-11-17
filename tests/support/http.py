"""Disposable HTTP servers for built-site and production-header checks."""
from __future__ import annotations
import contextlib
import io
from functools import partial
import http.server
import json
import os
from pathlib import Path
import socket
import socketserver
import threading
from typing import Iterator
from urllib.parse import urlsplit
from tests.support.paths import SITE_ROOT, ensure_site, input_path

DEFAULT_HOST = "127.0.0.1"

class StaticHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault('directory', str(SITE_ROOT))
        super().__init__(*args, **kwargs)

    def send_head(self):
        if urlsplit(self.path).path != '/__task_tracer_audit__/axe.min.js':
            return super().send_head()
        try:
            data = input_path('node_modules/axe-core/axe.min.js').read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return None
        self.send_response(200)
        self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        return io.BytesIO(data)

    def log_message(self, format: str, *args: object) -> None:
        return

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        ensure_site()
        super().__init__(*args, **kwargs)

def reserve_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])

@contextlib.contextmanager
def local_server(site_root=None, *, production_headers=False) -> Iterator[str]:
    port = reserve_port()
    handler = StaticHandler
    if production_headers or os.environ.get('TASK_TRACER_PRODUCTION_HEADERS') == '1':
        handler = ProductionHeaderHandler
    if site_root is not None:
        handler = partial(handler, directory=str(site_root))
    server = ThreadingHTTPServer((DEFAULT_HOST, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://{DEFAULT_HOST}:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive(), 'Browser regression server did not stop'


@contextlib.contextmanager
def production_server() -> Iterator[str]:
    with local_server(production_headers=True) as url:
        yield url

class ProductionHeaderHandler(StaticHandler):
    def end_headers(self) -> None:
        config = json.loads((Path(self.directory) / 'vercel.json').read_text())
        for route in config['headers']:
            if route['source'] == '/(.*)':
                for header in route['headers']:
                    self.send_header(header['key'], header['value'])
        super().end_headers()
