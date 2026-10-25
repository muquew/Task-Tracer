#!/usr/bin/env python3
"""Protect reviewed import approvals from a background refresh after remote edits."""
from __future__ import annotations

import json
from datetime import datetime
from playwright.sync_api import expect, sync_playwright
from reminder_concurrency_playwright import seed
from smoke_playwright import (add_task, browser_launch_options, clear_app_data,
                              complete_task, get_task_records, local_server, select_filter, task_locator,
                              wait_for_app_ready)


def open_import(page, tasks):
    page.locator('#openMenuBtn').click()
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'synthetic-import.json', 'mimeType': 'application/json',
                            'buffer': json.dumps(tasks).encode()})
    expect(page.locator('#mergeImportMode')).to_be_visible()


def prepare_reminder_context(browser, url, name, completed_name=None):
    context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
    first = context.new_page()
    errors = []
    first.on('pageerror', lambda error: errors.append(str(error)))
    clear_app_data(first, url)
    if completed_name:
        add_task(first, completed_name, no_deadline=True)
        complete_task(first, completed_name)
    first.evaluate('async () => { await navigator.serviceWorker.ready; }')
    first.add_init_script("""(() => {
        Object.defineProperty(Notification, 'permission', {get:()=>'granted', configurable:true});
        ServiceWorkerRegistration.prototype.showNotification = function() {
            return new Promise(resolve => { window.finishDelayedReminder = resolve; });
        };
    })();""")
    seed(first, name)
    first.reload()
    wait_for_app_ready(first)
    first.wait_for_function('typeof window.finishDelayedReminder === "function"')
    return context, first, errors


def assert_reminder_metadata_only(page, before, reminder_name, delivery_started):
    after = get_task_records(page)
    previous = {task['id']: task for task in before}
    current = {task['id']: task for task in after}
    assert len(after) == len(before) and set(current) == set(previous), \
        'Reminder delivery added or removed task records'
    pending = [task for task in before if task['name'] == reminder_name]
    assert len(pending) == 1, 'The pending reminder fixture must identify exactly one task'
    reminder_id = pending[0]['id']
    metadata = {'lastReminderAt', 'snoozedUntil'}
    for task_id, old in previous.items():
        task = current[task_id]
        if task_id != reminder_id:
            assert task == old, 'Reminder delivery changed an unrelated task'
            continue
        assert {key: value for key, value in task.items() if key not in metadata} == \
               {key: value for key, value in old.items() if key not in metadata}, \
            'Reminder delivery overwrote task content or another non-reminder field'
        assert task.get('snoozedUntil') is None, 'Delivered reminder did not clear its prior snooze'
        delivered = task.get('lastReminderAt')
        assert isinstance(delivered, str) and delivered != old.get('lastReminderAt'), \
            'The pending reminder did not persist a new delivery timestamp'
        timestamp = datetime.fromisoformat(delivered.replace('Z', '+00:00'))
        assert timestamp.tzinfo is not None, 'Reminder delivery timestamp must include its timezone'
        delivered_ms = round(timestamp.timestamp() * 1000)
        observed_ms = page.evaluate('Date.now()')
        assert delivery_started <= delivered_ms <= observed_ms, \
            'Reminder delivery timestamp is outside the actual completion interval'
    return after


