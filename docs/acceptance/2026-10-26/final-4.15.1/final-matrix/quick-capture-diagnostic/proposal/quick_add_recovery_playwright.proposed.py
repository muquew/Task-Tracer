#!/usr/bin/env python3
"""Preserve raw quick-add text and capture metadata through storage failures."""
from __future__ import annotations

from smoke_playwright import open_task_editor, ensure_capture

import argparse
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import Error, expect, sync_playwright

import smoke_playwright as smoke
from recovery_management_playwright import config, stored
from task_draft_playwright import downloaded_drafts, inject_quota_failure, unload_is_guarded

RAW_TEXT = '  明天 20:00 复核 快速输入 #待办 /个人  '
RAW_NAME = '复核 快速输入'


def mark_document(page):
    page.evaluate('window.quickAddRecoveryOriginalDocument = true')


def assert_same_document(page):
    assert page.evaluate('window.quickAddRecoveryOriginalDocument === true'), 'Storage Retry reloaded away the in-memory quick-add text or metadata'


def prepare(page, url):
    smoke.clear_app_data(page, url)
    smoke.add_task(page, 'Existing task protected during quick-add Retry', no_deadline=True)
    mark_document(page)
    assert not unload_is_guarded(page)
    return stored(page)


def fail_quick_add(page, raw=RAW_TEXT):
    ensure_capture(page)
    page.locator('#quickAddInput').fill(raw)
    inject_quota_failure(page)
    ensure_capture(page)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#quickAddInput')).to_have_value(raw)


def assert_retained_readonly(page, raw=RAW_TEXT):
    field = page.locator('#quickAddInput')
    expect(field).to_be_enabled()
    expect(field).to_have_attribute('readonly', '')
    expect(field).to_have_attribute('aria-disabled', 'false')
    expect(field).to_have_value(raw)
    expect(page.locator('#quickAddForm button[type="submit"]')).to_be_disabled()
    expect(page.locator('#quickAddRetainedMessage')).to_be_visible()
    field.focus()
    field.evaluate('(input) => input.setSelectionRange(0,input.value.length)')
    expect(field).to_be_focused()
    assert field.evaluate('(input) => input.value.slice(input.selectionStart,input.selectionEnd)') == raw, 'The read-only retained input cannot be selected for copying'
    assert unload_is_guarded(page)
    assert_same_document(page)


def retry(page, before, raw=RAW_TEXT):
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    smoke.wait_for_app_ready(page)
    field = page.locator('#quickAddInput')
    expect(field).to_be_enabled()
    expect(field).not_to_have_attribute('readonly', '')
    expect(field).to_have_value(raw)
    expect(page.locator('#quickAddForm button[type="submit"]')).to_be_enabled()
    assert_same_document(page)
    assert stored(page) == before, 'Retry changed task records, history, backup metadata or configuration without a task submission'
    assert unload_is_guarded(page)


def submit_and_check(page, before, name=RAW_NAME, description='', project='个人', tags=None):
    ensure_capture(page)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    expect(page.locator('#quickAddForm button[type="submit"]')).to_be_enabled()
    after = stored(page)
    added = [task for task in after['tasks'] if task['id'] not in {task['id'] for task in before['tasks']}]
    assert len(added) == 1 and len(after['tasks']) == len(before['tasks']) + 1, 'One recovered submission added zero or duplicate tasks'
    task = added[0]
    assert task['name'] == name and task['description'] == description
    assert task['project'] == project and task['tags'] == (tags if tags is not None else ['待办'])
    for original in before['tasks']:
        assert next(item for item in after['tasks'] if item['id'] == original['id']) == original
    assert config(after)['taskRevision'] == config(before)['taskRevision'] + 1
    assert not unload_is_guarded(page), 'A successfully saved and emptied quick-add input still blocked departure'
    return task


