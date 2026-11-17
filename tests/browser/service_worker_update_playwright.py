#!/usr/bin/env python3
"""Exercise interrupted PWA updates with real HTTP failures and physical offline reloads."""
from __future__ import annotations
from tests.support.service_worker_update import (
    Bundle,
    UpdateServer,
    app_version,
    bundle,
    current_bundle,
    installed_bundle,
    next_bundle,
    next_number,
    workspace,
)
from tests.support.paths import (
    REPO_ROOT,
    SOURCE_HTML,
    SITE_ROOT,
    input_path,
    source_path,
    read_application_source,
    read_source_html,
    ensure_site,
)

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit
import zipfile

from playwright.sync_api import expect, sync_playwright
from tests.support.http import StaticHandler, ThreadingHTTPServer
from tests.support.browser import (
    add_task,
    browser_launch_options,
    clear_app_data,
    task_locator,
    wait_for_app_ready,
)
from scripts.validate_static import (
    app_version as configured_app_version,
    resource_version,
    service_worker_assets,
)

ROOT = REPO_ROOT
TASK_NAME = 'Preserved through interrupted update'
VIEW_NAME = 'Preserved update workspace'

# Verbatim 4.6 worker, used with a clearly synthetic HTML fixture in clean CI checkouts.
LEGACY_WORKER_SOURCE = r'''
const CACHE_PREFIX = 'task-tracer-';
const CACHE_NAME = 'task-tracer-v4.6';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    './resources/en.json?v=4.30',
    './resources/zh-CN.json?v=4.30',
    './fav/favicon-16x16.png',
    './fav/favicon-32x32.png',
    './fav/favicon.ico',
    './fav/apple-touch-icon.png',
    './fav/android-chrome-192x192.png',
    './fav/android-chrome-512x512.png'
];
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(ASSETS_TO_CACHE);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});
self.addEventListener('fetch', (e) => {
    if (e.request.method !== 'GET') return;
    const url = new URL(e.request.url);
    if (url.origin !== self.location.origin) return;
    if (e.request.mode === 'navigate' || isAppShellRequest(url)) {
        e.respondWith(networkFirst(e.request, './index.html'));
        return;
    }
    if (url.pathname.includes('/resources/')) {
        e.respondWith(networkFirst(e.request));
        return;
    }
    e.respondWith(cacheFirst(e.request));
});
self.addEventListener('notificationclick', (e) => {
    e.notification.close();
    e.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                for (const client of clientList) {
                    if ('focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow('./index.html');
                }
            })
    );
});
self.addEventListener('message', (e) => {
    if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys()
            .then((keyList) => {
                return Promise.all(keyList.map((key) => {
                    if (key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                }));
            })
            .then(() => {
                return self.clients.claim();
            })
    );
});
function isAppShellRequest(url) {
    return url.pathname === '/' || url.pathname.endsWith('/index.html');
}
async function networkFirst(request, fallbackUrl) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            cacheResponse(request, networkResponse).catch((error) => {
                console.warn('[Service Worker] Cache update failed:', error);
            });
            return networkResponse;
        }
        const fallbackResponse = await getCachedFallback(request, fallbackUrl);
        if (fallbackResponse) return fallbackResponse;
        return networkResponse;
    } catch (error) {
        const fallbackResponse = await getCachedFallback(request, fallbackUrl);
        if (fallbackResponse) return fallbackResponse;
        throw error;
    }
}
async function getCachedFallback(request, fallbackUrl) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) return cachedResponse;
    if (fallbackUrl) {
        const fallbackResponse = await caches.match(fallbackUrl);
        if (fallbackResponse) return fallbackResponse;
    }
    return null;
}
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) return cachedResponse;
    const networkResponse = await fetch(request);
    cacheResponse(request, networkResponse).catch((error) => {
        console.warn('[Service Worker] Cache update failed:', error);
    });
    return networkResponse;
}
async function cacheResponse(request, response) {
    if (!response || response.status !== 200 || response.type !== 'basic') return;
    const responseToCache = response.clone();
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, responseToCache);
}
'''


