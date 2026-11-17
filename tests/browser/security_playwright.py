#!/usr/bin/env python3
"""Serve the configured deployment headers and verify real browser CSP enforcement."""
from __future__ import annotations
from tests.support.paths import (
    REPO_ROOT,
    SOURCE_HTML,
    SITE_ROOT,
    input_path,
    source_path,
    read_application_source,
    read_source_html,
)

import json
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright
from tests.support.http import StaticHandler, ThreadingHTTPServer
from tests.support.browser import add_task, browser_launch_options, clear_app_data, task_locator
from scripts.security_policy import check as check_policy

ROOT = REPO_ROOT


from tests.support.http import ProductionHeaderHandler


def main() -> None:
    check_policy()
    server = ThreadingHTTPServer(('127.0.0.1', 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**browser_launch_options())
            page = browser.new_page()
            errors: list[str] = []
            analytics: list[str] = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: analytics.append(request.url) if '/_vercel/' in request.url else None)
            clear_app_data(page, url)
            name = 'Task under enforced CSP'
            add_task(page, name, no_deadline=True)
            page.reload()
            expect(task_locator(page, name)).to_have_count(1)
            page.evaluate("""() => {
                const script = document.createElement('script');
                script.textContent = 'window.untrustedScriptExecuted = true';
                document.head.appendChild(script);
                const button = document.createElement('button');
                button.setAttribute('onclick', 'window.untrustedHandlerExecuted = true');
                document.body.appendChild(button);
                button.click();
                button.remove();
            }""")
            assert not page.evaluate('Boolean(window.untrustedScriptExecuted || window.untrustedHandlerExecuted)'), 'CSP allowed unsigned script or inline event handler'
            if errors:
                raise AssertionError(f'Application errors with deployment CSP: {errors}')
            if analytics:
                raise AssertionError(f'Unexpected analytics requests: {analytics}')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    print('Security passed: hash-authorized app runs; unsigned inline scripts and event handlers are blocked')


if __name__ == '__main__':
    main()
