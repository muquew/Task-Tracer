#!/usr/bin/env python3
"""Verify database upgrades unblock and keep recoverable tasks available."""
from __future__ import annotations

import json
import os
from playwright.sync_api import expect, sync_playwright
from smoke_playwright import add_task, browser_launch_options, clear_app_data, local_server, wait_for_app_ready


def check(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        clear_app_data(page, url)
        add_task(page, 'Survive database upgrade', no_deadline=True)
        result = page.evaluate("""() => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 3);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('tasks');
                const tasks = tx.objectStore('tasks').getAll();
                tx.oncomplete = () => { db.close(); resolve(tasks.result.map(task => task.name)); };
                tx.onabort = () => reject(tx.error);
            };
        })""")
        assert 'Survive database upgrade' in result, result
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        expect(page.locator('#storageUnavailableMessage')).to_have_attribute('data-i18n', 'storage.versionChanged')
        expect(page.locator('#openModalBtn')).to_be_disabled()
        expect(page.locator('#emergencyBackupBtn')).to_be_visible()
        with page.expect_download() as download_info:
            page.locator('#emergencyBackupBtn').click()
        payload = json.loads(download_info.value.path().read_text())
        assert any(task['name'] == 'Survive database upgrade' for task in payload['tasks'])
        context.close()
        print('Storage upgrade unblocks and retains tasks plus an emergency export')

        context = browser.new_context()
        blocker = context.new_page()
        blocker.goto(url + 'robots.txt')
        blocker.evaluate("""() => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 1);
            request.onsuccess = () => { window.blockingDB = request.result; resolve(); };
            request.onerror = () => reject(request.error);
        })""")
        page = context.new_page()
        page.goto(url)
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        expect(page.locator('#storageUnavailableMessage')).to_have_attribute('data-i18n', 'storage.upgradeBlocked')
        expect(page.locator('#initial-loader')).to_have_count(0)
        expect(page.locator('#openModalBtn')).to_be_disabled()
        blocker.evaluate('window.blockingDB.close()')
        page.locator('#retryStorageBtn').click()
        wait_for_app_ready(page)
        expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
        expect(page.locator('#openModalBtn')).to_be_enabled()
        context.close()
        browser.close()
        print('Blocked startup shows recovery guidance and retry works after the older window closes')


if __name__ == '__main__':
    target = os.environ.get('TASK_TRACER_URL')
    if target:
        check(target)
    else:
        with local_server() as target:
            check(target)