def seed_workspace(page, url):
    clear_app_data(page, url)
    page.wait_for_function("async () => navigator.serviceWorker.controller && (await navigator.serviceWorker.ready).active?.state === 'activated'")
    add_task(page, TASK_NAME, description='Persist exact task, project, tags, and subtasks.',
             no_deadline=True, project='Offline release', tags=['preserve', 'update'],
             subtasks=['Subtask before upgrade'])
    page.locator('#searchInput').fill('Preserved')
    page.locator('#saveSmartViewBtn').click()
    page.locator('#savedViewNameInput').fill(VIEW_NAME)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('#searchInput').fill('')
    expect(task_locator(page, TASK_NAME)).to_have_count(1)
    page.wait_for_function("async () => navigator.serviceWorker.controller && (await navigator.serviceWorker.ready).active?.state === 'activated'")
    snapshot = workspace(page)
    assert len(snapshot['tasks']) == 1 and len(snapshot['views']) == 1
    return snapshot


def assert_workspace(page, expected, version):
    wait_for_app_ready(page)
    assert app_version(page) == version, (app_version(page), version)
    expect(task_locator(page, TASK_NAME)).to_have_count(1)
    expect(page.locator('#savedViewsList .saved-view-name').filter(has_text=VIEW_NAME)).to_have_count(1)
    assert workspace(page) == expected, 'An update changed persisted tasks or saved-view metadata'


def start_update(page):
    page.evaluate("""async () => {
        window.__updateState = 'requested';
        window.__updateError = null;
        const registration = await navigator.serviceWorker.getRegistration();
        registration.addEventListener('updatefound', () => {
            const installing = registration.installing;
            const record = () => { window.__updateState = installing.state; };
            installing.addEventListener('statechange', record);
            record();
        }, {once: true});
        registration.update().catch(error => { window.__updateError = error.name; });
    }""")


def active_worker(context, version):
    for worker in reversed(context.service_workers):
        try:
            if worker.evaluate('CACHE_NAME') == f'task-tracer-v{version}':
                return worker
        except Exception:
            continue
    raise AssertionError(f'No live worker for bundle {version}')


