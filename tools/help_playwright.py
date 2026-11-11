#!/usr/bin/env python3
"""Verify bilingual help, explicit diagnostics export and storage-failure access."""
from __future__ import annotations

from smoke_playwright import help_entry, open_help, open_settings, return_to_task_workspace

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import select_language
from smoke_playwright import add_task, browser_launch_options, clear_app_data, local_server, wait_for_app_ready
from validate_static import app_version

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_VALUES = ['PRIVATE-TASK-724', 'PRIVATE-DESCRIPTION-724', 'PRIVATE-TAG-724',
                  'PRIVATE-PROJECT-724', 'PRIVATE-URL-724', 'PRIVATE-ERROR-724',
                  'PRIVATE-ERROR-NAME-724', 'PRIVATE-PREFERENCE-724']


def snapshot(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const open = window.__testOpenIndexedDB || indexedDB.open.bind(indexedDB);
        const request = open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => {
                db.close();
                resolve({tasks: tasks.result, config: config.result,
                    local: {...localStorage}, session: {...sessionStorage}});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def assert_focus_trap(page):
    page.locator('#submitBtn').focus()
    page.keyboard.press('Tab')
    expect(page.locator('#closeModalBtn')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(page.locator('#submitBtn')).to_be_focused()


def assert_private_report(report):
    text = json.dumps(report)
    for sentinel in PRIVATE_VALUES:
        assert sentinel not in text, f'Diagnostic leaked synthetic private value {sentinel}'
    assert set(report) == {'type', 'schemaVersion', 'generatedAt', 'appVersion', 'resourceVersion',
                           'databaseVersion', 'browser', 'capabilities', 'storage', 'serviceWorker'}
    assert report['type'] == 'task-tracer-diagnostics'
    assert report['schemaVersion'] == 1
    assert set(report['browser']) == {'userAgent', 'language', 'online', 'standalone'}
    assert set(report['storage']) == {'available', 'error', 'persistent', 'usageBytes', 'quotaBytes'}
    assert set(report['serviceWorker']) == {'controlled'}
    assert re.fullmatch(r'\d+\.\d+(?:\.\d+)?', report['appVersion'])


def exercise_diagnostics(page, downloads, expected_error=None):
    before = snapshot(page)
    count_before = len(downloads)
    page.locator('#helpDiagnosticsBtn').click()
    expect(page.locator('#diagnosticPreview')).to_be_visible()
    language = page.locator('html').get_attribute('lang')
    translations = json.loads((ROOT / 'resources' / f'{language}.json').read_text())['help']
    expect(page.locator('#diagnosticPreview dt')).to_have_text([
        translations[key] for key in ('diagnosticVersion', 'diagnosticBrowser', 'diagnosticConnection', 'diagnosticStorage')])
    values = page.locator('#diagnosticPreview dd').all_inner_texts()
    assert len(values) == 4 and all(values), 'Diagnostic summary contains missing or empty data'
    assert values[0] == app_version((ROOT / 'index.html').read_text())
    assert len(downloads) == count_before, 'Diagnostics downloaded before explicit confirmation'
    assert snapshot(page) == before, 'Previewing diagnostics changed stored data'
    assert_focus_trap(page)
    activation_errors = []
    def observe_activation(message):
        if message.type == 'error':
            activation_errors.append(message.text)
    page.on('console', observe_activation)
    try:
        with page.expect_download() as result:
            page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
    finally:
        page.remove_listener('console', observe_activation)
    assert not activation_errors, f'Diagnostics confirmation triggered a native form submission or console error: {activation_errors}'
    download = result.value
    actual = json.loads(download.path().read_text())
    assert_private_report(actual)
    assert actual['storage']['error'] == expected_error
    assert actual['storage']['available'] == (expected_error is None)
    assert download.suggested_filename == f'task-tracer-diagnostics-{actual["appVersion"]}.json'
    assert values[0] == actual['appVersion'], 'Downloaded version differs from the reviewed summary'
    assert values[2] == translations['diagnosticOnline' if actual['browser']['online'] else 'diagnosticOffline']
    assert values[3] == translations['diagnosticAvailable' if actual['storage']['available'] else 'diagnosticUnavailable']
    assert actual['browser']['userAgent'] == page.evaluate('navigator.userAgent')
    browser = re.fullmatch(r'(.+) ([\d.]+)', values[1])
    assert browser and browser[2] in actual['browser']['userAgent'], 'Browser summary differs from the downloaded report'
    assert len(downloads) == count_before + 1
    expect(page.locator('#taskModal')).to_be_hidden()
    assert snapshot(page) == before, 'Help/diagnostics changed tasks, settings or browser storage'
    return actual


def run(engine='chromium'):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        options['timeout'] = 30000
        browser = getattr(p, engine).launch(**options)
        print(f'{engine}: Help/diagnostics regression on {browser.version}', flush=True)
        context = browser.new_context(accept_downloads=True, locale='en-US', reduced_motion='reduce')
        try:
            page = context.new_page()
            errors, downloads = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('download', lambda download: downloads.append(download))
            clear_app_data(page, url)
            add_task(page, PRIVATE_VALUES[0], description=PRIVATE_VALUES[1], no_deadline=True,
                     project=PRIVATE_VALUES[3], tags=[PRIVATE_VALUES[2]])
            page.evaluate("""value => new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction('config', 'readwrite');
                    tx.objectStore('config').put({key:'privateSupportTest', value});
                    tx.oncomplete = () => {db.close(); resolve();};
                    tx.onabort = () => reject(tx.error);
                };
                request.onerror = () => reject(request.error);
            })""", PRIVATE_VALUES[-1])
            page.goto(url + '?support_private_url=' + PRIVATE_VALUES[4])
            wait_for_app_ready(page)
            for language in ('en', 'zh-CN'):
                select_language(page, language)
                expect(page.locator('html')).to_have_attribute('lang', language)
                page.keyboard.press('Escape')
                translations = json.loads((ROOT / 'resources' / f'{language}.json').read_text())['help']
                open_settings(page, 'help')
                expect(page.locator('#helpMenuBtn')).to_be_visible()
                page.locator('#helpMenuBtn').click()
                expect(page.get_by_role('dialog', name=translations['menu'], exact=True)).to_be_visible()
                expect(page.locator('.help-guide details.help-reference')).to_have_count(0)
                guide = page.get_by_role('link', name=translations['userGuide'], exact=True)
                expect(guide).to_be_visible()
                readme = 'README_zh_cn.md' if language == 'zh-CN' else 'README.md'
                expect(guide).to_have_attribute('href', f'https://github.com/muquew/Task-Tracer/blob/main/{readme}')
                expect(guide).to_have_attribute('target', '_blank')
                expect(guide).to_have_attribute('rel', re.compile(r'noopener'))
                expect(page.locator('.help-guide dl dt')).to_have_count(5)
                for action in ('newTask', 'search', 'commands', 'settings', 'undo'):
                    expect(page.locator('.help-guide dl')).to_contain_text(translations[action])
                version = app_version((ROOT / 'index.html').read_text())
                assert_focus_trap(page)
                page.keyboard.press('Escape')
                expect(page.locator('#taskModal')).to_be_hidden()
                expect(page.locator('#helpMenuBtn')).to_be_focused()
                return_to_task_workspace(page)
                open_help(page)
                assert help_entry(page).is_enabled()
                report = exercise_diagnostics(page, downloads)
                assert report['appVersion'] == version
                expect(help_entry(page)).to_be_focused()
                open_help(page)
                page.locator('#helpCommandsBtn').click()
                expect(page.locator('#commandPalette')).to_be_visible()
                expect(page.locator('#commandPaletteInput')).to_be_focused()
                page.keyboard.press('Escape')
                expect(page.locator('#commandPalette')).to_be_hidden()
                print(f'Help passed: {language}; guide/shortcuts, keyboard focus, commands and private explicit-download report', flush=True)

            before_cancel = snapshot(page)
            download_count = len(downloads)
            page.evaluate("""() => {
                window.__originalDiagnosticStorage = Object.getOwnPropertyDescriptor(navigator, 'storage');
                Object.defineProperty(navigator, 'storage', {configurable: true, value: {
                    persisted: async () => false,
                    estimate: () => new Promise(resolve => {
                        window.finishDelayedDiagnosticEstimate = resolve;
                    })
                }});
            }""")
            open_help(page)
            page.locator('#helpDiagnosticsBtn').click()
            page.wait_for_function('typeof window.finishDelayedDiagnosticEstimate === "function"')
            page.keyboard.press('Escape')
            expect(page.locator('#taskModal')).to_be_hidden()
            expect(help_entry(page)).to_be_focused()
            page.evaluate("""async () => {
                window.finishDelayedDiagnosticEstimate({usage: 1024, quota: 1048576});
                await new Promise(requestAnimationFrame);
                if (window.__originalDiagnosticStorage) {
                    Object.defineProperty(navigator, 'storage', window.__originalDiagnosticStorage);
                } else {
                    delete navigator.storage;
                }
            }""")
            expect(page.locator('#taskModal')).to_be_hidden()
            assert len(downloads) == download_count
            assert snapshot(page) == before_cancel
            print('Help passed: cancellation during a delayed storage estimate cannot reopen diagnostics', flush=True)

            before_failure = snapshot(page)
            page.add_init_script("""(() => {
                window.__testOpenIndexedDB = indexedDB.open.bind(indexedDB);
                IDBFactory.prototype.open = function(...args) {
                    if (sessionStorage.getItem('__helpStorageRecovered') === 'yes') {
                        return window.__testOpenIndexedDB(...args);
                    }
                    const error = new Error('PRIVATE-ERROR-724');
                    error.name = 'PRIVATE-ERROR-NAME-724';
                    throw error;
                };
            })();""")
            page.reload()
            expect(page.locator('body')).to_have_class(re.compile(r'\bstorage-unavailable\b'))
            expect(page.locator('#openModalBtn')).to_be_disabled()
            expect(help_entry(page)).to_be_enabled()
            open_help(page)
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#helpCommandsBtn')).to_be_disabled()
            assert_focus_trap(page)
            page.keyboard.press('Escape')
            expect(page.locator('#taskModal')).to_be_hidden()
            expect(help_entry(page)).to_be_focused()
            open_help(page)
            exercise_diagnostics(page, downloads, 'StorageError')
            expect(help_entry(page)).to_be_focused()
            assert snapshot(page) == before_failure, 'Storage-error help changed existing data'
            open_help(page)
            expect(page.locator('#cancelBtn')).to_be_hidden()
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            expect(help_entry(page)).to_be_focused()
            page.evaluate("sessionStorage.setItem('__helpStorageRecovered', 'yes')")
            with page.expect_navigation():
                page.locator('#retryStorageBtn').click()
            wait_for_app_ready(page)
            expect(page.locator('#openModalBtn')).to_be_enabled()
            open_help(page)
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#helpCommandsBtn')).to_be_enabled()
            exercise_diagnostics(page, downloads)
            expect(help_entry(page)).to_be_focused()
            assert not errors, errors
            print('Help passed: storage failure retains settings Help, keyboard access and redacted diagnostics; retry restores normal Help and one-download behavior', flush=True)
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
