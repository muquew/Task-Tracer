#!/usr/bin/env python3
"""Verify task-backup coverage follows the downloaded snapshot rather than age alone."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace

import argparse
import contextlib
import http.server
import json
from pathlib import Path
import re
import tempfile
import threading
import zipfile

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    ThreadingHTTPServer, add_task, browser_launch_options, clear_app_data, delete_task,
    edit_task, get_task_records, local_server, wait_for_app_ready,
)

ROOT = Path(__file__).resolve().parents[1]
DUE = re.compile(r'\bbackup-due\b')


@contextlib.contextmanager
def candidate_server(baseline_archive=None):
    if baseline_archive is None:
        with local_server() as url:
            yield url
        return
    with tempfile.TemporaryDirectory(prefix='task-tracer-backup-baseline-') as directory:
        root = Path(directory)
        with zipfile.ZipFile(baseline_archive) as archive:
            for name in archive.namelist():
                if not (root / name).resolve().is_relative_to(root.resolve()):
                    raise AssertionError(f'Unsafe archive path: {name}')
            archive.extractall(root)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root), **kwargs)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/'
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def stored_state(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => {
                const settings = Object.fromEntries(config.result.map(record => [record.key, record.value]));
                db.close();
                resolve({tasks: tasks.result, taskRevision: settings.taskRevision || 0,
                    lastBackupAt: settings.lastBackupAt || null, lastTaskBackup: settings.lastTaskBackup || null});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def set_backup_metadata(page, date, record):
    page.evaluate("""({date, record}) => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction('config', 'readwrite');
            const store = tx.objectStore('config');
            store.put({key: 'lastBackupAt', value: date});
            if (record === null) store.delete('lastTaskBackup');
            else store.put({key: 'lastTaskBackup', value: record});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", {'date': date, 'record': record})


def open_menu(page):
    open_settings(page)
    expect(page.locator('#backupHealthText')).to_be_visible()


def assert_health(page, *, due, message_key=None):
    open_menu(page)
    if due:
        expect(page.locator('#backupHealth')).to_have_class(DUE)
    else:
        expect(page.locator('#backupHealth')).not_to_have_class(DUE)
    if message_key:
        language = page.locator('html').get_attribute('lang')
        translations = json.loads((ROOT / 'resources' / f'{language}.json').read_text())
        text = translations['backup']['health'][message_key]
        prefix = text.split('{age}')[0]
        if prefix:
            expect(page.locator('#backupHealthText')).to_contain_text(prefix)
    page.keyboard.press('Escape')


def backup(page):
    open_menu(page)
    with page.expect_download() as info:
        page.locator('#backupBtn').click()
    data = json.loads(info.value.path().read_text())
    if page.locator('#settingsWorkspace').count():
        expect(page.locator('#settingsWorkspace')).to_be_visible()
    assert stored_state(page)['lastBackupAt'] == data['date'], 'Backup timestamp did not match the downloaded file'
    return data


def assert_edit_delete_undo_coverage(page):
    name = 'Backup freshness task'
    add_task(page, name, no_deadline=True)
    original = stored_state(page)
    first = backup(page)
    assert first['tasks'] == original['tasks']
    assert_health(page, due=False)
    edit_task(page, name, name + ' edited')
    assert_health(page, due=True, message_key='changed')
    record = stored_state(page)['lastTaskBackup']
    assert record == {'date': first['date'], 'taskRevision': original['taskRevision']}, \
        'Backup coverage did not retain the revision of the downloaded snapshot'
    backup(page)
    assert_health(page, due=False)
    delete_task(page, name + ' edited')
    assert get_task_records(page) == []
    assert_health(page, due=True, message_key='changed')
    empty_backup = backup(page)
    assert empty_backup['tasks'] == [], 'An intentionally empty workspace was not exported faithfully'
    assert_health(page, due=False)
    page.locator('#undoBtn').click()
    expect(page.locator('.task-item')).to_have_count(1)
    assert_health(page, due=True, message_key='changed')
    backup(page)
    assert_health(page, due=False)
    print('Backup coverage passed: edit, deletion to empty and Undo stay due until a new task backup', flush=True)


def assert_nonbackup_exports(page):
    edit_task(page, 'Backup freshness task edited', 'Backup freshness task edited again')
    before = stored_state(page)
    open_menu(page)
    with page.expect_download() as csv_info:
        page.locator('#exportCsvBtn').click()
    assert csv_info.value.suggested_filename.endswith('.csv')
    assert stored_state(page) == before, 'CSV export was recorded as a task backup'
    assert_health(page, due=True, message_key='changed')
    open_menu(page)
    page.locator('#savedViewsTransferBtn').click()
    with page.expect_download() as views_info:
        page.locator('#savedViewsExportBtn').click()
    assert json.loads(views_info.value.path().read_text())['type'] == 'saved-views'
    if page.locator('#settingsWorkspace').count():
        expect(page.locator('#cancelBtn')).to_be_hidden()
        page.locator('#submitBtn').click()
    else:
        page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert stored_state(page) == before, 'View export was recorded as a task backup'
    assert_health(page, due=True, message_key='changed')
    print('Backup coverage passed: CSV and saved-view exports do not reset task-backup coverage', flush=True)