def quick_add_only(page, url):
    before = prepare(page, url)
    tomorrow = page.evaluate("""() => {
        const date = new Date(); date.setDate(date.getDate()+1);
        return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
    }""")
    fail_quick_add(page)
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
    assert stored(page) == before, 'The failed quick-add transaction partially wrote task/history/configuration'
    assert_retained_readonly(page)
    # A second attempted submit while unavailable must not write or consume text.
    page.locator('#quickAddForm').evaluate("form => form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    expect(page.locator('#quickAddInput')).to_have_value(RAW_TEXT)
    assert stored(page) == before
    retry(page,before)
    task = submit_and_check(page,before)
    assert task['dueLocalDate'] == tomorrow and task['dueLocalTime'] == '20:00'
    # A normal later submission must still have exactly one effective listener.
    next_before = stored(page)
    ensure_capture(page)
    page.locator('#quickAddInput').fill('Another recovered quick-add task')
    submit_and_check(page,next_before,name='Another recovered quick-add task',project='Inbox',tags=[])
    print('Quick-add recovery passed: exact raw text, selectable read-only fallback, same-document Retry and one task per normal submission',flush=True)


def coexist_with_form(page, url):
    before = prepare(page,url)
    ensure_capture(page)
    page.locator('#quickAddInput').fill(RAW_TEXT)
    if page.locator('#captureShelf').count():
        # Ctrl+I starts an independent form; More options continues this capture.
        page.keyboard.press('Control+i')
        expect(page.locator('#taskModal')).to_be_visible()
    else:
        open_task_editor(page)
    page.locator('#taskName').fill('Coexisting full form 保留')
    page.locator('#taskDesc').fill('  Keep this separate raw form text  ')
    page.locator('#noDeadline').check()
    page.locator('#subtaskInput').fill('Unsubmitted partial subtask')
    inject_quota_failure(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    assert_retained_readonly(page)
    drafts = downloaded_drafts(page)
    assert len(drafts) == 1
    assert drafts[0]['form']['values']['name'] == 'Coexisting full form 保留'
    assert drafts[0]['form']['values']['desc'] == '  Keep this separate raw form text  '
    assert stored(page) == before
    retry(page,before)
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_enabled()
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskName')).to_have_value('Coexisting full form 保留')
    expect(page.locator('#taskDesc')).to_have_value('  Keep this separate raw form text  ')
    expect(page.locator('#subtaskInput')).to_have_value('Unsubmitted partial subtask')
    expect(page.locator('#quickAddInput')).to_have_value(RAW_TEXT)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
    after_form = stored(page)
    assert len(after_form['tasks']) == len(before['tasks']) + 1
    assert len([task for task in after_form['tasks'] if task['name'] == 'Coexisting full form 保留']) == 1
    assert unload_is_guarded(page), 'Saving the full form incorrectly removed quick-add departure protection'
    submit_and_check(page,after_form)
    print('Quick-add recovery passed: quick-add and full-form drafts coexist and recover without overwriting one another',flush=True)


def failed_retry(page, url):
    before = prepare(page,url)
    fail_quick_add(page)
    assert_retained_readonly(page)
    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.put;
        window.quickAddRetryFailureCount = 0;
        IDBObjectStore.prototype.put = function(value,...args) {
            if (this.name === 'config' && value?.key === '__task_tracer_storage_probe__') {
                IDBObjectStore.prototype.put = original;
                window.quickAddRetryFailureCount += 1;
                throw new DOMException('Synthetic one-shot Retry quota failure','QuotaExceededError');
            }
            return original.call(this,value,...args);
        };
    }""")
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#retryStorageBtn')).to_be_enabled()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    assert page.evaluate('window.quickAddRetryFailureCount') == 1
    assert_retained_readonly(page)
    assert stored(page) == before
    retry(page,before)
    submit_and_check(page,before)
    print('Quick-add recovery passed: failed Retry retains raw text and a later successful Retry still saves exactly once',flush=True)


def native_beforeunload(page, url):
    before = prepare(page,url)
    dialogs = []

    def cancel_departure(dialog):
        dialogs.append(dialog.type)
        dialog.dismiss()

    page.on('dialog',cancel_departure)
    try:
        page.reload(wait_until='domcontentloaded')
        smoke.wait_for_app_ready(page)
        assert dialogs == [], 'An empty quick-add input blocked departure'
        mark_document(page)
        ensure_capture(page)
        page.locator('#quickAddInput').click()
        ensure_capture(page)
        page.locator('#quickAddInput').fill(RAW_TEXT)
        assert unload_is_guarded(page)
        for unavailable in (False,True):
            if unavailable:
                inject_quota_failure(page)
                ensure_capture(page)
                page.locator('#quickAddInput').press('Enter')
                expect(page.locator('#storageUnavailableBanner')).to_be_visible()
                assert_retained_readonly(page)
            previous_dialogs = len(dialogs)
            try:
                page.reload(timeout=10000,wait_until='domcontentloaded')
            except Error as error:
                if len(dialogs) == previous_dialogs:
                    raise AssertionError(f'Reload failed without a native departure dialog: {error}') from error
            assert dialogs[previous_dialogs:] == ['beforeunload'], 'The engine did not present the actual quick-add departure warning'
            assert_same_document(page)
            expect(page.locator('#quickAddInput')).to_have_value(RAW_TEXT)
            assert stored(page) == before
        retry(page,before)
        submit_and_check(page,before)
        page.reload(wait_until='domcontentloaded')
        smoke.wait_for_app_ready(page)
        assert dialogs == ['beforeunload','beforeunload']
    finally:
        page.remove_listener('dialog',cancel_departure)
    print('Quick-add recovery passed: actual native refresh cancellation preserves editable and unavailable read-only drafts; saved text no longer warns',flush=True)


def capture_metadata(page, url):
    prepare(page,url)
    title = '分享标题 复核'
    body = '分享正文 重要信息'
    shared_url = 'https://example.com/synthetic-capture?source=quick-recovery'
    page.goto(url+'?'+urlencode({'capture':'1','title':title,'text':body,'url':shared_url}),wait_until='domcontentloaded')
    smoke.wait_for_app_ready(page)
    expect(page.locator('#quickAddInput')).to_have_value(title)
    assert page.evaluate('location.search') == ''
    expect(page.locator('#captureShelf')).to_be_visible()
    expect(page.locator('#quickAddInput')).to_be_focused()
    mark_document(page)
    before = stored(page)
    raw = '  '+title+'  '
    fail_quick_add(page,raw)
    assert_retained_readonly(page,raw)
    assert stored(page) == before
    retry(page,before,raw)
    submit_and_check(page,before,name=title,description=body+'\n'+shared_url,project='Inbox',tags=[])
    assert page.evaluate('location.search') == ''
    page.reload(wait_until='domcontentloaded')
    smoke.wait_for_app_ready(page)
    assert len([task for task in smoke.get_task_records(page) if task['name'] == title]) == 1
    print('Quick-add recovery passed: cleared URL parameters cannot erase retained capture description/URL metadata, and reload cannot duplicate the saved task',flush=True)


def empty_input(page, url):
    before = prepare(page,url)
    ensure_capture(page)
    page.locator('#quickAddInput').fill('   ')
    assert not unload_is_guarded(page), 'Whitespace without a task unexpectedly blocked departure'
    ensure_capture(page)
    page.locator('#quickAddInput').fill('')
    page.add_init_script("""(() => {
        if (sessionStorage.getItem('__quick_empty_quota_seen') === 'yes') return;
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(value,...args) {
            if (this.name === 'config' && value?.key === '__task_tracer_storage_probe__') {
                IDBObjectStore.prototype.put = original;
                sessionStorage.setItem('__quick_empty_quota_seen','yes');
                throw new DOMException('Synthetic one-shot startup quota failure','QuotaExceededError');
            }
            return original.call(this,value,...args);
        };
    })();""")
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#quickAddInput')).to_be_disabled()
    expect(page.locator('#quickAddInput')).not_to_have_attribute('readonly','')
    expect(page.locator('#quickAddRetainedMessage')).to_be_hidden()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
    assert not unload_is_guarded(page)
    assert stored(page) == before
    mark_document(page)
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    smoke.wait_for_app_ready(page)
    expect(page.locator('#quickAddInput')).to_be_enabled()
    expect(page.locator('#quickAddInput')).to_have_value('')
    assert not page.evaluate('window.quickAddRecoveryOriginalDocument === true'), 'An empty workspace unexpectedly changed the existing reload recovery path'
    assert stored(page) == before
    print('Quick-add recovery passed: empty unavailable input stays disabled and keeps the established no-draft Retry path',flush=True)


CASES = {'quota':quick_add_only,'coexist':coexist_with_form,'retry':failed_retry,
         'unload':native_beforeunload,'capture':capture_metadata,'empty':empty_input}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=['chromium','firefox','webkit'],default='chromium')
    parser.add_argument('--case',choices=['all',*CASES],default='all')
    parser.add_argument('--source-root',type=Path,help='Serve a prepared isolated static copy; never modify that copy or the main working tree')
    args = parser.parse_args()
    if args.source_root:
        candidate = args.source_root.resolve()
        assert (candidate/'index.html').is_file()
        smoke.REPO_ROOT = candidate
    expect.set_options(timeout=15000)
    with smoke.local_server() as url, sync_playwright() as playwright:
        options = smoke.browser_launch_options() if args.browser == 'chromium' else {'headless':True}
        browser = getattr(playwright,args.browser).launch(**options)
        print(f'{args.browser}: quick-add recovery on {browser.version}',flush=True)
        try:
            cases = CASES.items() if args.case == 'all' else [(args.case,CASES[args.case])]
            for name,operation in cases:
                context = browser.new_context(accept_downloads=True,reduced_motion='reduce',timezone_id='UTC')
                errors = []
                try:
                    page = context.new_page()
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    operation(page,url)
                    assert not errors,(name,errors)
                finally:
                    context.close()
        finally:
            browser.close()
    print(f'{args.browser}: all selected quick-add recovery checks passed',flush=True)


if __name__ == '__main__':
    main()
