#!/usr/bin/env python3
"""Delay notification delivery while another window edits/deletes/snoozes a task."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect, sync_playwright
from smoke_playwright import click_task_action
from smoke_playwright import (browser_launch_options, clear_app_data, delete_task,
                              due_fields_from_now, edit_task, get_task_records,
                              iso_minutes_from_now, local_server, snooze_task_reminder,
                              task_locator, wait_for_app_ready)


def seed(page, name):
    task = {'id': 123456, 'name': name, 'description': 'Original description',
            **due_fields_from_now(-1), 'reminderOffset': 15, 'reminderRepeat': -1,
            'snoozedUntil': None, 'lastReminderAt': None, 'repeatType': 'none',
            'repeatInterval': 1, 'repeatWeekdays': [], 'repeatPaused': False,
            'subtasks': [], 'completed': False, 'completedAt': None,
            'archived': False, 'archivedAt': None, 'createdAt': iso_minutes_from_now(-120), 'order': 100}
    page.evaluate("""task => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            tx.objectStore('tasks').put(task);
            tx.objectStore('config').put({key:'notifications_enabled',value:true});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
        open.onerror = () => reject(open.error);
    })""", task)


def snapshot(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const revision = tx.objectStore('config').get('taskRevision');
            tx.oncomplete = () => {
                db.close();
                resolve({tasks: tasks.result, revision: revision.result?.value || 0});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        for action in ('edit', 'delete', 'snooze', 'abort', 'quota'):
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            diagnostics = []
            page.on('console', lambda message: diagnostics.append(f'{message.type}: {message.text}'))
            page.on('pageerror', lambda error: diagnostics.append(f'pageerror: {error}'))
            clear_app_data(page, url)
            page.evaluate("async () => { await navigator.serviceWorker.ready; }")
            page.add_init_script("""(() => {
                window.reminderWriteCount = 0;
                window.reminderTransactions = [];
                const transaction = IDBDatabase.prototype.transaction;
                IDBDatabase.prototype.transaction = function(stores, mode, ...rest) {
                    const tx = transaction.call(this, stores, mode, ...rest);
                    const names = typeof stores === 'string' ? [stores] : Array.from(stores);
                    if (mode === 'readwrite' && names.includes('tasks')) {
                        const record = {stores: names, status: 'pending'};
                        window.reminderTransactions.push(record);
                        tx.addEventListener('complete', () => { window.reminderWriteCount++; });
                        tx.addEventListener('complete', () => { record.status = 'complete'; });
                        tx.addEventListener('abort', () => {
                            record.status = 'abort';
                            record.error = tx.error?.name || null;
                        });
                    }
                    return tx;
                };
                Object.defineProperty(Notification, 'permission', {get:()=>'granted', configurable:true});
                ServiceWorkerRegistration.prototype.showNotification = function() {
                    window.delayedReminderStarted = true;
                    return new Promise(resolve => {window.finishDelayedReminder = resolve;});
                };
            })();""")
            name = f'Delayed reminder {action}'
            seed(page, name)
            page.reload()
            wait_for_app_ready(page)
            page.wait_for_function('typeof window.finishDelayedReminder === "function"')
            changed_name = name + ' edited elsewhere'
            if action in ('edit', 'delete', 'snooze'):
                other = context.new_page()
                other.goto(url)
                wait_for_app_ready(other)
                if action == 'edit': edit_task(other, name, changed_name)
                elif action == 'delete': delete_task(other, name)
                else: snooze_task_reminder(other, name)
            expected = snapshot(page)
            open_settings(page)
            with page.expect_download(): page.locator('#exportCsvBtn').click()
            if action in ('abort', 'quota'):
                page.evaluate("""mode => {
                    const put = IDBObjectStore.prototype.put;
                    IDBObjectStore.prototype.put = function(value, ...args) {
                        if (this.name === 'config' && value?.key === 'taskRevision') {
                            window.reminderMetadataFailureInjected = true;
                            if (mode === 'quota') throw new DOMException('Synthetic reminder quota failure', 'QuotaExceededError');
                            const request = put.call(this, value, ...args);
                            this.transaction.abort();
                            return request;
                        }
                        return put.call(this, value, ...args);
                    };
                }""", action)
            writes = page.evaluate('window.reminderWriteCount')
            page.evaluate('window.finishDelayedReminder()')
            try:
                if action in ('abort', 'quota'):
                    page.wait_for_function("window.reminderTransactions.some(tx => tx.status === 'abort')")
                else:
                    page.wait_for_function('before => window.reminderWriteCount > before', arg=writes)
            except PlaywrightTimeoutError:
                print(f'Reminder {action} diagnostics: {diagnostics}', flush=True)
                print(f'Reminder transactions: {page.evaluate("window.reminderTransactions")}', flush=True)
                print(f'Expected task records: {expected}', flush=True)
                print(f'Actual task records: {get_task_records(page)}', flush=True)
                raise
            actual = snapshot(page)
            if action == 'edit':
                assert len(actual['tasks']) == 1 and actual['tasks'][0]['name'] == changed_name, 'Delayed reminder overwrote a newer task edit'
                assert actual['tasks'][0]['lastReminderAt'], 'Delivered reminder was not recorded on the latest task'
                assert {key: value for key, value in actual['tasks'][0].items() if key != 'lastReminderAt'} == \
                    {key: value for key, value in expected['tasks'][0].items() if key != 'lastReminderAt'}, \
                    'Reminder metadata write changed a newer task field'
                assert actual['revision'] == expected['revision'] + 1, 'Reminder write did not advance the latest database revision exactly once'
                expect(task_locator(page, changed_name)).to_have_count(1)
                expect(task_locator(page, name)).to_have_count(0)
                click_task_action(task_locator(page, changed_name), 'edit')
                expect(page.locator('#taskModal')).to_be_visible()
                expect(page.locator('#taskDesc')).to_have_value(expected['tasks'][0]['description'])
                followup_name = changed_name + ' saved here'
                page.locator('#taskName').fill(followup_name)
                page.locator('#submitBtn').click()
                expect(task_locator(page, followup_name)).to_have_count(1)
                followup = snapshot(page)
                assert followup['tasks'][0] == {**actual['tasks'][0], 'name': followup_name}, \
                    'Saving after reminder delivery overwrote fields changed in another window'
                assert followup['revision'] == actual['revision'] + 1
            elif action in ('abort', 'quota'):
                assert page.evaluate('window.reminderMetadataFailureInjected'), 'Reminder metadata failure hook was not reached'
                assert actual == expected, f'Reminder {action} left partial task data or revision metadata'
                assert page.evaluate('window.reminderWriteCount') == writes, 'Failed reminder transaction was reported as committed'
                assert page.evaluate("JSON.parse(sessionStorage.getItem('notifiedTasks') || '[]').length") == 0, \
                    'Failed reminder delivery was recorded as notified in the session'
            else:
                assert actual == expected, f'Delayed reminder changed a remotely {action}d task or advanced the revision'
                if action == 'delete': expect(task_locator(page, name)).to_have_count(0)
                else:
                    click_task_action(task_locator(page, name), 'edit')
                    expect(page.locator('#taskDesc')).to_have_value(expected['tasks'][0]['description'])
                    page.locator('#cancelBtn').click()
            context.close()
            print(f'Reminder concurrency passed: delayed delivery preserves remote {action}', flush=True)
        browser.close()


if __name__ == '__main__': run()
