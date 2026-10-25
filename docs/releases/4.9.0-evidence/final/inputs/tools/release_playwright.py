#!/usr/bin/env python3
"""Verify reproducible packaging and execute the extracted artifact in a browser."""
from __future__ import annotations
import hashlib
import http.server
from pathlib import Path
import tempfile
import threading
import zipfile

from playwright.sync_api import expect, sync_playwright
from build_release import build, expected_distribution_files
from smoke_playwright import (ThreadingHTTPServer, add_task, assert_pwa_resources,
                              assert_service_worker_and_offline_load, browser_launch_options,
                              clear_app_data, task_locator, wait_for_app_ready)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='task-tracer-release-') as folder:
        root = Path(folder)
        first = build(root / 'one')
        second = build(root / 'two')
        assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest(), 'Release bytes are not reproducible'
        with zipfile.ZipFile(first) as archive:
            names = archive.namelist()
            expected = expected_distribution_files()
            assert len(names) == len(expected) and set(names) == expected, 'The archive differs from the explicit distribution file set'
            archive.extractall(root / 'app')
        class DistributionHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root / 'app'), **kwargs)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), DistributionHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(**browser_launch_options())
                context = browser.new_context()
                page = context.new_page()
                url = f'http://127.0.0.1:{server.server_port}/'
                assert_pwa_resources(context, url)
                clear_app_data(page, url)
                add_task(page, 'Packaged task', no_deadline=True)
                page.reload()
                wait_for_app_ready(page)
                expect(task_locator(page, 'Packaged task')).to_have_count(1)
                assert_service_worker_and_offline_load(context, page)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    print('Release passed: reproducible bytes, verified manifest, safe file set, extracted PWA persistence and offline reload')


if __name__ == '__main__':
    main()
