"""Disposable byte relay to the inherited HTTP session proxy; no TLS interception."""
from __future__ import annotations
import os
import socket
import threading
import time
from urllib.parse import urlsplit


class SessionProxyForwarder:
    def __init__(self):
        configured = os.environ.get('HTTPS_PROXY', 'http://proxy:8080')
        parsed = urlsplit(configured)
        if parsed.scheme != 'http' or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('This control requires the inherited plain-HTTP session proxy URL without inline credentials; no proxy downgrade or destination connection is performed')
        self.upstream_host = parsed.hostname
        self.upstream_port = parsed.port or 80
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._listener = None
        self._accept_thread = None
        self._workers = []
        self._sockets = set()
        self.host = '127.0.0.1'
        self.port = None
        self._counts = {'accepted_clients': 0, 'upstream_connections_opened': 0,
                        'bytes_to_upstream': 0, 'bytes_to_client': 0,
                        'upstream_connection_errors': 0, 'relay_errors': 0}

    def start(self):
        if self._listener is not None or self._stop.is_set():
            raise RuntimeError('Forwarder instances are single-use')
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, 0))
        listener.listen(32)
        listener.settimeout(0.2)
        self.port = listener.getsockname()[1]
        self._listener = listener
        self._accept_thread = threading.Thread(target=self._accept, name='session-proxy-accept', daemon=True)
        self._accept_thread.start()
        return f'http://{self.host}:{self.port}'

    def _register(self, item):
        with self._lock:
            if self._stop.is_set():
                item.close()
                raise RuntimeError('Forwarder stopped')
            self._sockets.add(item)

    def _close(self, item):
        if item is None:
            return
        with self._lock:
            self._sockets.discard(item)
        try:
            item.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            item.close()
        except OSError:
            pass

    def _accept(self):
        while not self._stop.is_set():
            try:
                client, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._register(client)
            except RuntimeError:
                break
            with self._lock:
                self._counts['accepted_clients'] += 1
                worker = threading.Thread(target=self._handle, args=(client,), name='session-proxy-tunnel', daemon=True)
                self._workers.append(worker)
                worker.start()

    def _handle(self, client):
        upstream = None
        inbound = None
        try:
            upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._register(upstream)
            upstream.settimeout(5)
            # This is the only upstream connection: the configured proxy, never the requested destination.
            upstream.connect((self.upstream_host, self.upstream_port))
            if self._stop.is_set():
                return
            with self._lock:
                self._counts['upstream_connections_opened'] += 1
            client.settimeout(0.2)
            upstream.settimeout(0.2)
            inbound = threading.Thread(target=self._pump, args=(upstream, client, 'bytes_to_client'), name='session-proxy-inbound', daemon=True)
            with self._lock:
                self._workers.append(inbound)
                inbound.start()
            self._pump(client, upstream, 'bytes_to_upstream')
        except (OSError, RuntimeError):
            if not self._stop.is_set():
                with self._lock:
                    self._counts['upstream_connection_errors'] += 1
        finally:
            self._close(client)
            self._close(upstream)
            if inbound is not None:
                inbound.join(timeout=1)

    def _pump(self, source, target, counter):
        try:
            while not self._stop.is_set():
                try:
                    data = source.recv(65536)
                except socket.timeout:
                    continue
                if not data:
                    return
                remaining = memoryview(data)
                while remaining and not self._stop.is_set():
                    try:
                        count = target.send(remaining)
                    except socket.timeout:
                        continue
                    if count == 0:
                        return
                    with self._lock:
                        self._counts[counter] += count
                    remaining = remaining[count:]
        except OSError:
            if not self._stop.is_set():
                with self._lock:
                    self._counts['relay_errors'] += 1
        finally:
            self._close(source)
            self._close(target)

    def snapshot(self):
        with self._lock:
            return {**self._counts, 'stopped': self._stop.is_set(),
                    'listener_open': self._listener is not None and self._listener.fileno() >= 0,
                    'active_sockets': sum(item.fileno() >= 0 for item in self._sockets),
                    'active_worker_threads': sum(worker.is_alive() for worker in self._workers),
                    'accept_thread_alive': bool(self._accept_thread and self._accept_thread.is_alive()),
                    'upstream_proxy_host': self.upstream_host, 'upstream_proxy_port': self.upstream_port,
                    'listen_host': self.host, 'listen_port': self.port,
                    'request_headers_or_bodies_logged': False, 'tls_intercepted': False}

    def stop(self):
        self._stop.set()
        self._close(self._listener)
        with self._lock:
            sockets = list(self._sockets)
        for item in sockets:
            self._close(item)
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1)
        deadline = time.monotonic() + 6
        with self._lock:
            workers = list(self._workers)
        for worker in workers:
            if worker is not threading.current_thread():
                worker.join(timeout=max(0, deadline - time.monotonic()))
        result = self.snapshot()
        if result['listener_open'] or result['active_sockets'] or result['active_worker_threads'] or result['accept_thread_alive']:
            raise RuntimeError('The transport control did not fully stop; offline verification must not proceed')
        return result
