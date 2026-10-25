#!/usr/bin/env python3
"""Run engine-neutral critical flows; missing browser binaries fail explicitly."""
from __future__ import annotations
import argparse
import tempfile
import contextlib
import threading

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, StaticHandler, ThreadingHTTPServer, SW_CACHE_NAME,
    clear_app_data, complete_task, delete_task, edit_task, exercise_export_backup,
    exercise_import, exercise_language, select_view, task_locator,
    wait_for_app_ready,
)


@contextlib.contextmanager
def controlled_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), StaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/', server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def run(engine: str) -> None:
    with sync_playwright() as p:
        launcher = getattr(p, engine)
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        options['timeout'] = 30000
        for viewport in ({'width': 1280, 'height': 800}, {'width': 390, 'height': 844}):
            print(f'{engine} {viewport["width"]}px: starting', flush=True)
            with tempfile.TemporaryDirectory(prefix=f'task-tracer-{engine}-') as profile, controlled_server() as (url, server):
                context = launcher.launch_persistent_context(profile, viewport=viewport, accept_downloads=True, **options)
                try:
                    print(f'{engine}: {context.browser.version if context.browser else engine}', flush=True)
                    page = context.pages[0] if context.pages else context.new_page()
                    errors: list[str] = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    clear_app_data(page, url)
                    print(f'{engine}: storage initialized', flush=True)
                    exercise_language(page)
                    add_task(page, 'Portable task', no_deadline=True, project='Compatibility', tags=['portable'])
                    edit_task(page, 'Portable task', 'Portable task edited')
                    page.reload()
                    wait_for_app_ready(page)
                    expect(task_locator(page, 'Portable task edited')).to_have_count(1)
                    for view in ('calendar', 'timeline', 'stats', 'list'):
                        select_view(page, view)
                        expect(page.locator('#taskList')).to_have_attribute('aria-labelledby', f'viewTab-{view}')
                    complete_task(page, 'Portable task edited')
                    print(f'{engine}: CRUD and views passed', flush=True)
                    backup = exercise_export_backup(page)
                    assert any(task['name'] == 'Portable task edited' and task['completed'] for task in backup['tasks'])
                    exercise_import(page, 'Portable restored task')
                    print(f'{engine}: export and restore passed', flush=True)
                    delete_task(page, 'Portable restored task')
                    page.wait_for_function("async name => navigator.serviceWorker.controller && (await caches.keys()).includes(name)", arg=SW_CACHE_NAME)
                    server.shutdown()
                    server.server_close()
                    page.reload(wait_until='domcontentloaded')
                    wait_for_app_ready(page)
                    expect(page.locator('.task-item')).to_have_count(0)
                    print(f'{engine}: offline passed', flush=True)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Unexpected horizontal overflow'
                    if errors:
                        raise AssertionError(f'{engine} runtime errors: {errors}')
                finally:
                    context.close()
        print(f'{engine}: desktop/mobile critical flows and offline reload passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