def assert_legacy_coverage(page):
    before = stored_state(page)
    legacy_date = page.evaluate('new Date().toISOString()')
    set_backup_metadata(page, legacy_date, None)
    page.reload()
    wait_for_app_ready(page)
    assert_health(page, due=True, message_key='coverageUnknown')
    assert get_task_records(page) == before['tasks']
    backup(page)
    assert_health(page, due=False)
    paired = stored_state(page)
    later_date = page.evaluate('new Date().toISOString()')
    assert later_date != paired['lastBackupAt']
    set_backup_metadata(page, later_date, paired['lastTaskBackup'])
    assert_health(page, due=True, message_key='coverageUnknown')
    backup(page)
    assert_health(page, due=False)
    print('Backup coverage passed: legacy timestamps and mismatched date/revision records cannot claim current coverage', flush=True)


def assert_cross_window_coverage(page, other, url):
    backup(page)
    assert_health(page, due=False)
    visible_before = page.locator('.task-item').count()
    other.goto(url)
    wait_for_app_ready(other)
    add_task(other, 'New task in another window', no_deadline=True)
    assert page.locator('.task-item').count() == visible_before, 'Fixture unexpectedly refreshed the original task view'
    assert_health(page, due=True, message_key='changed')
    latest = stored_state(other)
    data = backup(page)
    assert data['tasks'] == latest['tasks'], 'Backup from a stale tab omitted a newer stored task'
    assert stored_state(page)['lastTaskBackup'] == {'date': data['date'], 'taskRevision': latest['taskRevision']}
    assert_health(page, due=False)
    print('Backup coverage passed: stale-window menu reads current storage, and its export includes the latest task snapshot', flush=True)


def assert_download_race(page, other):
    before = stored_state(page)
    dialogs = []
    handler = lambda dialog: dialogs.append(dialog)
    page.on('dialog', handler)
    page.evaluate("""() => {
        window.backupTestNativeAnchorClick = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function(...args) {
            const result = window.backupTestNativeAnchorClick.apply(this, args);
            if (this.download.includes('_backup_')) alert('Synthetic pause after the real task backup download starts');
            return result;
        };
    }""")
    held = None
    try:
        open_menu(page)
        with page.expect_download() as info:
            with page.expect_event('dialog') as paused:
                page.locator('#backupBtn').click()
            held = paused.value
            assert held.message.startswith('Synthetic pause')
            add_task(other, 'Changed during backup download', no_deadline=True)
            after_change = stored_state(other)
            assert after_change['taskRevision'] > before['taskRevision']
            held.accept()
            held = None
        data = json.loads(info.value.path().read_text())
        if page.locator('#settingsWorkspace').count():
            expect(page.locator('#settingsWorkspace')).to_be_visible()
        assert data['tasks'] == before['tasks'], 'Race fixture did not preserve the earlier downloaded task snapshot'
        actual = stored_state(page)
        assert actual['tasks'] == after_change['tasks'], 'Backup overwrote a concurrent task mutation'
        assert actual['lastTaskBackup'] == {'date': data['date'], 'taskRevision': before['taskRevision']}, \
            'Backup recorded a newer revision than the tasks actually downloaded'
        assert_health(page, due=True, message_key='changed')
        print('Backup coverage passed: a real download paused across another window write records only its captured revision', flush=True)
    finally:
        if held:
            held.dismiss()
        page.remove_listener('dialog', handler)
        page.evaluate('() => { HTMLAnchorElement.prototype.click = window.backupTestNativeAnchorClick; }')


def assert_metadata_failure(page, mode):
    before = stored_state(page)
    assert before['lastTaskBackup']['taskRevision'] != before['taskRevision'], 'Metadata failure fixture must start with unexported changes'
    page.evaluate("""mode => {
        const put = IDBObjectStore.prototype.put;
        window.backupMetadataFailurePending = true;
        IDBObjectStore.prototype.put = function(value, ...args) {
            if (this.name === 'config' && value?.key === 'lastTaskBackup' && window.backupMetadataFailurePending) {
                window.backupMetadataFailurePending = false;
                if (mode === 'quota') throw new DOMException('Synthetic backup metadata quota failure', 'QuotaExceededError');
                const result = put.call(this, value, ...args);
                this.transaction.abort();
                return result;
            }
            return put.call(this, value, ...args);
        };
    }""", mode)
    open_menu(page)
    with page.expect_download() as info:
        page.locator('#backupBtn').click()
    data = json.loads(info.value.path().read_text())
    page.wait_for_function('window.backupMetadataFailurePending === false')
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b.*\bshow\b'))
    assert data['tasks'] == before['tasks'], 'Metadata failure prevented the already-triggered backup from containing current tasks'
    assert stored_state(page) == before, 'Failed metadata transaction left a timestamp, revision or partial task change'
    if page.locator('#storageUnavailableBanner').is_visible():
        if page.locator('#settingsWorkspace').count():
            expect(page.locator('#openMenuBtn')).to_be_enabled()
            expect(page.locator('#backupBtn')).to_be_disabled()
        else:
            expect(page.locator('#openMenuBtn')).to_be_disabled()
    else:
        assert_health(page, due=True, message_key='changed')
    print(f'Backup coverage passed: {mode} metadata failure rolls back both coverage fields after a real download', flush=True)


def run(engine, baseline_archive=None):
    with candidate_server(baseline_archive) as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'Backup freshness {engine}: {browser.version}', flush=True)
        context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            assert_edit_delete_undo_coverage(page)
            assert_nonbackup_exports(page)
            assert_legacy_coverage(page)
            other = context.new_page()
            assert_cross_window_coverage(page, other, url)
            assert_download_race(page, other)
            assert_metadata_failure(page, 'abort')
            page.reload()
            wait_for_app_ready(page)
            assert_metadata_failure(page, 'quota')
            assert not errors, errors
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--baseline-archive', type=Path, help='Serve an extracted local release artifact to reproduce the old defect')
    args = parser.parse_args()
    run(args.browser, args.baseline_archive)
