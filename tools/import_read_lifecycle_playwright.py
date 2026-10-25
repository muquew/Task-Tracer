#!/usr/bin/env python3
"""Keep cancelled or superseded task-file reads from replacing a newer workflow."""
from __future__ import annotations

from smoke_playwright import open_task_editor

from smoke_playwright import open_settings, return_to_task_workspace

import json

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    browser_launch_options, clear_app_data, get_task_records, local_server,
)


def defer_native_reads(page):
    page.evaluate("""() => {
        const readAsText = FileReader.prototype.readAsText;
        window.pendingImportReads = [];
        window.completedImportReads = [];
        FileReader.prototype.readAsText = function(file, ...args) {
            const index = window.pendingImportReads.length;
            window.pendingImportReads.push({reader: this, file, args});
            this.addEventListener('loadend', () => window.completedImportReads.push(index), {once: true});
        };
        window.finishImportRead = index => {
            const {reader, file, args} = window.pendingImportReads[index];
            readAsText.call(reader, file, ...args);
        };
    }""")


def choose_file(page, name):
    count = page.evaluate('window.pendingImportReads.length')
    open_settings(page)
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({
        'name': f'{name}.json', 'mimeType': 'application/json',
        'buffer': json.dumps([{'id': 123456, 'name': name, 'description': 'Synthetic import'}]).encode(),
    })
    page.wait_for_function('before => window.pendingImportReads.length === before + 1', arg=count)
    return count


def cancel_pending_ui(page):
    # The former implementation had no reading surface. A cancellable reading
    # dialog is permitted, but an old file must never reopen over a later form.
    if page.locator('#taskModal').is_visible():
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()


def finish_read(page, index):
    page.evaluate('index => window.finishImportRead(index)', index)
    page.wait_for_function('index => window.completedImportReads.includes(index)', arg=index)
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(resolve))')


def cancelled_read_preserves_draft(browser, url):
    context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
    try:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(page, url)
        defer_native_reads(page)
        old = choose_file(page, 'CANCELLED_OLD_IMPORT')
        cancel_pending_ui(page)
        return_to_task_workspace(page)
        open_task_editor(page)
        page.locator('#taskName').fill('New task draft must survive')
        page.locator('#taskDesc').fill('Unsaved synthetic description')
        finish_read(page, old)
        expect(page.locator('#taskName')).to_be_visible()
        expect(page.locator('#taskName')).to_have_value('New task draft must survive')
        expect(page.locator('#taskDesc')).to_have_value('Unsaved synthetic description')
        expect(page.locator('#mergeImportMode')).to_be_hidden()
        assert get_task_records(page) == [], 'An abandoned file read wrote task data'
        assert not errors, errors
        print('Task import read passed: cancelled file completion preserves a later task draft', flush=True)
    finally:
        context.close()


def superseded_read_preserves_new_preview(browser, url):
    context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
    try:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(page, url)
        defer_native_reads(page)
        old = choose_file(page, 'SUPERSEDED_OLD_IMPORT')
        cancel_pending_ui(page)
        latest = choose_file(page, 'LATEST_SELECTED_IMPORT')
        finish_read(page, latest)
        expect(page.locator('#mergeImportMode')).to_be_visible()
        expect(page.locator('#confirm-message-text')).to_contain_text('LATEST_SELECTED_IMPORT')
        finish_read(page, old)
        expect(page.locator('#mergeImportMode')).to_be_visible()
        expect(page.locator('#confirm-message-text')).to_contain_text('LATEST_SELECTED_IMPORT')
        expect(page.locator('#confirm-message-text')).not_to_contain_text('SUPERSEDED_OLD_IMPORT')
        assert get_task_records(page) == [], 'Preview selection wrote task data before confirmation'
        assert not errors, errors
        print('Task import read passed: a slower old file cannot replace the latest selected preview', flush=True)
    finally:
        context.close()


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        try:
            cancelled_read_preserves_draft(browser, url)
            superseded_read_preserves_new_preview(browser, url)
        finally:
            browser.close()


if __name__ == '__main__':
    run()
