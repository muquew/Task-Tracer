#!/usr/bin/env python3
"""Keep delayed local dialogs and confirmations bound to their own UI session."""
from __future__ import annotations

from smoke_playwright import open_task_editor

from smoke_playwright import open_settings, return_to_task_workspace

import argparse
import contextlib
from pathlib import Path
import tempfile
import zipfile

from playwright.sync_api import expect, sync_playwright

import smoke_playwright as smoke


def settle(page):
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def open_menu_item(page, selector):
    open_settings(page)
    page.locator(selector).click()


def begin_draft(page):
    return_to_task_workspace(page)
    open_task_editor(page)
    page.locator('#taskName').fill('Later synthetic task draft')
    page.locator('#taskDesc').fill('A delayed earlier dialog must preserve this text')


def assert_draft(page):
    expect(page.locator('#taskName')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value('Later synthetic task draft')
    expect(page.locator('#taskDesc')).to_have_value('A delayed earlier dialog must preserve this text')
    expect(page.locator('#submitBtn')).to_be_enabled()


def cancel_if_open(page):
    if page.locator('#taskModal').is_visible():
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()


def storage_loading_preserves_draft(page, url):
    smoke.clear_app_data(page, url)
    page.evaluate("""() => {
        Object.defineProperty(navigator, 'storage', {configurable: true, value: {persist: async () => false}});
        navigator.storage.persisted = () => new Promise(resolve => { window.finishStorageRead = resolve; });
        navigator.storage.estimate = async () => ({usage: 1024, quota: 1048576});
    }""")
    open_menu_item(page, '#storageHealthBtn')
    page.wait_for_function('typeof window.finishStorageRead === "function"')
    cancel_if_open(page)
    begin_draft(page)
    page.evaluate('window.finishStorageRead(false)')
    settle(page)
    assert_draft(page)
    assert smoke.get_task_records(page) == []
    print('Dialog lifecycle passed: cancelled storage status read cannot cover a later task draft', flush=True)


def recovery_loading_preserves_draft(page, url):
    smoke.clear_app_data(page, url)
    smoke.add_task(page, 'Synthetic recovery entry', no_deadline=True)
    before = smoke.get_task_records(page)
    page.evaluate("""() => {
        const nativeGet = IDBObjectStore.prototype.get;
        IDBObjectStore.prototype.get = function(key) {
            const request = nativeGet.call(this, key);
            if (this.name === 'config' && key === 'recoveryHistory' && this.transaction.mode === 'readonly') {
                IDBObjectStore.prototype.get = nativeGet;
                const tx = this.transaction;
                const complete = tx.oncomplete;
                tx.oncomplete = null;
                tx.addEventListener('complete', event => {
                    window.finishRecoveryRead = () => complete.call(tx, event);
                }, {once: true});
            }
            return request;
        };
    }""")
    open_menu_item(page, '#recoveryBtn')
    page.wait_for_function('typeof window.finishRecoveryRead === "function"')
    cancel_if_open(page)
    begin_draft(page)
    page.evaluate('window.finishRecoveryRead()')
    settle(page)
    assert_draft(page)
    assert smoke.get_task_records(page) == before
    print('Dialog lifecycle passed: cancelled recovery read cannot cover a later task draft', flush=True)


def repeated_storage_read_keeps_latest(page, url):
    smoke.clear_app_data(page, url)
    page.evaluate("""() => {
        Object.defineProperty(navigator, 'storage', {configurable: true, value: {persist: async () => false}});
        window.storageReadCompletions = [];
        navigator.storage.persisted = () => new Promise(resolve => window.storageReadCompletions.push(resolve));
        navigator.storage.estimate = async () => ({usage: 1024, quota: 1048576});
    }""")
    open_menu_item(page, '#storageHealthBtn')
    page.wait_for_function('window.storageReadCompletions.length === 1')
    cancel_if_open(page)
    open_menu_item(page, '#storageHealthBtn')
    page.wait_for_function('window.storageReadCompletions.length === 2')
    page.evaluate('window.storageReadCompletions[0](true)')
    settle(page)
    expect(page.locator('#storageHealthReadStatus')).to_be_visible()
    expect(page.locator('#storageUsage')).to_have_count(0)
    expect(page.locator('#submitBtn')).to_be_disabled()
    page.evaluate('window.storageReadCompletions[1](false)')
    expect(page.locator('#storageUsage')).to_be_visible()
    expect(page.locator('#storagePersistenceStatus')).to_contain_text('尽力')
    expect(page.locator('#submitBtn')).to_be_enabled()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert smoke.get_task_records(page) == []
    print('Dialog lifecycle passed: an older status read cannot replace a repeated newer request', flush=True)


def begin_pending_persistence(page, url):
    smoke.clear_app_data(page, url)
    page.evaluate("""() => {
        Object.defineProperty(navigator, 'storage', {configurable: true, value: {persist: async () => false}});
        navigator.storage.persisted = async () => false;
        navigator.storage.estimate = async () => ({usage: 1024, quota: 1048576});
        navigator.storage.persist = () => new Promise(resolve => { window.finishPersistence = resolve; });
    }""")
    open_menu_item(page, '#storageHealthBtn')
    expect(page.locator('#storageUsage')).to_be_visible()
    page.locator('#submitBtn').click()
    page.wait_for_function('typeof window.finishPersistence === "function"')
    expect(page.locator('#submitBtn')).to_be_disabled()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def old_confirmation_preserves_draft(page, url):
    begin_pending_persistence(page, url)
    begin_draft(page)
    page.evaluate('window.finishPersistence(true)')
    settle(page)
    assert_draft(page)
    assert smoke.get_task_records(page) == []
    print('Dialog lifecycle passed: completed old confirmation cannot close a later task draft', flush=True)


def old_confirmation_preserves_gate(page, url):
    begin_pending_persistence(page, url)
    page.evaluate("""() => {
        FileReader.prototype.readAsText = function() { window.taskReadHeld = true; };
    }""")
    open_settings(page)
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'held-tasks.json', 'mimeType': 'application/json', 'buffer': b'[]'})
    page.wait_for_function('window.taskReadHeld === true')
    expect(page.locator('#taskImportReadStatus')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_disabled()
    page.evaluate('window.finishPersistence(false)')
    settle(page)
    expect(page.locator('#taskImportReadStatus')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_disabled()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert smoke.get_task_records(page) == []
    print('Dialog lifecycle passed: old false-result confirmation cannot unlock a newer reading gate', flush=True)


CASES = {
    'storage': storage_loading_preserves_draft,
    'recovery': recovery_loading_preserves_draft,
    'repeated': repeated_storage_read_keeps_latest,
    'confirm': old_confirmation_preserves_draft,
    'gate': old_confirmation_preserves_gate,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--baseline-archive', type=Path, help='Serve a previously built static archive without changing the working tree')
    args = parser.parse_args()
    with contextlib.ExitStack() as stack:
        if args.baseline_archive:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='task-tracer-dialog-baseline-')))
            with zipfile.ZipFile(args.baseline_archive) as archive:
                for name in archive.namelist():
                    if Path(name).is_absolute() or '..' in Path(name).parts:
                        raise AssertionError('Unsafe baseline archive path')
                archive.extractall(root)
            smoke.REPO_ROOT = root
        url = stack.enter_context(smoke.local_server())
        playwright = stack.enter_context(sync_playwright())
        options = smoke.browser_launch_options() if args.browser == 'chromium' else {'headless': True}
        browser = getattr(playwright, args.browser).launch(**options)
        stack.callback(browser.close)
        selected = CASES.items() if args.case == 'all' else [(args.case, CASES[args.case])]
        for name, case in selected:
            context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
            errors = []
            try:
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                case(page, url)
                assert not errors, (name, errors)
            finally:
                context.close()
    print(f'{args.browser}: dialog lifecycle checks passed', flush=True)


if __name__ == '__main__':
    main()
