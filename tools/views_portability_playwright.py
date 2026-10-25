#!/usr/bin/env python3
"""Verify saved-view files migrate only views through reviewed atomic merges."""
from __future__ import annotations

import argparse
import json

from playwright.sync_api import expect, sync_playwright
from saved_views_playwright import inject_aborted_save, save_view, stored_views
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, get_task_records, local_server,
    wait_for_app_ready,
)


def checksum(payload):
    source = {key: value for key, value in payload.items() if key != 'checksum'}
    text = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    encoded = text.encode('utf-16-le', errors='surrogatepass')
    value = 2166136261
    for index in range(0, len(encoded), 2):
        value ^= encoded[index] | (encoded[index + 1] << 8)
        value = value * 16777619 & 0xffffffff
    return f'fnv1a32:{value:08x}'


def view(name, query, identity='external-view'):
    return {'id': identity, 'name': name, 'searchQuery': query, 'filter': 'active',
            'projectFilter': 'all', 'sort': 'smart', 'viewMode': 'list'}


def payload(views):
    result = {'app': 'Task Tracer', 'type': 'saved-views', 'version': '1.0',
              'date': '2026-10-23T00:00:00.000Z', 'savedViews': views}
    result['checksum'] = checksum(result)
    return result


def snapshot(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const settings = tx.objectStore('config').getAll();
            tx.oncomplete = () => {
                db.close();
                resolve({tasks: tasks.result, config: settings.result,
                    local: {...localStorage}, session: {...sessionStorage}});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def assert_only_views_changed(before, after):
    assert before['tasks'] == after['tasks'], 'View transfer changed task records'
    assert before['local'] == after['local'] and before['session'] == after['session']
    without_views = lambda records: [record for record in records if record['key'] != 'savedViews']
    assert without_views(before['config']) == without_views(after['config']), \
        'View transfer changed preferences, task revision, backup timestamp or recovery history'


def seed_views(page, views):
    page.evaluate("""views => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction('config', 'readwrite');
            tx.objectStore('config').put({key: 'savedViews', value: views});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", views)
    page.reload()
    wait_for_app_ready(page)


def open_manager(page):
    if page.locator('#taskModal').is_visible():
        page.locator('#cancelBtn').click()
    page.locator('#openMenuBtn').click()
    page.locator('#savedViewsTransferBtn').click()
    expect(page.locator('#savedViewsTransferContent')).to_be_visible()


def choose_file(page, data, filename='saved-views.json'):
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
    with page.expect_file_chooser() as info:
        page.locator('#savedViewsImportBtn').click()
    info.value.set_files({'name': filename, 'mimeType': 'application/json', 'buffer': raw})


def preview(page, data):
    open_manager(page)
    choose_file(page, data)
    expect(page.locator('#savedViewsImportPreview')).to_be_visible()


def export_views(page):
    open_manager(page)
    with page.expect_download() as result:
        page.locator('#savedViewsExportBtn').click()
    download = result.value
    assert download.suggested_filename.startswith('task-tracer-saved-views-')
    data = json.loads(download.path().read_text())
    assert set(data) == {'app', 'type', 'version', 'date', 'savedViews', 'checksum'}
    assert data['app'] == 'Task Tracer' and data['type'] == 'saved-views' and data['version'] == '1.1'
    assert data['checksum'] == checksum(data), 'View export checksum does not match actual bytes'
    return data


def assert_immediate_search_snapshot(page):
    queries = ['project:instant-search', 'tag:another-instant-search']
    for index, query in enumerate(queries):
        default_name = page.evaluate("""({query, index}) => {
            const search = document.getElementById('searchInput');
            search.value = query;
            search.dispatchEvent(new Event('input', {bubbles: true}));
            document.getElementById('saveSmartViewBtn').click();
            const name = document.getElementById('savedViewNameInput');
            const defaultName = name.value;
            name.value = `Immediate search snapshot ${index}`;
            document.getElementById('submitBtn').click();
            return defaultName;
        }""", {'query': query, 'index': index})
        expect(page.locator('#taskModal')).to_be_hidden()
        assert query in default_name, 'Saving before search debounce used an outdated default name'
        assert {item['searchQuery'] for item in stored_views(page)} == set(queries[:index + 1]), \
            'Rapid distinct saves captured stale queries or replaced an unrelated saved view'


def assert_pending_view_reads(page):
    page.evaluate("""() => {
        window.viewTestNativeFileText = File.prototype.text;
        window.pendingViewFileReads = [];
        File.prototype.text = function() {
            if (!this.name.startsWith('deferred-')) return window.viewTestNativeFileText.call(this);
            const file = this;
            return new Promise(resolve => {
                window.pendingViewFileReads.push({name: file.name, finish: () =>
                    window.viewTestNativeFileText.call(file).then(text => resolve(text))});
            });
        };
    }""")
    try:
        for newest_first in (False, True):
            open_manager(page)
            before = snapshot(page)
            page.evaluate('window.pendingViewFileReads = []')
            choose_file(page, payload([view('Older selection', 'project:older')]), 'deferred-older.json')
            page.wait_for_function('window.pendingViewFileReads.length === 1')
            choose_file(page, payload([view('Latest selection', 'project:latest')]), 'deferred-latest.json')
            page.wait_for_function('window.pendingViewFileReads.length === 2')
            if not newest_first:
                page.evaluate("window.pendingViewFileReads.find(read => read.name === 'deferred-older.json').finish()")
                page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                expect(page.locator('#savedViewsTransferContent')).to_be_visible()
                expect(page.locator('#savedViewsImportPreview')).to_have_count(0)
            page.evaluate("window.pendingViewFileReads.find(read => read.name === 'deferred-latest.json').finish()")
            expect(page.locator('#savedViewsImportPreview')).to_be_visible()
            expect(page.locator('#savedViewsImportPreview')).to_contain_text('Latest selection')
            expect(page.locator('#savedViewsImportPreview')).not_to_contain_text('Older selection')
            reviewed = page.locator('#savedViewsImportPreview').inner_text()
            if newest_first:
                page.evaluate("window.pendingViewFileReads.find(read => read.name === 'deferred-older.json').finish()")
                page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                assert page.locator('#savedViewsImportPreview').inner_text() == reviewed, \
                    'An older completed read replaced the latest reviewed view file'
            assert snapshot(page) == before, 'Pending view reads wrote data before confirmation'

        open_manager(page)
        before = snapshot(page)
        page.evaluate('window.pendingViewFileReads = []')
        choose_file(page, payload([view('Cancelled selection', 'project:cancelled')]), 'deferred-cancelled.json')
        page.wait_for_function('window.pendingViewFileReads.length === 1')
        page.keyboard.press('Escape')
        expect(page.locator('#taskModal')).to_be_hidden()
        page.locator('#openModalBtn').click()
        page.locator('#taskName').fill('Unsaved task draft while file read completes')
        page.evaluate("window.pendingViewFileReads[0].finish()")
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskName')).to_have_value('Unsaved task draft while file read completes')
        expect(page.locator('#savedViewsImportPreview')).to_have_count(0)
        assert snapshot(page) == before, 'Cancelled view read changed workspace data'
        page.locator('#cancelBtn').click()
        expect(page.locator('#draftDiscardPrompt')).to_be_visible()
        page.locator('#draftDiscardBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
    finally:
        page.evaluate('() => { File.prototype.text = window.viewTestNativeFileText; }')


def run(engine):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'View portability {engine}: {browser.version}', flush=True)
        context = browser.new_context(accept_downloads=True, locale='en-US', reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            page.locator('#openMenuBtn').click()
            page.locator('#langMenuToggle').click()
            page.locator('#lang-container .lang-btn[data-lang="en"]').click()
            expect(page.locator('html')).to_have_attribute('lang', 'en')
            page.keyboard.press('Escape')
            add_task(page, 'PRIVATE task not in a view file', no_deadline=True)
            assert_immediate_search_snapshot(page)
            print('View portability passed: immediate distinct search saves capture current queries and default names', flush=True)
            seed_views(page, [])
            page.locator('#openMenuBtn').focus()
            page.keyboard.press('Control+p')
            expect(page.locator('#commandPalette')).to_be_visible()
            page.locator('#commandPaletteInput').fill('transfer saved views')
            page.keyboard.press('Enter')
            expect(page.locator('#savedViewsTransferContent')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#openMenuBtn')).to_be_focused()
            assert_pending_view_reads(page)
            print('View portability passed: latest file intent wins both read orders; cancellation preserves task drafts', flush=True)
            other = context.new_page()
            other.goto(url)
            wait_for_app_ready(other)
            save_view(page, 'Existing Alpha', 'project:alpha')
            save_view(other, '中文 Beta', 'tag:学习')
            before = snapshot(page)
            exported = export_views(page)
            assert {item['name'] for item in exported['savedViews']} == {'Existing Alpha', '中文 Beta'}, \
                f'View export used stale data: exported={exported["savedViews"]}, stored={stored_views(page)}'
            assert 'PRIVATE task' not in json.dumps(exported)
            assert snapshot(page) == before, 'View export modified workspace state'
            preview(page, exported)
            expect(page.locator('#savedViewsImportSummary')).to_contain_text('add 0, skip 2')
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            assert snapshot(page) == before, 'Duplicate-only import wrote configuration'
            print('View portability passed: export reads latest views, Unicode/checksum round-trip, task/backup isolation', flush=True)

            existing = stored_views(page)
            incoming = payload([
                view('Existing Alpha', 'project:distinct', existing[0]['id']),
                view('Ignored duplicate name', 'project:distinct', existing[0]['id']),
                view('<img src=x onerror=alert(1)>', 'tag:新标签', existing[0]['id']) |
                {'filter': 'no-deadline', 'sort': 'alpha-asc'},
            ])
            preview(page, incoming)
            expect(page.locator('#savedViewsImportSummary')).to_contain_text('add 2, skip 1')
            expect(page.locator('#savedViewsImportPreview')).to_contain_text('No Deadline')
            expect(page.locator('#savedViewsImportPreview')).to_contain_text('Name (A-Z)')
            assert stored_views(page) == existing, 'Preview wrote view configuration'
            page.locator('#cancelBtn').click()
            assert stored_views(page) == existing, 'Cancelling import changed views'
            preview(page, incoming)
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            actual = stored_views(page)
            assert actual[:len(existing)] == existing, 'Import renamed or reordered existing views'
            assert len(actual) == 4 and len({item['id'] for item in actual}) == 4
            assert all(item['id'] not in {item['id'] for item in existing} for item in actual[len(existing):])
            assert actual[-1]['name'].startswith('<img')
            assert_only_views_changed(before, snapshot(page))
            print('View portability passed: reviewed merge, cancellation, snapshot dedupe and ID collision safety', flush=True)

            bases = [view(f'Keep {index}', f'project:keep-{index}', f'keep-{index}') for index in range(11)]
            seed_views(page, bases)
            before = snapshot(page)
            limited = payload([bases[0], view('Add first', 'project:first'),
                               view('Duplicate first', 'project:first'), view('Too many A', 'project:extra-a'),
                               view('Too many B', 'project:extra-b')])
            preview(page, limited)
            expect(page.locator('#savedViewsImportSummary')).to_contain_text('add 1, skip 2 matching views and 2 beyond')
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            actual = stored_views(page)
            assert actual[:11] == bases and len(actual) == 12 and actual[-1]['name'] == 'Add first'
            assert_only_views_changed(before, snapshot(page))
            print('View portability passed: 12-view capacity skips overflow without evicting existing views', flush=True)

            seed_views(page, [view('Stable base', 'project:base', 'stable-base')])
            other.reload()
            wait_for_app_ready(other)
            before = snapshot(page)
            stale = payload([view('Incoming one', 'project:one'), view('Incoming two', 'project:two')])
            preview(page, stale)
            save_view(other, 'Concurrent newer view', 'project:concurrent')
            latest = stored_views(other)
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#notificationText')).to_contain_text('Review the updated preview')
            assert stored_views(page) == latest, 'Stale preview committed without renewed confirmation'
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            assert stored_views(page)[:len(latest)] == latest and len(stored_views(page)) == 4
            assert_only_views_changed(before, snapshot(page))
            print('View portability passed: changed storage rebuilds preview and requires explicit second confirmation', flush=True)

            before = snapshot(page)
            preview(page, payload([view('Retry after abort', 'project:retry')]))
            inject_aborted_save(page)
            page.locator('#submitBtn').click()
            page.wait_for_function('window.abortNextSavedViewWrite === false')
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#submitBtn')).to_be_enabled()
            assert snapshot(page) == before, 'Aborted view import left partial configuration'
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            assert any(item['name'] == 'Retry after abort' for item in stored_views(page))
            assert_only_views_changed(before, snapshot(page))
            print('View portability passed: atomic abort keeps preview/data and a later retry succeeds', flush=True)

            bad_checksum = payload([view('Corrupt file', 'project:corrupt')])
            bad_checksum['savedViews'][0]['name'] = 'Changed without checksum'
            invalid_files = [bad_checksum,
                             {'version': '2.4', 'type': 'backup', 'tasks': []},
                             payload([view('Unknown filter', 'project:bad') | {'filter': 'not-a-filter'}]),
                             payload([view('Wrong query type', 'project:bad') | {'searchQuery': {'unsafe': True}}]),
                             payload([view('Too many', f'project:large-{index}') for index in range(13)]),
                             b'{not json', b' ' * (1024 * 1024 + 1)]
            for invalid in invalid_files:
                before = snapshot(page)
                open_manager(page)
                page.evaluate("document.getElementById('notification').classList.remove('show')")
                choose_file(page, invalid)
                expect(page.locator('#notification')).to_have_class('notification error show')
                expect(page.locator('#savedViewsTransferContent')).to_be_visible()
                assert snapshot(page) == before, 'Invalid view file changed workspace state'
            assert get_task_records(page) == before['tasks']
            assert not errors, errors
            print('View portability passed: corrupted/wrong-task/invalid-field/oversized files rejected without writes', flush=True)
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
