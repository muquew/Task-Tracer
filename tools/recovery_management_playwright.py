#!/usr/bin/env python3
"""Review/export historical tasks and explicitly clear only reviewed recovery points."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

from recovery_playwright import open_recovery
from smoke_playwright import (
    add_task, assert_backup_payload_integrity, browser_launch_options, clear_app_data,
    delete_task, get_task_records, local_server, wait_for_app_ready,
)


def stored(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => {db.close(); resolve({tasks:tasks.result, config:config.result});};
            tx.onabort = () => reject(tx.error);
        };
    })""")


def config(snapshot):
    return {entry['key']: entry['value'] for entry in snapshot['config']}


def prepare(page, url):
    clear_app_data(page, url)
    add_task(page, 'Current task remains unchanged', no_deadline=True)
    page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const tasks = tx.objectStore('tasks').getAll();
            const revision = tx.objectStore('config').get('taskRevision');
            tasks.onsuccess = () => {
                const template = tasks.result[0];
                const historical = Array.from({length:235}, (_, index) => ({...template,
                    id:10000+index, name:index === 0 ? 'Historical <img src=x onerror=window.recoveryPreviewXss=true>' : `Historical task ${String(index).padStart(3,'0')}`,
                    description:`Deleted private historical content ${index}`,
                    completed:index % 3 === 0, archived:index % 5 === 0,
                    completedAt:index % 3 === 0 ? '2026-01-01T00:00:00.000Z' : null,
                    archivedAt:index % 5 === 0 ? '2026-01-02T00:00:00.000Z' : null,
                    project:`Historical project ${index % 4}`, tags:['history'],
                    subtasks:[{id:20000+index,text:`Historical subtask ${index}`,completed:false}]
                }));
                historical[1].name = 'Long historical name ' + 'A'.repeat(400);
                const store = tx.objectStore('config');
                store.put({key:'recoveryHistory',value:[
                    {id:'history-large',createdAt:'2026-02-01T00:00:00.000Z',tasks:historical},
                    {id:'history-small',createdAt:'2026-02-01T00:00:00.000Z',tasks:[
                        {...historical[233],completed:'false',archived:'false'},
                        {...historical[234],completed:'true',archived:'false'}
                    ]},
                    {id:'history-empty',createdAt:'2026-01-01T00:00:00.000Z',tasks:[]}
                ]});
                store.put({key:'recoveryReviewPreference',value:{private:'unchanged preference'}});
                const date = new Date().toISOString();
                store.put({key:'lastBackupAt',value:date});
                revision.onsuccess = () => store.put({key:'lastTaskBackup',value:{date,taskRevision:revision.result.value}});
            };
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""")
    return stored(page)


def change_point(page, value):
    page.locator('#recoverySelect').select_option(value, force=True)


def assert_focused_preview_row_visible(row):
    assert row.evaluate("""node => {
        const item = node.getBoundingClientRect();
        const list = node.parentElement.getBoundingClientRect();
        return item.top >= list.top - 1 && item.bottom <= list.bottom + 1
            && item.top >= 0 && item.bottom <= window.innerHeight;
    }"""), 'Keyboard focus moved to a historical task outside the visible preview scroll area'


def preview_and_export(page, url, browser):
    before = prepare(page, url)
    page.set_viewport_size({'width':390,'height':844})
    downloads = []
    page.on('download', lambda download: downloads.append(download))
    open_recovery(page)
    expect(page.locator('#recoveryPrivacy')).to_be_visible()
    rows = page.locator('#recoveryTaskPreview > li')
    expect(rows).to_have_count(100)
    language = page.locator('html').get_attribute('lang')
    translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
    expect(page.locator('#recoveryPreviewSummary')).to_have_text(
        translations['recovery']['previewSummary'].format(shown=100,count=235,completed=79,archived=47))
    expect(rows.first).to_contain_text('Historical <img src=x onerror=window.recoveryPreviewXss=true>')
    assert not page.evaluate('Boolean(window.recoveryPreviewXss)')
    assert page.locator('#recoveryTaskPreview img').count() == 0
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Long historical task names overflow the mobile viewport'
    page.locator('#recoveryPreviewMore').click()
    expect(rows).to_have_count(200)
    expect(rows.nth(100)).to_be_focused()
    assert_focused_preview_row_visible(rows.nth(100))
    page.locator('#recoveryPreviewMore').click()
    expect(rows).to_have_count(235)
    expect(rows.nth(200)).to_be_focused()
    assert_focused_preview_row_visible(rows.nth(200))
    expect(page.locator('#recoveryPreviewMore')).to_be_hidden()
    page.locator('#recoveryConfirm').check()
    change_point(page, 'history-small')
    expect(rows).to_have_count(2)
    expect(rows.first).to_contain_text('Historical task 233')
    expect(rows.first).to_contain_text(translations['filters']['active'])
    expect(rows.last).to_contain_text(translations['filters']['completed'])
    expect(page.locator('#recoveryPreviewSummary')).to_have_text(
        translations['recovery']['previewSummary'].format(shown=2,count=2,completed=1,archived=0))
    expect(page.locator('#recoveryConfirm')).not_to_be_checked()
    change_point(page, 'history-large')
    expect(rows).to_have_count(100)
    expect(page.locator('#recoveryPreviewMore')).to_be_visible()
    assert stored(page) == before and not downloads, 'Reviewing historical tasks wrote data or automatically downloaded them'
    with page.expect_download() as result:
        page.locator('#recoveryExportBtn').click()
    download = result.value
    assert download.suggested_filename.startswith('task-tracer_recovery-backup_')
    payload = json.loads(download.path().read_text())
    assert_backup_payload_integrity(payload, 'backup')
    assert payload['version'] == '2.4'
    assert payload['tasks'] == config(before)['recoveryHistory'][0]['tasks']
    assert stored(page) == before, 'Historical export changed tasks, history, preferences, revision or current-task backup metadata'
    expect(page.locator('#taskModal')).to_be_visible()
    change_point(page, 'history-empty')
    expect(rows).to_have_count(0)
    expect(page.locator('#recoveryPreviewEmpty')).to_be_visible()
    with page.expect_download() as empty_result:
        page.locator('#recoveryExportBtn').click()
    empty = json.loads(empty_result.value.path().read_text())
    assert_backup_payload_integrity(empty, 'backup')
    assert empty['tasks'] == [] and stored(page) == before
    page.locator('#cancelBtn').click()

    target_context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
    try:
        target = target_context.new_page()
        clear_app_data(target, url)
        open_settings(target)
        with target.expect_file_chooser() as chooser:
            target.locator('#importBtn').click()
        chooser.value.set_files({'name':download.suggested_filename,'mimeType':'application/json',
                                'buffer':json.dumps(payload).encode()})
        expect(target.locator('#mergeImportMode')).to_be_visible()
        target.locator('#submitBtn').click()
        expect(target.locator('#taskModal')).to_be_hidden()
        assert get_task_records(target) == payload['tasks'], 'Historical export cannot restore the same task fields in a clean browser profile'
    finally:
        target_context.close()
    print('Recovery management passed: bounded safe preview, reset/focus, read-only historical/empty exports and actual import round trip', flush=True)


def clear_only_history(page, url, _browser):
    before = prepare(page, url)
    undo_enabled = page.locator('#undoBtn').is_enabled()
    open_recovery(page)
    page.locator('#recoveryClearBtn').click()
    expect(page.locator('#recoveryClearConfirm')).to_be_visible()
    assert stored(page) == before
    page.locator('#cancelBtn').click()
    assert stored(page) == before, 'Cancelling history cleanup changed data'
    open_recovery(page)
    page.locator('#recoveryClearBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = stored(page)
    assert after['tasks'] == before['tasks']
    expected = config(before)
    expected.pop('recoveryHistory')
    assert config(after) == expected, 'History cleanup changed non-history configuration or task revision'
    assert page.locator('#undoBtn').is_enabled() == undo_enabled
    add_task(page, 'New task after intentional history cleanup', no_deadline=True)
    continued = stored(page)
    assert len(continued['tasks']) == 2
    assert config(continued)['taskRevision'] == config(before)['taskRevision'] + 1
    assert len(config(continued)['recoveryHistory']) == 1
    assert config(continued)['recoveryHistory'][0]['tasks'] == before['tasks']
    print('Recovery management passed: explicit/cancellable cleanup removes only history and later writes retain fresh recovery protection', flush=True)


def concurrent_history(page, url, _browser):
    prepare(page, url)
    open_recovery(page)
    page.locator('#recoveryClearBtn').click()
    second = page.context.new_page()
    try:
        second.goto(url)
        wait_for_app_ready(second)
        add_task(second, 'Remote task with an unseen recovery point', no_deadline=True)
        delete_task(second, 'Remote task with an unseen recovery point')
        expected = stored(second)
        expected_count = len(config(expected)['recoveryHistory'])
        assert expected_count > 3
        page.locator('#submitBtn').click()
        expect(page.locator('#recoverySelect option')).to_have_count(expected_count)
        expect(page.locator('#recoveryClearBtn')).to_be_visible()
        assert stored(page) == expected, 'A stale cleanup confirmation erased an unseen recovery point'
        page.locator('#recoveryClearBtn').click()
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        actual = stored(page)
        expected_config = config(expected)
        expected_config.pop('recoveryHistory')
        assert actual['tasks'] == expected['tasks'] and config(actual) == expected_config
    finally:
        second.close()
    print('Recovery management passed: changed history requires a fresh review before cleanup', flush=True)


def aborted_clear(page, url, _browser):
    before = prepare(page, url)
    open_recovery(page)
    page.locator('#recoveryClearBtn').click()
    page.evaluate("""() => {
        const nativeDelete = IDBObjectStore.prototype.delete;
        IDBObjectStore.prototype.delete = function(key) {
            const request = nativeDelete.call(this, key);
            if (this.name === 'config' && key === 'recoveryHistory') {
                IDBObjectStore.prototype.delete = nativeDelete;
                window.recoveryCleanupAborted = true;
                this.transaction.abort();
            }
            return request;
        };
    }""")
    page.locator('#submitBtn').click()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    assert page.evaluate('window.recoveryCleanupAborted === true')
    assert stored(page) == before, 'An aborted cleanup changed historical/current tasks or metadata'
    print('Recovery management passed: aborted history cleanup rolls back without data loss', flush=True)


def old_clear_preserves_draft(page, url, _browser):
    before = prepare(page, url)
    open_recovery(page)
    page.locator('#recoveryClearBtn').click()
    page.evaluate("""() => {
        const nativeDelete = IDBObjectStore.prototype.delete;
        IDBObjectStore.prototype.delete = function(key) {
            const request = nativeDelete.call(this, key);
            if (this.name === 'config' && key === 'recoveryHistory') {
                IDBObjectStore.prototype.delete = nativeDelete;
                const tx = this.transaction;
                const complete = tx.oncomplete;
                tx.oncomplete = null;
                tx.addEventListener('complete', event => {
                    window.finishRecoveryCleanup = () => complete.call(tx, event);
                }, {once:true});
            }
            return request;
        };
    }""")
    page.locator('#submitBtn').click()
    page.wait_for_function('typeof window.finishRecoveryCleanup === "function"')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#settingsWorkspace')).to_be_visible()
    return_to_task_workspace(page)
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Later task draft after cleanup')
    page.locator('#taskDesc').fill('Keep this raw unsaved text')
    page.evaluate('window.finishRecoveryCleanup()')
    page.evaluate('() => new Promise(requestAnimationFrame)')
    expect(page.locator('#taskName')).to_have_value('Later task draft after cleanup')
    expect(page.locator('#taskDesc')).to_have_value('Keep this raw unsaved text')
    expect(page.locator('#submitBtn')).to_be_enabled()
    after = stored(page)
    expected_config = config(before)
    expected_config.pop('recoveryHistory')
    assert after['tasks'] == before['tasks'] and config(after) == expected_config
    print('Recovery management passed: completed old cleanup cannot close or alter a later task draft', flush=True)


CASES = {'preview':preview_and_export, 'clear':clear_only_history, 'concurrent':concurrent_history,
         'abort':aborted_clear, 'session':old_clear_preserves_draft}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium','firefox','webkit'], default='chromium')
    parser.add_argument('--case', choices=['all',*CASES], default='all')
    args = parser.parse_args()
    expect.set_options(timeout=10000)
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if args.browser == 'chromium' else {'headless':True}
        browser = getattr(p,args.browser).launch(**options)
        try:
            selected = CASES.items() if args.case == 'all' else [(args.case,CASES[args.case])]
            for name, operation in selected:
                context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
                errors = []
                try:
                    page = context.new_page()
                    page.on('pageerror', lambda error:errors.append(str(error)))
                    operation(page,url,browser)
                    assert not errors, (name,errors)
                finally:
                    context.close()
        finally:
            browser.close()
    print(f'{args.browser}: recovery management checks passed', flush=True)


if __name__ == '__main__':
    main()
