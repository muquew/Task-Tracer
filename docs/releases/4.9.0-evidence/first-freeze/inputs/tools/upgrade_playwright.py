#!/usr/bin/env python3
"""Exercise old-to-new PWA upgrade and rollback on the same origin without resetting data."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import threading
from urllib.parse import urlparse
import zipfile

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import click_task_action, reveal_workspace_control
from smoke_playwright import (StaticHandler, ThreadingHTTPServer, add_task,
                              browser_launch_options, clear_app_data, delete_task,
                              task_locator, wait_for_app_ready)
from validate_static import app_version as configured_app_version

ROOT = Path(__file__).resolve().parents[1]
BASE_REF = os.environ.get('TASK_TRACER_UPGRADE_BASE', '1c3bacb0ca8015fb5840c6b5d1d5efa0937e6e28')


@dataclass
class Baseline:
    files: dict[str, bytes]
    version: str
    cache_name: str
    source: str

    @property
    def typed_views(self) -> bool:
        return tuple(int(part) for part in self.version.split('.')) >= (4, 7)


def bundle_metadata(files: dict[str, bytes], source: str) -> Baseline:
    html = files['index.html'].decode()
    version = re.search(r'"softwareVersion":\s*"([\d.]+)"', html)
    declared = configured_app_version(html)
    cache = re.search(r"\bconst CACHE_NAME = ['\"]([^'\"]+)['\"]", files['sw.js'].decode())
    assert version and declared and cache, f'Missing application/worker versions: {source}'
    assert version.group(1) == declared, f'HTML/application versions disagree: {source}'
    assert cache.group(1) == f'task-tracer-v{version.group(1)}', f'Worker/application versions disagree: {source}'
    return Baseline(files, version.group(1), cache.group(1), source)


def safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not any(character in name for character in ('\\', '\x00', ':')) \
        and not path.is_absolute() and '..' not in path.parts and path.as_posix() == name


def load_archive(path: Path) -> Baseline:
    path = path.resolve()
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        assert len(entries) <= 128, 'Baseline archive has too many entries'
        assert len({entry.filename for entry in entries}) == len(entries), 'Duplicate baseline ZIP entries'
        assert sum(entry.file_size for entry in entries) <= 64 * 1024 * 1024, 'Baseline archive is too large'
        files = {}
        for entry in entries:
            assert safe_archive_name(entry.orig_filename), f'Unsafe baseline path: {entry.orig_filename!r}'
            assert not entry.is_dir() and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG), 'Baseline entries must be regular files'
            assert entry.file_size <= 32 * 1024 * 1024, 'Baseline file is too large'
            files[entry.filename] = archive.read(entry)
    manifest = json.loads(files['integrity.json'])
    assert isinstance(manifest, dict) and isinstance(manifest.get('files'), dict), 'Invalid baseline integrity manifest'
    assert set(files) == set(manifest['files']) | {'integrity.json'}, 'Manifest and baseline file set differ'
    for name, digest in manifest['files'].items():
        assert safe_archive_name(name) and name != 'integrity.json', 'Unsafe manifest path'
        assert isinstance(digest, str) and re.fullmatch(r'[a-f0-9]{64}', digest), f'Invalid baseline checksum: {name}'
        assert hashlib.sha256(files[name]).hexdigest() == digest, f'Baseline integrity mismatch: {name}'
    for required in ('index.html', 'sw.js', 'manifest.json', 'resources/en.json', 'resources/zh-CN.json'):
        assert required in files, f'Missing baseline runtime file: {required}'
    baseline = bundle_metadata(files, f'actual {path.name} SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}')
    assert manifest.get('version') == baseline.version, 'Manifest/application versions disagree'
    return baseline


def load_baseline(archive: Path | None) -> Baseline:
    if archive is not None:
        return load_archive(archive)
    files = {path: subprocess.check_output(['git', 'show', f'{BASE_REF}:{path}'], cwd=ROOT)
             for path in ('index.html', 'sw.js', 'resources/en.json', 'resources/zh-CN.json')}
    return bundle_metadata(files, f'git {BASE_REF}')


def app_version(page) -> str:
    return page.evaluate(r"""() => {
        const metadata = [...document.querySelectorAll('script[type="application/ld+json"]')]
            .map(node => JSON.parse(node.textContent)).find(value => value.softwareVersion);
        const main = [...document.scripts].find(node => /^\s*\(function\s*\(\s*\)\s*\{\s*const\s+CONFIG\s*=/.test(node.textContent));
        const declared = main?.textContent.match(/\bAPP:\s*\{\s*VERSION:\s*'([^']+)'/)?.[1];
        if (!metadata || metadata.softwareVersion !== declared) throw new Error('Loaded page version metadata disagrees');
        return declared;
    }""")


def assert_controller(context, page, expected: Baseline) -> None:
    page.wait_for_function("""async () => {
        const registration = await navigator.serviceWorker.getRegistration();
        return registration?.active?.state === 'activated' &&
            navigator.serviceWorker.controller === registration.active;
    }""", timeout=20000)
    found = False
    for worker in reversed(context.service_workers):
        try:
            if worker.evaluate('CACHE_NAME') != expected.cache_name:
                continue
            worker.evaluate("""() => {
                if (self.__taskTracerUpgradeProbeReady) return;
                self.__taskTracerUpgradeProbeReady = true;
                self.addEventListener('message', event => {
                    if (event.data?.type === 'TASK_TRACER_UPGRADE_TEST_IDENTITY') event.ports[0]?.postMessage(CACHE_NAME);
                });
            }""")
            found = True
        except Exception:
            continue
    assert found, f'No live worker for {expected.version}'
    actual = page.evaluate("""async () => {
        const deadline = Date.now() + 20000;
        while (!navigator.serviceWorker.controller || navigator.serviceWorker.controller.state !== 'activated') {
            if (Date.now() > deadline) throw new Error('Activated controller did not become ready');
            await new Promise(resolve => setTimeout(resolve, 25));
        }
        const controller = navigator.serviceWorker.controller;
        return new Promise((resolve, reject) => {
        const channel = new MessageChannel();
        const timer = setTimeout(() => reject(new Error('Controller identity probe timed out')), 5000);
        channel.port1.onmessage = event => { clearTimeout(timer); resolve(event.data); };
        controller.postMessage({type:'TASK_TRACER_UPGRADE_TEST_IDENTITY'}, [channel.port2]);
        });
    }""")
    assert actual == expected.cache_name, f'Wrong controlling worker: {actual}, expected {expected.cache_name}'


def workspace(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const views = tx.objectStore('config').get('savedViews');
            tx.oncomplete = () => { db.close(); resolve({tasks:tasks.result, views:views.result?.value || []}); };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def assert_workspace(context, page, expected, release):
    wait_for_app_ready(page)
    assert app_version(page) == release.version, f'The page did not actually load {release.version}'
    assert_controller(context, page, release)
    assert workspace(page) == expected, f'Task fields or saved-view metadata changed while loading {release.version}'
    baseline_view = next(view for view in expected['views'] if view['name'] == 'Baseline migration view')
    reveal_workspace_control(page, page.locator(f'[data-saved-view-id={json.dumps(baseline_view["id"])}]')).click()
    expect(task_locator(page, 'Created before upgrade')).to_have_count(1)
    typed = isinstance(baseline_view['projectFilter'], dict)
    expect(task_locator(page, 'Created outside saved project')).to_have_count(0 if typed else 1)
    page.locator('#clearSearchBtn').click()
    assert workspace(page) == expected, 'Applying a migrated view rewrote stored task/view fields'


def offline_roundtrip(context, page, expected, release):
    context.set_offline(True)
    try:
        page.reload(wait_until='load')
        assert_workspace(context, page, expected, release)
    finally:
        context.set_offline(False)


def save_view(page, name, typed, query='Created'):
    page.locator('#searchInput').fill('no-task-matches-this-upgrade-query')
    expect(page.locator('.task-item')).to_have_count(0)
    page.locator('#searchInput').fill(query)
    matching_name = 'Created before upgrade' if query == 'Created' else 'Created after upgrade'
    expect(task_locator(page, matching_name)).to_have_count(1)
    if typed:
        page.locator('#projectFilterBtn').click()
        encoded = json.dumps({'kind':'project', 'name':'all'}, separators=(',', ':'))
        page.locator(f'#projectDropdown .dropdown-option[data-project={json.dumps(encoded)}]').click()
    page.locator('#saveSmartViewBtn').click()
    page.locator('#savedViewNameInput').fill(name)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('#clearSearchBtn').click()
    expect(task_locator(page, 'Created before upgrade')).to_have_count(1)
    if typed:
        saved = next(view for view in workspace(page)['views'] if view['name'] == name)
        assert saved['projectFilter'] == {'kind':'project', 'name':'all'}, 'The baseline did not persist a real typed project scope'


def exercise_crud(page, phase):
    before = workspace(page)
    name = f'Temporary CRUD {phase}'
    add_task(page, name, no_deadline=True, project='all', tags=['crud', 'migration'], subtasks=['Preserve subtask'])
    created = next(task for task in workspace(page)['tasks'] if task['name'] == name)
    click_task_action(task_locator(page, name), 'edit')
    description = f'Edited during actual {phase}'
    page.locator('#taskDesc').fill(description)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    edited = next(task for task in workspace(page)['tasks'] if task['name'] == name)
    assert edited == {**created, 'description':description}, 'An ordinary description edit changed unrelated fields'
    delete_task(page, name)
    assert workspace(page) == before, f'CRUD in {phase} changed unrelated task/view fields'


def change_release(context, page, phase, use_old, release, expected):
    page.evaluate("""() => {
        window.upgradeControllerChanges = 0;
        navigator.serviceWorker.addEventListener('controllerchange', () => window.upgradeControllerChanges++);
    }""")
    phase['old'] = use_old
    with context.expect_event('serviceworker', timeout=20000) as started:
        page.evaluate("async () => (await navigator.serviceWorker.getRegistration()).update()")
    assert started.value.evaluate('CACHE_NAME') == release.cache_name, 'An unexpected worker was installed'
    page.wait_for_function("window.upgradeControllerChanges > 0", timeout=20000)
    assert_controller(context, page, release)
    page.reload(wait_until='load')
    assert_workspace(context, page, expected, release)


def main(archive: Path | None = None) -> None:
    old = load_baseline(archive)
    current = bundle_metadata({path:(ROOT / path).read_bytes() for path in ('index.html', 'sw.js')}, 'current working tree')
    assert old.version != current.version, 'The baseline and candidate must have distinct real versions'
    phase = {'old': True}

    class UpgradeHandler(StaticHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path.lstrip('/') or 'index.html'
            if phase['old'] and path in old.files:
                data = old.files[path]
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            super().do_GET()

        def end_headers(self) -> None:
            self.send_header('Cache-Control', 'no-cache')
            super().end_headers()

    server = ThreadingHTTPServer(('127.0.0.1', 0), UpgradeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**browser_launch_options())
            context = browser.new_context()
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url)
            wait_for_app_ready(page)
            page.wait_for_function("async () => navigator.serviceWorker.controller && (await navigator.serviceWorker.ready).active?.state === 'activated'")
            clear_app_data(page, url)
            assert app_version(page) == old.version
            assert_controller(context, page, old)
            add_task(page, 'Created before upgrade', description='字段保留 — exact Unicode migration data',
                     no_deadline=True, project='all', tags=['preserve', 'upgrade'], subtasks=['Before upgrade subtask'])
            add_task(page, 'Created outside saved project', no_deadline=True, project='Other project')
            save_view(page, 'Baseline migration view', old.typed_views)
            expected = workspace(page)
            offline_roundtrip(context, page, expected, old)
            exercise_crud(page, f'baseline {old.version}')
            print(f'Baseline verified: {old.source}; page and controlling worker are {old.version}', flush=True)

            change_release(context, page, phase, False, current, expected)
            add_task(page, 'Created after upgrade', no_deadline=True, project='all', tags=['candidate'])
            if old.typed_views:
                save_view(page, 'Candidate migration view', True, 'Created after')
            expected = workspace(page)
            if old.typed_views:
                assert len(expected['views']) == 2, 'The candidate must retain both distinct typed views'
            exercise_crud(page, f'candidate {current.version}')
            offline_roundtrip(context, page, expected, current)
            print(f'Actual {old.version} → {current.version}: fields/views, CRUD and offline reload passed', flush=True)

            change_release(context, page, phase, True, old, expected)
            add_task(page, 'Created after rollback', no_deadline=True, project='all', tags=['rollback'])
            expected = workspace(page)
            exercise_crud(page, f'rollback {old.version}')
            offline_roundtrip(context, page, expected, old)
            print(f'Actual rollback to {old.version}: fields/views, CRUD and offline reload passed', flush=True)

            change_release(context, page, phase, False, current, expected)
            exercise_crud(page, f're-upgrade {current.version}')
            offline_roundtrip(context, page, expected, current)
            assert not errors, errors
            context.close()
            browser.close()
            print(f'Actual re-upgrade to {current.version}: exact tasks/views, CRUD and offline reload passed', flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-archive', type=Path, help='Verify and use an actual earlier static ZIP instead of the default git baseline')
    main(parser.parse_args().baseline_archive)
