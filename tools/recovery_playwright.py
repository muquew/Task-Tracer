#!/usr/bin/env python3
"""Exercise local recovery through the UI and verify transactional rollback."""

from __future__ import annotations

import os
import json
import re
import sys
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task,
    assert_empty_task_list,
    browser_launch_options,
    clear_app_data,
    delete_task,
    edit_task,
    local_server,
    task_locator,
    wait_for_app_ready,
)


def read_storage(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(['tasks', 'config'], 'readonly');
                const tasks = tx.objectStore('tasks').getAll();
                const history = tx.objectStore('config').get('recoveryHistory');
                tx.oncomplete = () => {
                    db.close();
                    resolve({tasks: tasks.result, history: history.result?.value || []});
                };
                tx.onerror = () => reject(tx.error);
                tx.onabort = () => reject(tx.error);
            };
        })"""
    )


def open_recovery(page: Page) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#recoveryBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    expect(page.locator("#recoverySelect")).to_have_count(1)


def exercise_recovery(page: Page, url: str) -> None:
    clear_app_data(page, url)
    name = "Recovery original"
    edited = "Recovery edited <img src=x onerror=window.recoveryXss=true>"
    add_task(page, name, no_deadline=True)
    edit_task(page, name, edited)
    delete_task(page, edited)
    page.reload()
    wait_for_app_ready(page)
    assert_empty_task_list(page)

    before_restore = read_storage(page)
    matching = [
        point
        for point in before_restore["history"]
        if any(task["name"] == edited for task in point["tasks"])
    ]
    if not matching:
        raise AssertionError("Deletion did not retain a recoverable task snapshot")
    open_recovery(page)
    page.locator("#recoverySelect").select_option(str(matching[0]["id"]), force=True)
    expect(page.locator("#recoveryConfirm")).not_to_be_checked()
    if page.locator("#submitBtn").is_enabled():
        page.locator("#submitBtn").click()
        expect(page.locator("#taskModal")).to_be_visible()
        if read_storage(page) != before_restore:
            raise AssertionError("Recovery changed data or history without explicit confirmation")
    alternative = next(
        point for point in before_restore["history"] if point["id"] != matching[0]["id"]
    )
    page.locator("#recoveryConfirm").check()
    page.locator("#recoverySelect").select_option(str(alternative["id"]), force=True)
    expect(page.locator("#recoveryConfirm")).not_to_be_checked()
    page.locator("#recoverySelect").select_option(str(matching[0]["id"]), force=True)
    page.locator("#recoveryConfirm").check()
    page.locator("#submitBtn").click()
    expect(page.locator("#taskModal")).to_be_hidden()
    expect(task_locator(page, edited)).to_have_count(1)
    expect(page.locator("#undoBtn")).to_be_disabled()
    if page.evaluate("Boolean(window.recoveryXss)"):
        raise AssertionError("Recovered task text was interpreted as executable HTML")

    page.reload()
    wait_for_app_ready(page)
    expect(task_locator(page, edited)).to_have_count(1)
    restored = read_storage(page)
    if not any(point["tasks"] == before_restore["tasks"] for point in restored["history"]):
        raise AssertionError("Restoration did not retain the state it replaced")
    print("Recovery passed: deleted data survives reload, explicit confirmation, reversible restore, safe task text")


def exercise_aborted_deletion(page: Page, url: str) -> None:
    clear_app_data(page, url)
    name = "Task protected by transaction rollback"
    add_task(page, name, no_deadline=True)
    before = read_storage(page)
    page.evaluate(
        """() => {
            const original = IDBObjectStore.prototype.delete;
            window.recoveryAbortInjected = false;
            IDBObjectStore.prototype.delete = function(...args) {
                if (this.name !== 'tasks') return original.apply(this, args);
                IDBObjectStore.prototype.delete = original;
                const request = original.apply(this, args);
                window.recoveryAbortInjected = true;
                this.transaction.abort();
                return request;
            };
        }"""
    )
    click_task_action(task_locator(page, name), 'delete')
    page.locator("#submitBtn").click()
    expect(page.locator("#notification")).to_have_class(re.compile(r"\berror\b"))
    if not page.evaluate("window.recoveryAbortInjected"):
        raise AssertionError("The transactional failure injection did not execute")
    if read_storage(page) != before:
        raise AssertionError("An aborted deletion changed task data or recovery history")
    page.reload()
    wait_for_app_ready(page)
    expect(task_locator(page, name)).to_have_count(1)
    print("Recovery passed: aborted task write rolls back both task data and recovery history")


def exercise_retention(page: Page, url: str) -> None:
    clear_app_data(page, url)
    names = [f"Recovery retention {index}" for index in range(12)]
    for name in names:
        add_task(page, name, no_deadline=True)
    for name in names:
        delete_task(page, name)
    stored = read_storage(page)
    if stored["tasks"]:
        raise AssertionError("Retention exercise did not delete the intended tasks")
    if len(stored["history"]) != 10:
        raise AssertionError(f"Expected 10 retained recovery points, got {len(stored['history'])}")
    if any(len(point["tasks"]) > 10 for point in stored["history"]):
        raise AssertionError("Old recovery points were not evicted")
    if not any([task["name"] for task in point["tasks"]] == [names[-1]] for point in stored["history"]):
        raise AssertionError("The most recent deleted task is not recoverable")
    print("Recovery passed: history retains the latest 10 recovery points")


def exercise_checkpoint_quota(page: Page, url: str) -> None:
    clear_app_data(page, url)
    name = 'Task protected when checkpoint storage is full'
    add_task(page, name, no_deadline=True)
    before = read_storage(page)
    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(value, ...args) {
            if (this.name === 'config' && value?.key === 'recoveryHistory') {
                IDBObjectStore.prototype.put = original;
                throw new DOMException('Synthetic checkpoint quota failure', 'QuotaExceededError');
            }
            return original.call(this, value, ...args);
        };
    }""")
    click_task_action(task_locator(page, name), 'delete')
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#emergencyBackupBtn')).to_be_visible()
    if read_storage(page) != before:
        raise AssertionError('Quota failure partially committed task deletion or checkpoint history')
    with page.expect_download() as download_info:
        page.locator('#emergencyBackupBtn').click()
    backup = json.loads(download_info.value.path().read_text())
    if not any(task['name'] == name for task in backup['tasks']):
        raise AssertionError('Quota failure lost the emergency task snapshot')
    page.locator('#clearRecoveryBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#cancelBtn').click()
    if read_storage(page) != before:
        raise AssertionError('Cancelling quota cleanup changed saved data')
    page.locator('#clearRecoveryBtn').click()
    page.locator('#submitBtn').click()
    wait_for_app_ready(page)
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    expect(task_locator(page, name)).to_have_count(1)
    after = read_storage(page)
    if after['history'] or after['tasks'] != before['tasks']:
        raise AssertionError('Quota cleanup failed to clear only recovery history')
    print('Recovery passed: checkpoint quota failure preserves task/history and emergency export')