def legacy_fixture(current):
    files = dict(current.files)
    html = files['index.html'].decode()
    html = html.replace(f'"softwareVersion": "{current.version}"', '"softwareVersion": "4.6"')
    html = html.replace(f"VERSION: '{current.version}'", "VERSION: '4.6'")
    html = html.replace(f"RESOURCE_VERSION: '{current.resources}'", "RESOURCE_VERSION: '4.30'")
    html = re.sub(r'<script\b[^>]*\bid="bundledTranslations"[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    files['index.html'] = html.encode()
    files['sw.js'] = LEGACY_WORKER_SOURCE.encode()
    return bundle(files)


def assert_legacy_first_migration(browser, current, archive=None):
    if archive is not None:
        archive = archive.resolve()
        assert archive.is_file(), f'Legacy archive not found: {archive}'
        with zipfile.ZipFile(archive) as release:
            legacy = bundle({path: release.read(path) for path in release.namelist() if not path.endswith('/')})
        origin = f'actual {archive.name} SHA256={hashlib.sha256(archive.read_bytes()).hexdigest()}'
    else:
        legacy = legacy_fixture(current)
        origin = 'synthetic legacy HTML fixture + verbatim 4.6 networkFirst worker'
    assert legacy.version == '4.6' and legacy.resources == '4.30'
    if current.version == '4.7':
        assert current.resources == '4.31', 'The 4.7 migration must exercise its real resource version 4.31'
    assert current.resources != legacy.resources, 'Migration must request new, previously uncached language URLs'
    server = UpdateServer(legacy)
    server.start()
    context = browser.new_context()
    try:
        page = context.new_page()
        expected = seed_workspace(page, server.url)
        assert app_version(page) == legacy.version
        server.bundle = current
        server.worker_fails = server.resources_fail = True
        response = context.request.get(server.url)
        assert response.ok and f'"softwareVersion": "{current.version}"' in response.text()
        page.reload()
        assert_workspace(page, expected, current.version)
        assert any(status == 503 and '/resources/' in path for _, path, status in server.requests)
        page.evaluate("async () => { try { await (await navigator.serviceWorker.getRegistration()).update(); } catch (error) {} }")
        assert any(status == 503 and path == '/sw.js' for _, path, status in server.requests)
        assert current.cache not in page.evaluate('caches.keys()')
        server.stop()
        page.reload()
        assert_workspace(page, expected, current.version)
        print(f'PASS: {origin}; new HTML + language/SW 503 stays usable after physical offline reload', flush=True)
    finally:
        context.close()
        server.release_resource.set()
        server.stop()


def assert_atomic_updates(browser, current):
    candidate = next_bundle(current)
    future = next_bundle(candidate)
    server = UpdateServer(current)
    server.start()
    context = browser.new_context()
    try:
        old_page = context.new_page()
        expected = seed_workspace(old_page, server.url)
        baseline = installed_bundle(old_page, current)
        assert all(baseline.values()), 'The installed baseline must be complete'
        old_page.evaluate("async () => (await caches.open('unrelated-cache')).put('./unrelated', new Response('keep'))")

        server.bundle = candidate
        server.worker_fails = server.resources_fail = True
        old_page.reload()
        assert_workspace(old_page, expected, current.version)
        old_page.evaluate("async () => { try { await (await navigator.serviceWorker.getRegistration()).update(); } catch (error) {} }")
        assert installed_bundle(old_page, current) == baseline
        server.stop()
        old_page.reload()
        assert_workspace(old_page, expected, current.version)
        print('PASS: unavailable worker/languages cannot replace an installed complete bundle; physical offline reload works', flush=True)

        server.start()
        server.worker_fails = False
        start_update(old_page)
        old_page.wait_for_function("window.__updateState === 'redundant'", timeout=20_000)
        assert candidate.cache not in old_page.evaluate('caches.keys()'), 'Failed installation left a partial bundle cache'
        assert installed_bundle(old_page, current) == baseline
        server.stop()
        old_page.reload()
        assert_workspace(old_page, expected, current.version)
        print('PASS: failed candidate precache is discarded while the previous full bundle remains usable offline', flush=True)

        server.start()
        server.resources_fail = False
        server.shell_bundle = current
        start_update(old_page)
        old_page.wait_for_function("window.__updateState === 'redundant'", timeout=20_000)
        assert candidate.cache not in old_page.evaluate('caches.keys()'), 'Mixed HTTP-200 release installed under a new cache version'
        assert installed_bundle(old_page, current) == baseline
        assert_workspace(old_page, expected, current.version)
        print('PASS: HTTP-200 old HTML mixed with new worker/resources cannot install an inconsistent bundle', flush=True)

        server.shell_bundle = None
        server.block_resource = server.drop_resource = True
        start_update(old_page)
        assert server.resource_requested.wait(10), 'Candidate install never began its language transfer'
        server.stop()
        server.release_resource.set()
        old_page.wait_for_function("window.__updateState === 'redundant'", timeout=20_000)
        assert candidate.cache not in old_page.evaluate('caches.keys()')
        old_page.reload()
        assert_workspace(old_page, expected, current.version)
        assert installed_bundle(old_page, current) == baseline
        print('PASS: TCP connection loss during a required install asset preserves the full previous bundle offline', flush=True)

        server.block_resource = server.drop_resource = False
        server.resource_requested.clear()
        server.release_resource.clear()
        server.start()
        start_update(old_page)
        old_page.wait_for_function("window.__updateState === 'activated'", timeout=20_000)
        new_page = context.new_page()
        new_page.goto(server.url)
        assert_workspace(new_page, expected, candidate.version)
        assert all(installed_bundle(new_page, candidate).values())
        assert_workspace(old_page, expected, current.version)
        assert current.cache in new_page.evaluate('caches.keys()'), 'A live old page lost its bundle'
        old_page.evaluate("async () => (await fetch('./index.html')).text()")
        active_worker(context, candidate.version).evaluate('async () => { await cleanupOldBundleCaches(); }')
        assert current.cache in new_page.evaluate('caches.keys()'), 'A background shell fetch misidentified an old live client as the new version'
        old_page.evaluate("""() => {
            const postMessage = ServiceWorker.prototype.postMessage;
            ServiceWorker.prototype.postMessage = function(message, ...args) {
                if (message?.type !== 'CLIENT_VERSION') return postMessage.call(this, message, ...args);
            };
        }""")
        worker = active_worker(context, candidate.version)
        worker.evaluate('() => { clientBundles.clear(); requestedClientVersions.clear(); }')
        old_page.evaluate("async () => (await fetch('./index.html')).text()")
        worker.evaluate('async () => { await cleanupOldBundleCaches(); }')
        assert current.cache in new_page.evaluate('caches.keys()'), 'An unknown legacy client lost its old bundle after an ordinary shell fetch'
        old_title = json.loads(current.files['resources/en.json'])['app']['title']
        title = old_page.evaluate("async version => (await (await fetch(`./resources/en.json?v=${version}`)).json()).app.title", current.resources)
        assert title == old_title, 'Old page received a different language resource version'
        candidate_title = new_page.evaluate("async version => (await (await fetch(`./resources/en.json?v=${version}`)).json()).app.title", candidate.resources)
        assert candidate_title != old_title
        print('PASS: healthy update retains exact old-language URLs and protects known/unknown old clients from background shell fetches', flush=True)

        app_urls = [asset for asset in service_worker_assets(current.files['sw.js'].decode())
                    if urlsplit(asset).query == f'v={current.version}'
                    and urlsplit(asset).path.endswith(('.js', '.css'))]
        assert any(urlsplit(asset).path.startswith('./app/') for asset in app_urls), 'The fixture must exercise external application modules'
        expected_assets = {asset: hashlib.sha256(current.files[urlsplit(asset).path.removeprefix('./')]).hexdigest()
                           for asset in app_urls}
        server.stop()
        old_assets = old_page.evaluate("""async urls => {
            const entries = await Promise.all(urls.map(async url => {
                const response = await fetch(url, {cache: 'no-store'});
                if (!response.ok) throw new Error('Old application asset unavailable offline');
                const digest = await crypto.subtle.digest('SHA-256', await response.arrayBuffer());
                return [url, Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('')];
            }));
            return Object.fromEntries(entries);
        }""", app_urls)
        assert old_assets == expected_assets, 'The new worker lost or mixed an old client application module'
        unknown_asset = app_urls[0].rsplit('=', 1)[0] + '=999.999.999'
        unknown_response = old_page.evaluate("""async url => {
            try {
                const response = await fetch(url, {cache: 'no-store'});
                return {rejected: !response.ok, status: response.status, url: response.url};
            } catch { return {rejected: true}; }
        }""", unknown_asset)
        assert unknown_response['rejected'], ('An uncached version was served bytes from a different application bundle',
                                               unknown_asset, unknown_response)
        server.start()
        print('PASS: the active new worker serves every exact old module/CSS URL offline and rejects an uncached version', flush=True)

        server.bundle = future
        server.block_resource = True
        start_update(new_page)
        assert server.resource_requested.wait(10), 'Future worker never requested its required language asset'
        new_page.wait_for_function('async name => (await caches.keys()).includes(name)', arg=future.cache)
        worker = active_worker(context, candidate.version)
        worker.evaluate('async () => { await cleanupOldBundleCaches(); }')
        assert future.cache in new_page.evaluate('caches.keys()'), 'Active cleanup deleted an installing future bundle'
        server.release_resource.set()
        new_page.wait_for_function("window.__updateState === 'activated'", timeout=20_000)
        newest_page = context.new_page()
        newest_page.goto(server.url)
        assert_workspace(newest_page, expected, future.version)
        old_page.close()
        new_page.close()
        newest_page.evaluate("version => navigator.serviceWorker.controller.postMessage({type: 'CLIENT_VERSION', version})", future.version)
        newest_page.wait_for_function("async names => { const keys = await caches.keys(); return names.every(name => !keys.includes(name)); }", arg=[current.cache, candidate.cache])
        assert 'unrelated-cache' in newest_page.evaluate('caches.keys()')
        server.stop()
        newest_page.reload()
        assert_workspace(newest_page, expected, future.version)
        print('PASS: active cleanup protects an installing bundle, cleans unused old bundles, and preserves unrelated caches/data offline', flush=True)
    finally:
        server.release_resource.set()
        context.close()
        server.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['all', 'legacy', 'atomic'], default='all')
    parser.add_argument('--legacy-archive', type=Path, help='Test a real prior release ZIP instead of the self-contained synthetic legacy fixture')
    args = parser.parse_args()
    current = current_bundle()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        try:
            if args.case in ('all', 'legacy'):
                assert_legacy_first_migration(browser, current, args.legacy_archive)
            if args.case in ('all', 'atomic'):
                assert_atomic_updates(browser, current)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