def run_case(browser, url, mode):
    name = f'Import reviewed {mode}'
    context, first, errors = prepare_reminder_context(browser, url, name)
    try:
        imported = [{'id': 987654321, 'name': name if mode == 'merge' else 'Replacement task',
                     'description': 'Imported description', 'dueDate': None, 'completed': False}]
        open_import(first, imported)
        if mode == 'replace':
            with first.expect_download() as download:
                first.locator('#submitBtn').click()
            snapshot = json.loads(download.value.path().read_text())
            assert len(snapshot['tasks']) == 1
            expect(first.locator('#taskModal')).to_be_visible()
        else:
            first.locator('#mergeImportMode').check()
            first.locator('#import-conflict-0').select_option('replace')

        second = context.new_page()
        second.goto(url)
        wait_for_app_ready(second)
        if mode == 'replace':
            remote = 'Created after import approval'
            add_task(second, remote, no_deadline=True)
        else:
            remote = 'Description changed after import approval'
            task_locator(second, name).locator('[data-action="edit"]').click()
            second.locator('#taskDesc').fill(remote)
            second.locator('#submitBtn').click()
            expect(second.locator('#taskModal')).to_be_hidden()
        expected = get_task_records(second)
        delivery_started = first.evaluate('Date.now()')
        first.evaluate('window.finishDelayedReminder()')
        # Atomic reminder metadata completion explicitly refreshes the latest task
        # records while the import modal is still open.
        if mode == 'replace':
            expect(task_locator(first, remote)).to_have_count(1)
        else:
            expect(task_locator(first, name).locator('.task-desc')).to_contain_text(remote)
        expected = assert_reminder_metadata_only(first, expected, name, delivery_started)
        if first.locator('#taskModal').is_visible():
            first.locator('#submitBtn').click()
            expect(first.locator('#submitBtn')).to_be_enabled()
        assert get_task_records(first) == expected, \
            f'Stale {mode} import approvals overwrote newer tasks after a background refresh'
        expect(first.locator('#taskModal')).to_be_visible()
        expect(first.locator('#mergeImportMode')).not_to_be_checked()
        if mode == 'replace':
            with first.expect_download() as new_download:
                first.locator('#submitBtn').click()
            fresh_snapshot = json.loads(new_download.value.path().read_text())
            assert fresh_snapshot['tasks'] == expected, 'Fresh approval did not back up the latest task data'
            assert get_task_records(first) == expected, 'Snapshot download prematurely applied the import'
        else:
            first.locator('#mergeImportMode').check()
            first.locator('#import-conflict-0').select_option('replace')
        first.locator('#submitBtn').click()
        expect(first.locator('#taskModal')).to_be_hidden()
        imported_records = get_task_records(first)
        assert len(imported_records) == 1 and imported_records[0]['description'] == 'Imported description', \
            'A fresh explicit approval could not complete the preserved import file'
        first.locator('#undoBtn').click()
        expect(first.locator('#undoBtn')).to_be_disabled()
        assert get_task_records(first) == expected, 'Undo lost newer data after a freshly reviewed import'
        assert not errors, errors
        print(f'Import preview concurrency passed: stale {mode} approval preserves remote changes after background refresh', flush=True)
    finally:
        context.close()



def run_confirmation_case(browser, url, action):
    completed_name = f'Completed task awaiting {action}' if action != 'recovery' else None
    reminder_name = f'Reminder during {action}'
    context, first, errors = prepare_reminder_context(browser, url, reminder_name, completed_name)
    try:
        if action == 'recovery':
            # Seed a real checkpoint after startup without changing the pending reminder.
            first.evaluate("""() => new Promise((resolve, reject) => {
                const open = indexedDB.open('TaskTrackerDB', 2);
                open.onsuccess = () => {
                    const db = open.result;
                    const tx = db.transaction('config','readwrite');
                    tx.objectStore('config').put({key:'recoveryHistory',value:[{
                        id:'reviewed-empty-point',createdAt:new Date().toISOString(),tasks:[]
                    }]});
                    tx.oncomplete = () => {db.close();resolve();};
                    tx.onabort = () => reject(tx.error);
                };
                open.onerror = () => reject(open.error);
            })""")
        first.locator('#openMenuBtn').click()
        first.locator({'clear': '#clearCompletedBtn', 'archive': '#archiveCompletedBtn',
                       'recovery': '#recoveryBtn'}[action]).click()
        expect(first.locator('#taskModal')).to_be_visible()
        if action == 'recovery': first.locator('#recoveryConfirm').check()
        second = context.new_page()
        second.goto(url)
        wait_for_app_ready(second)
        if completed_name:
            select_filter(second, 'all')
            task_locator(second, completed_name).locator('[data-action="toggle"]').click()
            assert next(task for task in get_task_records(second) if task['name'] == completed_name)['completed'] is False
            remote = completed_name
        else:
            remote = 'Task created after recovery review'
            add_task(second, remote, no_deadline=True)
        expected = get_task_records(second)
        delivery_started = first.evaluate('Date.now()')
        first.evaluate('window.finishDelayedReminder()')
        expect(task_locator(first, remote)).to_have_count(1)
        expected = assert_reminder_metadata_only(first, expected, reminder_name, delivery_started)
        if first.locator('#taskModal').is_visible():
            first.locator('#submitBtn').click()
            expect(first.locator('#submitBtn')).to_be_enabled()
        assert get_task_records(first) == expected, \
            f'Stale {action} confirmation changed newer tasks after a background refresh'
        assert not errors, errors
        print(f'Destructive confirmation passed: stale {action} preserves remote changes after background refresh', flush=True)
    finally:
        context.close()


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        try:
            for mode in ('replace', 'merge'):
                run_case(browser, url, mode)
            for action in ('clear', 'archive', 'recovery'):
                run_confirmation_case(browser, url, action)
        finally:
            browser.close()


if __name__ == '__main__':
    run()
