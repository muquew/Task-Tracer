#!/usr/bin/env python3
"""Verify persistence is user-requested, with safe denied/unsupported fallbacks."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (add_task, assert_backup_payload_integrity, browser_launch_options,
                              clear_app_data, get_task_records, local_server, task_locator)


def main() -> None:
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        for mode in ('granted', 'denied', 'unsupported'):
            context = browser.new_context(accept_downloads=True)
            context.add_init_script("""(() => {
                const mode = MODE;
                window.persistenceRequests = 0;
                let granted = false;
                const storage = {
                    persisted: async () => granted,
                    estimate: async () => ({usage: 2097152, quota: 104857600})
                };
                if (mode !== 'unsupported') storage.persist = async () => {
                    window.persistenceRequests++;
                    granted = mode === 'granted';
                    return granted;
                };
                Object.defineProperty(navigator, 'storage', {value: storage});
            })();""".replace('MODE', json.dumps(mode)))
            page = context.new_page()
            clear_app_data(page, url)
            add_task(page, 'Protected local task', no_deadline=True)
            before = get_task_records(page)
            language = page.locator('html').get_attribute('lang') or 'zh-CN'
            translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
            health = translations['storage']['health']

            def open_health():
                open_settings(page)
                page.locator('#storageHealthBtn').click()
                expect(page.locator('#storageUsage')).to_contain_text('100')

            def close_read_only(expected_requests):
                expect(page.locator('#submitBtn')).to_be_enabled()
                expect(page.locator('#submitBtn')).to_have_accessible_name(translations['viewsTransfer']['close'])
                expect(page.locator('#cancelBtn')).to_be_hidden()
                page.locator('#submitBtn').click()
                expect(page.locator('#taskModal')).to_be_hidden()
                assert page.evaluate('window.persistenceRequests') == expected_requests, 'Closing a read-only storage dialog requested permission'
                assert get_task_records(page) == before, 'Closing the storage dialog changed tasks'

            open_health()
            assert page.evaluate('window.persistenceRequests') == 0, 'Persistence permission was requested without a user click'
            if mode == 'unsupported':
                expect(page.locator('#storagePersistenceStatus')).to_have_text(health['unsupported'])
                close_read_only(0)
                open_health()
                expect(page.locator('#submitBtn')).to_be_enabled()
                expect(page.locator('#submitBtn')).to_have_accessible_name(translations['viewsTransfer']['close'])
                assert page.evaluate('window.persistenceRequests') == 0, 'Reopening unsupported storage requested permission'
            else:
                expect(page.locator('#submitBtn')).to_be_enabled()
                expect(page.locator('#submitBtn')).to_have_accessible_name(health['request'])
                page.locator('#submitBtn').click()
                assert page.evaluate('window.persistenceRequests') == 1
                assert get_task_records(page) == before, 'A persistence request changed tasks'
                if mode == 'granted':
                    expect(page.locator('#taskModal')).to_be_hidden()
                    open_health()
                    expect(page.locator('#storagePersistenceStatus')).to_have_text(health['persistent'])
                    close_read_only(1)
                    open_health()
                    expect(page.locator('#submitBtn')).to_be_enabled()
                    expect(page.locator('#submitBtn')).to_have_accessible_name(translations['viewsTransfer']['close'])
                    assert page.evaluate('window.persistenceRequests') == 1, 'Reopening granted storage requested permission again'
                else:
                    expect(page.locator('#taskModal')).to_be_visible()
                    expect(page.locator('#storagePersistenceStatus')).to_have_text(health['bestEffort'])
                    expect(page.locator('#submitBtn')).to_be_enabled()
                    expect(page.locator('#submitBtn')).to_have_accessible_name(health['request'])
                    page.locator('#submitBtn').click()
                    assert page.evaluate('window.persistenceRequests') == 2, 'Denied persistence did not allow an explicit retry'
                    expect(page.locator('#taskModal')).to_be_visible()
                    expect(page.locator('#submitBtn')).to_be_enabled()
                    expect(page.locator('#submitBtn')).to_have_accessible_name(health['request'])
                    assert get_task_records(page) == before, 'Retrying a denied persistence request changed tasks'
            expected_requests = page.evaluate('window.persistenceRequests')
            with page.expect_download() as download_info:
                page.locator('#storageHealthExportBtn').click()
            backup = json.loads(download_info.value.path().read_text())
            assert_backup_payload_integrity(backup, 'backup')
            assert backup['tasks'] == before, 'Storage-health export changed or omitted task fields'
            assert get_task_records(page) == before, 'Storage-health export changed saved tasks'
            assert page.evaluate('window.persistenceRequests') == expected_requests, 'Exporting a backup requested persistence permission'
            expect(task_locator(page, 'Protected local task')).to_have_count(1)
            context.close()
            print(f'Storage health passed: {mode}; explicit permission, existing tasks and export preserved')
        browser.close()


if __name__ == '__main__':
    main()
