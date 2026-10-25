#!/usr/bin/env python3
"""A stale writer must not inherit a revision published by an earlier queued read."""
from __future__ import annotations

from playwright.sync_api import expect, sync_playwright
from import_preview_concurrency_playwright import assert_reminder_metadata_only
from reminder_concurrency_playwright import seed
from smoke_playwright import (browser_launch_options, clear_app_data, get_task_records,
                              local_server, task_locator, wait_for_app_ready)


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
        try:
            first = context.new_page()
            errors = []
            first.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(first, url)
            first.evaluate('async () => { await navigator.serviceWorker.ready; }')
            first.add_init_script("""(() => {
                const completion = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, 'oncomplete');
                Object.defineProperty(IDBTransaction.prototype, 'oncomplete', {
                    configurable: true,
                    get: completion.get,
                    set(handler) {
                        const tx = this;
                        const names = Array.from(tx.objectStoreNames);
                        const shouldHold = tx.mode === 'readonly' && names.includes('tasks') && names.includes('config');
                        completion.set.call(tx, function(event) {
                            if (shouldHold && window.holdNextTaskRefresh) {
                                window.holdNextTaskRefresh = false;
                                window.finishHeldTaskRefresh = () => handler.call(tx, event);
                                window.heldRefreshReady = true;
                            } else handler.call(tx, event);
                        });
                    }
                });
                const transaction = IDBDatabase.prototype.transaction;
                IDBDatabase.prototype.transaction = function(stores, mode, ...rest) {
                    const tx = transaction.call(this, stores, mode, ...rest);
                    const names = typeof stores === 'string' ? [stores] : Array.from(stores);
                    if (mode === 'readwrite' && names.includes('tasks') && window.releaseOnNextTaskWrite) {
                        window.releaseOnNextTaskWrite = false;
                        queueMicrotask(() => {
                            window.finishHeldTaskRefresh();
                            window.heldRefreshReleased = true;
                        });
                    }
                    return tx;
                };
                Object.defineProperty(Notification, 'permission', {get:()=>'granted', configurable:true});
                ServiceWorkerRegistration.prototype.showNotification = function() {
                    return new Promise(resolve => { window.finishDelayedReminder = resolve; });
                };
            })();""")
            name = 'Queued write preserves remote task'
            seed(first, name)
            first.reload()
            wait_for_app_ready(first)
            first.wait_for_function('typeof window.finishDelayedReminder === "function"')
            second = context.new_page()
            second.goto(url)
            wait_for_app_ready(second)
            remote_description = 'Description committed in the second window'
            task_locator(second, name).locator('[data-action="edit"]').click()
            second.locator('#taskDesc').fill(remote_description)
            second.locator('#submitBtn').click()
            expect(second.locator('#taskModal')).to_be_hidden()
            expected = get_task_records(second)
            delivery_started = first.evaluate('Date.now()')
            first.evaluate("""() => {
                window.holdNextTaskRefresh = true;
                window.finishDelayedReminder();
            }""")
            first.wait_for_function('window.heldRefreshReady === true')
            expect(task_locator(first, name).locator('.task-desc')).not_to_contain_text(remote_description)
            expected = assert_reminder_metadata_only(first, expected, name, delivery_started)
            first.evaluate('() => { window.releaseOnNextTaskWrite = true; }')
            task_locator(first, name).locator('[data-action="toggle"]').click()
            first.wait_for_function('window.heldRefreshReleased === true')
            assert get_task_records(first) == expected, \
                'A stale queued writer inherited a refreshed revision and overwrote a newer task'
            assert not errors, errors
            print('Queued write concurrency passed: writer revision is captured before prior read completion', flush=True)
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    run()