def exercise_startup_quota(page: Page, url: str) -> None:
    clear_app_data(page, url)
    name = 'Existing task at quota-limited startup'
    add_task(page, name, no_deadline=True)
    page.add_init_script("""(() => {
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(value, ...args) {
            if (this.name === 'config' && value?.key === '__task_tracer_storage_probe__') {
                IDBObjectStore.prototype.put = original;
                throw new DOMException('Synthetic startup quota failure', 'QuotaExceededError');
            }
            return original.call(this, value, ...args);
        };
    })();""")
    page.reload()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#emergencyBackupBtn')).to_be_visible()
    with page.expect_download() as download_info:
        page.locator('#emergencyBackupBtn').click()
    backup = json.loads(download_info.value.path().read_text())
    if not any(task['name'] == name for task in backup['tasks']):
        raise AssertionError('Startup write-probe failure prevented a readable-data emergency export')
    print('Recovery passed: startup quota failure retains readable task data for export')


def check(url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        context = browser.new_context()
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        exercise_recovery(page, url)
        exercise_aborted_deletion(page, url)
        exercise_retention(page, url)
        exercise_checkpoint_quota(page, url)
        exercise_startup_quota(page, url)
        context.close()
        browser.close()
        if errors:
            raise AssertionError(f"Unexpected browser errors: {errors}")


def main() -> int:
    try:
        url = os.environ.get("TASK_TRACER_URL")
        if url:
            check(url)
        else:
            with local_server() as local_url:
                check(local_url)
    except Exception as error:
        print(f"Recovery checks failed: {error}", file=sys.stderr)
        return 1
    print("Local recovery checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
