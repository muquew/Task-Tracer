#!/usr/bin/env python3
"""Check manual PWA updates through real buttons and synthetic release fixtures.

The current application and worker are read unchanged. Candidate versions exist
only in UpdateServer memory; no release, source, or existing test is rewritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import traceback

from playwright.sync_api import expect, sync_playwright

from service_worker_update_playwright import (
    Bundle, UpdateServer, app_version, current_bundle, installed_bundle,
    next_bundle, workspace,
)
from smoke_playwright import (
    browser_launch_options, open_settings, return_to_task_workspace,
    task_locator, wait_for_app_ready,
)
from task_draft_playwright import hold_next_task_completion, inject_quota_failure


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = Path('/tmp/task-tracer-4.13.1-manual-update')
TASK_NAME = 'Task retained through a manual update'
VIEW_NAME = 'Manual update retained view'
QUICK_DRAFT = 'Keep this unsaved quick-add text #manual-update'


class Report:
    def __init__(self, directory: Path, release: Bundle):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        snapshot = self.directory / 'source-snapshot'
        snapshot.mkdir(exist_ok=True)
        sources = ('index.html', 'sw.js', 'resources/en.json', 'resources/zh-CN.json')
        for name in sources:
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(release.files[name])
        test_source = Path(__file__).read_bytes()
        (snapshot / 'manual_update_playwright.py').write_bytes(test_source)
        self.data = {
            'status': 'running',
            'started_at': datetime.now(timezone.utc).isoformat(),
            'source_version': release.version,
            'browser': 'chromium',
            'fixture': 'In-memory synthetic next-version bundles, served by UpdateServer',
            'source_sha256': {
                name: hashlib.sha256(release.files[name]).hexdigest() for name in sources
            },
            'test_sha256': hashlib.sha256(test_source).hexdigest(),
            'checks': [],
        }
        self.write()

    def write(self):
        (self.directory / 'report.json').write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def passed(self, name, page, **details):
        self.data['checks'].append({'name': name, 'status': 'passed', **details})
        page.screenshot(path=str(self.directory / f'{len(self.data["checks"]):02d}-{name}.png'))
        self.write()
        print(f'PASS: {name}', flush=True)


def expect_status(page, state, timeout=30_000):
    status = page.locator('#updateCheckStatus')
    expect(status).to_have_attribute('role', 'status')
    expect(status).to_have_attribute('data-state', state, timeout=timeout)
    assert status.inner_text().strip(), f'{state} has no user-facing explanation'
    return status


def check_update(page, state, timeout=30_000):
    open_settings(page, 'help')
    button = page.locator('#checkUpdateBtn')
    expect(button).to_be_visible()
    expect(button).to_be_enabled()
    button.click()
    expect_status(page, state, timeout)
    if state != 'checking':
        expect(button).to_be_enabled()


def seed_workspace(page, server, release):
    page.goto(server.url)
    wait_for_app_ready(page)
    page.wait_for_function("async () => navigator.serviceWorker.controller && (await navigator.serviceWorker.ready).active?.state === 'activated'")
    # The stable keyboard action opens the full task editor independently of the
    # current primary Add task / quick-capture presentation.
    page.keyboard.press('Control+i')
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#taskName').fill(TASK_NAME)
    page.locator('#taskDesc').fill('Keep committed tasks and view metadata unchanged.')
    page.locator('#taskProject').fill('Manual update')
    page.locator('#noDeadline').check()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_locator(page, TASK_NAME)).to_have_count(1)
    page.locator('#searchInput').fill('manual update')
    page.locator('#saveSmartViewBtn').click()
    page.locator('#savedViewNameInput').fill(VIEW_NAME)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('#searchInput').fill('')
    assert app_version(page) == release.version
    return workspace(page)


def quick_capture(page):
    return_to_task_workspace(page)
    field = page.locator('#quickAddInput')
    if not field.is_visible():
        # Keep this adapter local: older releases used Add task to reveal the
        # shelf, while the new primary action can open the full editor directly.
        for selector in ('#quickCaptureBtn', '#openQuickAddBtn', '#captureToggleBtn', '#openModalBtn'):
            control = page.locator(selector)
            if control.count() and control.is_visible():
                control.click()
                if field.is_visible():
                    break
                if page.locator('#taskModal').is_visible():
                    page.locator('#cancelBtn').click()
    expect(field).to_be_visible()
    assert not field.evaluate('node => Boolean(node.closest("[hidden], [inert]"))')
    return field


def assert_document_retained(page, token, dialogs):
    assert page.evaluate('window.__manualUpdateDocument') == token, 'Update replaced a document containing unsaved work'
    assert dialogs == [], f'Update relied on a native unload confirmation: {dialogs}'


def assert_manual_update(browser, release, report):
    candidate = next_bundle(release)
    server = UpdateServer(release)
    server.start()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                  locale='en-US', reduced_motion='reduce', accept_downloads=True)
    page = context.new_page()
    errors, dialogs = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('dialog', lambda dialog: (dialogs.append(dialog.type), dialog.dismiss()))
    try:
        expected = seed_workspace(page, server, release)
        baseline = installed_bundle(page, release)
        assert all(baseline.values())

        before = len(server.requests)
        check_update(page, 'latest')
        assert any(path == '/sw.js' and status == 200 for _, path, status in server.requests[before:]), 'Check update did not request the actual service-worker script'
        expect(page.locator('#settingsUpdateNowBtn')).to_be_hidden()
        assert workspace(page) == expected
        report.passed('latest', page)

        context.set_offline(True)
        check_update(page, 'offline')
        assert workspace(page) == expected
        report.passed('offline', page)
        context.set_offline(False)

        server.worker_fails = True
        before = len(server.requests)
        check_update(page, 'error')
        assert any(path == '/sw.js' and status == 503 for _, path, status in server.requests[before:])
        assert installed_bundle(page, release) == baseline
        assert workspace(page) == expected
        report.passed('worker-503', page)
        server.worker_fails = False

        server.bundle = candidate
        server.resources_fail = True
        check_update(page, 'error')
        assert candidate.cache not in page.evaluate('caches.keys()'), 'Failed installation left a partial candidate cache'
        assert installed_bundle(page, release) == baseline
        assert workspace(page) == expected
        report.passed('required-resource-failure', page, synthetic_candidate=candidate.version)

        server.resources_fail = False
        server.block_resource = True
        blocked_request_start = len(server.requests)
        check_update(page, 'checking')
        assert server.resource_requested.wait(10), 'Manual check did not start the candidate resource installation'
        expect_status(page, 'checking')
        expect(page.locator('#checkUpdateBtn')).to_be_disabled()
        assert app_version(page) == release.version
        assert workspace(page) == expected
        report.passed('install-remains-checking', page)

        started = time.monotonic()
        expect_status(page, 'error', timeout=40_000)
        expect(page.locator('#checkUpdateBtn')).to_be_enabled()
        assert not server.release_resource.is_set()
        assert not any(version == candidate.version and path.startswith('/resources/zh-CN.json')
                       for version, path, _ in server.requests[blocked_request_start:]), 'Server completed the blocked request before the UI timeout'
        assert app_version(page) == release.version
        report.passed('install-timeout-restores-control', page,
                      observed_wait_seconds=round(time.monotonic() - started, 2))
        server.release_resource.set()
        expect_status(page, 'ready')
        page.wait_for_function("async () => !(await navigator.serviceWorker.getRegistration()).installing && !(await navigator.serviceWorker.getRegistration()).waiting && (await navigator.serviceWorker.getRegistration()).active?.state === 'activated'")
        expect(page.locator('#settingsUpdateNowBtn')).to_be_visible()
        expect(page.locator('#updatePrompt')).to_be_visible()
        assert app_version(page) == release.version, 'Checking an update automatically refreshed the old page'
        assert workspace(page) == expected
        report.passed('ready-after-background-activation', page, synthetic_candidate=candidate.version)

        page.locator('#dismissUpdateBtn').click()
        expect(page.locator('#updatePrompt')).to_be_hidden()
        check_update(page, 'ready')
        expect(page.locator('#updatePrompt')).to_be_visible()
        report.passed('dismissed-activated-update-rediscovered', page)
        context.set_offline(True)
        check_update(page, 'ready')
        report.passed('ready-takes-precedence-over-offline', page)
        context.set_offline(False)

        token = 'manual-update-original-document'
        page.evaluate('token => { window.__manualUpdateDocument = token; }', token)
        quick_capture(page).fill(QUICK_DRAFT)
        open_settings(page, 'help')
        page.locator('#settingsUpdateNowBtn').click()
        expect_status(page, 'blocked')
        # Cover the previous 700ms unconditional reload regression explicitly.
        page.wait_for_timeout(900)
        assert_document_retained(page, token, dialogs)
        expect(page.locator('#quickAddInput')).to_have_value(QUICK_DRAFT)
        assert workspace(page) == expected
        report.passed('quick-add-draft-blocks-refresh', page)
        quick_capture(page).fill('')

        check_update(page, 'ready')
        return_to_task_workspace(page)
        page.keyboard.press('Control+i')
        page.locator('#taskName').fill('Keep this full-editor draft')
        # The modal owns pointer interaction; a dispatched activation checks the
        # same button handler against reentrant events without bypassing it.
        page.locator('#updateNowBtn').dispatch_event('click')
        expect_status(page, 'blocked')
        expect(page.locator('#taskName')).to_have_value('Keep this full-editor draft')
        assert_document_retained(page, token, dialogs)
        report.passed('full-editor-draft-blocks-refresh', page)
        page.locator('#cancelBtn').click()
        page.locator('#draftDiscardBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()

        check_update(page, 'ready')
        return_to_task_workspace(page)
        page.keyboard.press('Control+i')
        page.locator('#taskName').fill('Committed save waits before manual update')
        hold_next_task_completion(page)
        page.locator('#submitBtn').click()
        page.wait_for_function('window.taskWriteCommitted === true')
        expect(page.locator('#taskDraftSavingStatus')).to_be_visible()
        page.locator('#updateNowBtn').dispatch_event('click')
        expect_status(page, 'blocked')
        assert_document_retained(page, token, dialogs)
        report.passed('pending-save-blocks-refresh', page,
                      fixture='Real committed IDB transaction; only application completion callback held')
        page.evaluate('window.finishTaskWrite()')
        expect(page.locator('#taskModal')).to_be_hidden()
        expected = workspace(page)

        check_update(page, 'ready')
        return_to_task_workspace(page)
        page.keyboard.press('Control+i')
        page.locator('#taskName').fill('Memory-only recovery draft before update')
        inject_quota_failure(page)
        page.locator('#submitBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
        page.locator('#updateNowBtn').click()
        expect_status(page, 'blocked')
        assert_document_retained(page, token, dialogs)
        assert workspace(page) == expected
        report.passed('retained-recovery-draft-blocks-refresh', page,
                      fixture='One synthetic QuotaExceededError on task add')
        # Retry deliberately retains the current page while memory drafts exist;
        # with none left, the application's ordinary storage recovery reloads.
        page.locator('#retryStorageBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
        assert_document_retained(page, token, dialogs)
        page.locator('#taskDraftRecoveryDiscardBtn').click()
        page.locator('#submitBtn').click()
        expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()

        check_update(page, 'ready')
        with page.expect_navigation(wait_until='domcontentloaded'):
            page.locator('#settingsUpdateNowBtn').click()
        wait_for_app_ready(page)
        assert app_version(page) == candidate.version
        assert page.evaluate('window.__manualUpdateDocument') is None
        assert workspace(page) == expected, 'Successful update changed tasks or saved-view metadata'
        expect(task_locator(page, TASK_NAME)).to_have_count(1)
        assert dialogs == []
        assert errors == [], errors
        report.passed('cleared-drafts-permit-real-reload', page,
                      synthetic_candidate=candidate.version,
                      task_count=len(expected['tasks']), saved_view_count=len(expected['views']))
    except Exception:
        page.screenshot(path=str(report.directory / 'failure.png'))
        raise
    finally:
        server.release_resource.set()
        report.data['http_requests'] = server.requests
        report.data['page_errors'] = errors
        report.data['native_dialogs'] = dialogs
        report.write()
        context.close()
        server.stop()


def assert_waiting_update(browser, release, report):
    candidate = next_bundle(release)
    files = dict(candidate.files)
    worker = files['sw.js'].decode()
    assert worker.count('await self.skipWaiting();') == 2, 'Waiting-worker fixture must change only the two install activation calls'
    files['sw.js'] = worker.replace('await self.skipWaiting();',
                                   '/* Synthetic fixture: remain waiting until the user applies. */').encode()
    waiting = Bundle(files, candidate.version, candidate.resources)
    server = UpdateServer(release)
    server.start()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                  locale='en-US', reduced_motion='reduce')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        expected = seed_workspace(page, server, release)
        server.bundle = waiting
        check_update(page, 'ready')
        page.wait_for_function("async () => (await navigator.serviceWorker.getRegistration()).waiting?.state === 'installed'")
        assert app_version(page) == release.version
        context.set_offline(True)
        page.locator('#dismissUpdateBtn').click()
        check_update(page, 'ready')
        expect(page.locator('#updatePrompt')).to_be_visible()
        report.passed('existing-waiting-update-ready-offline', page,
                      synthetic_candidate=candidate.version,
                      fixture='Only the fixture install handler omits its two skipWaiting calls')
        with page.expect_navigation(wait_until='domcontentloaded'):
            page.locator('#settingsUpdateNowBtn').click()
        wait_for_app_ready(page)
        assert app_version(page) == candidate.version
        assert workspace(page) == expected
        assert errors == [], errors
        report.passed('waiting-update-activates-and-reloads-offline', page,
                      synthetic_candidate=candidate.version)
    except Exception:
        page.screenshot(path=str(report.directory / 'failure-waiting.png'))
        raise
    finally:
        report.data['waiting_fixture_http_requests'] = server.requests
        report.data['waiting_fixture_page_errors'] = errors
        report.write()
        context.close()
        server.stop()


def assert_initial_storage_fallback(browser, release, report):
    candidate = next_bundle(release)
    server = UpdateServer(release)
    server.start()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                  locale='en-US', reduced_motion='reduce')
    context.add_init_script("""(() => {
        const open = IDBFactory.prototype.open;
        IDBFactory.prototype.open = function(name, ...args) {
            if (name === 'TaskTrackerDB') {
                throw new DOMException('Synthetic initial database denial', 'SecurityError');
            }
            return open.call(this, name, ...args);
        };
    })();""")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(server.url)
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        page.wait_for_function("async () => navigator.serviceWorker.controller && (await navigator.serviceWorker.ready).active?.state === 'activated'")
        before = len(server.requests)
        check_update(page, 'latest')
        assert any(path == '/sw.js' and status == 200 for _, path, status in server.requests[before:])
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        report.passed('initial-storage-fallback-checks-latest', page,
                      fixture='TaskTrackerDB open throws SecurityError before initialization')
        context.set_offline(True)
        check_update(page, 'offline')
        report.passed('initial-storage-fallback-checks-offline', page)
        context.set_offline(False)

        server.bundle = candidate
        check_update(page, 'ready')
        expect(page.locator('#updatePrompt')).to_be_visible()
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        assert app_version(page) == release.version
        report.passed('initial-storage-fallback-finds-update', page,
                      synthetic_candidate=candidate.version)
        with page.expect_navigation(wait_until='domcontentloaded'):
            page.locator('#settingsUpdateNowBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        assert app_version(page) == candidate.version
        assert errors == [], errors
        report.passed('initial-storage-fallback-applies-update', page,
                      synthetic_candidate=candidate.version)
    except Exception:
        page.screenshot(path=str(report.directory / 'failure-initial-storage-fallback.png'))
        raise
    finally:
        report.data['initial_storage_fallback_http_requests'] = server.requests
        report.data['initial_storage_fallback_page_errors'] = errors
        report.write()
        context.close()
        server.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()
    release = current_bundle()
    report = Report(args.report_dir, release)
    with sync_playwright() as playwright:
        browser = None
        try:
            browser = playwright.chromium.launch(**browser_launch_options())
            assert_manual_update(browser, release, report)
            assert_waiting_update(browser, release, report)
            assert_initial_storage_fallback(browser, release, report)
            report.data['status'] = 'passed'
        except Exception:
            report.data['status'] = 'failed'
            report.data['failure'] = traceback.format_exc()
            raise
        finally:
            report.data['finished_at'] = datetime.now(timezone.utc).isoformat()
            report.write()
            if browser is not None:
                browser.close()
    print(f'Report: {report.directory / "report.json"}', flush=True)


if __name__ == '__main__':
    main()
