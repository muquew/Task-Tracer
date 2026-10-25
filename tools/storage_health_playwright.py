#!/usr/bin/env python3
"""Verify persistence is user-requested, with safe denied/unsupported fallbacks."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace
import json

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import add_task, browser_launch_options, clear_app_data, local_server, task_locator


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
            open_settings(page)
            page.locator('#storageHealthBtn').click()
            expect(page.locator('#storageUsage')).to_contain_text('100')
            assert page.evaluate('window.persistenceRequests') == 0, 'Persistence permission was requested without a user click'
            if mode == 'unsupported':
                expect(page.locator('#submitBtn')).to_be_disabled()
            else:
                page.locator('#submitBtn').click()
                assert page.evaluate('window.persistenceRequests') == 1
                if mode == 'granted':
                    expect(page.locator('#taskModal')).to_be_hidden()
                    open_settings(page)
                    page.locator('#storageHealthBtn').click()
                    expect(page.locator('#submitBtn')).to_be_disabled()
                else:
                    expect(page.locator('#taskModal')).to_be_visible()
            with page.expect_download() as download_info:
                page.locator('#storageHealthExportBtn').click()
            backup = json.loads(download_info.value.path().read_text())
            assert any(task['name'] == 'Protected local task' for task in backup['tasks'])
            expect(task_locator(page, 'Protected local task')).to_have_count(1)
            context.close()
            print(f'Storage health passed: {mode}; explicit permission, existing tasks and export preserved')
        browser.close()


if __name__ == '__main__':
    main()
