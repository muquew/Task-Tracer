#!/usr/bin/env python3
"""Check direct task creation and optional capture without a large task workload.

Composition checks use browser DOM events; they do not emulate a native OS IME.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

from playwright.sync_api import expect, sync_playwright

from ime_input_playwright import compose, key
from smoke_playwright import (
    REPO_ROOT, browser_launch_options, clear_app_data, close_workspace_navigation,
    ensure_capture, get_task_records, local_server, open_settings,
    return_to_task_workspace, select_view,
)
from task_draft_playwright import inject_quota_failure


def records_unchanged(page, before, phase):
    assert get_task_records(page) == before, f'{phase} changed stored tasks'


def direct_editor(page):
    close_workspace_navigation(page)
    expect(page.locator('#openModalBtn')).to_have_count(1)
    expect(page.locator('#openModalBtn')).to_be_visible()
    expect(page.locator('#openModalBtn')).to_have_attribute('aria-controls', 'taskModal')
    page.locator('#openModalBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#captureShelf')).to_be_hidden()
    expect(page.locator('#taskName')).to_be_focused()


def cancel_empty(page):
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#captureShelf')).to_be_hidden()
    expect(page.locator('#openModalBtn')).to_be_focused()
    expect(page.locator('#draftDiscardPrompt')).to_have_count(0)


def check_views(page, output, width):
    before = get_task_records(page)
    for view in ('list', 'calendar', 'timeline', 'stats'):
        select_view(page, view)
        direct_editor(page)
        expect(page.locator('#taskName')).to_have_value('')
        expect(page.locator('#taskProject')).to_have_value('Inbox')
        expect(page.locator('#noDeadline')).to_be_checked()
        if view == 'list':
            page.screenshot(path=str(output / f'{width}-direct-editor.png'))
        cancel_empty(page)
        expect(page.locator(f'#viewTab-{view}')).to_have_attribute('aria-current', 'page')
        records_unchanged(page, before, f'Opening and cancelling from {view}')
    open_settings(page, 'appearance')
    direct_editor(page)
    cancel_empty(page)
    expect(page.locator('#settingsWorkspace')).to_be_visible()
    records_unchanged(page, before, 'Opening and cancelling from settings')
    return_to_task_workspace(page)
    select_view(page, 'list')


def check_capture_draft(page, output, width):
    before = get_task_records(page)
    raw = '  明天 20:00 核对发布说明 #待办 /个人  '
    tomorrow = page.evaluate("""() => {
        const date = new Date(); date.setDate(date.getDate() + 1);
        return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
            String(date.getDate()).padStart(2, '0')].join('-');
    }""")
    ensure_capture(page).fill(raw)
    expect(page.locator('#quickCaptureBtn')).to_have_attribute('aria-expanded', 'true')
    direct_editor(page)
    expect(page.locator('#taskName')).to_have_value('核对发布说明')
    expect(page.locator('#taskProject')).to_have_value('个人')
    expect(page.locator('#taskTags')).to_have_value('待办')
    expect(page.locator('#dueDate')).to_have_value(tomorrow)
    expect(page.locator('#dueTime')).to_have_value('20:00')
    page.screenshot(path=str(output / f'{width}-continued-draft.png'))
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#captureShelf')).to_be_visible()
    expect(page.locator('#quickAddInput')).to_have_value(raw)
    expect(page.locator('#quickAddInput')).to_be_focused()
    records_unchanged(page, before, 'Cancelling a continued capture')

    # The existing keyboard shortcut intentionally creates an independent form.
    page.keyboard.press('Control+i')
    expect(page.locator('#taskName')).to_have_value('')
    expect(page.locator('#quickAddInput')).to_have_value(raw)
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#quickAddInput')).to_have_value(raw)
    records_unchanged(page, before, 'Cancelling the independent keyboard form')

    direct_editor(page)
    page.locator('#taskName').fill('An unsaved edit of the parsed task')
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#quickAddInput')).to_have_value(raw)
    records_unchanged(page, before, 'Discarding a form edit preserves the raw capture')

    direct_editor(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#quickAddInput')).to_have_value('')
    after = get_task_records(page)
    assert len(after) == len(before) + 1 and all(task in after for task in before)
    added = next(task for task in after if task not in before)
    assert added['name'] == '核对发布说明' and added['project'] == '个人'
    assert added['tags'] == ['待办'] and added['dueLocalDate'] == tomorrow
    assert added['dueLocalTime'] == '20:00'
    if page.locator('#captureShelf').is_visible():
        page.locator('#captureCloseBtn').click()


def choose_calendar_capture(page):
    select_view(page, 'calendar')
    day = page.locator('.calendar-day:not(.outside-month) .calendar-date-number').first
    selected = day.get_attribute('data-calendar-add-date') or day.get_attribute('data-calendar-detail-date')
    assert selected
    day.click()
    agenda = page.locator(f'.calendar-agenda-add[data-calendar-add-date="{selected}"]')
    if agenda.is_visible():
        agenda.click()
    expect(page.locator('#captureShelf')).to_be_visible()
    return selected


def check_calendar_context(page):
    before = get_task_records(page)
    choose_calendar_capture(page)
    page.locator('#captureCloseBtn').click()
    select_view(page, 'list')
    direct_editor(page)
    expect(page.locator('#noDeadline')).to_be_checked()
    cancel_empty(page)
    records_unchanged(page, before, 'Cancelling an empty calendar capture')

    selected = choose_calendar_capture(page)
    ensure_capture(page).fill('保留选定日期的任务')
    page.locator('#captureCloseBtn').click()
    select_view(page, 'timeline')
    direct_editor(page)
    expect(page.locator('#taskName')).to_have_value('保留选定日期的任务')
    expect(page.locator('#dueDate')).to_have_value(selected)
    expect(page.locator('#noDeadline')).not_to_be_checked()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#viewTab-timeline')).to_have_attribute('aria-current', 'page')
    after = get_task_records(page)
    assert len(after) == len(before) + 1 and all(task in after for task in before)
    added = next(task for task in after if task not in before)
    assert added['name'] == '保留选定日期的任务' and added['dueLocalDate'] == selected
    if page.locator('#captureShelf').is_visible():
        page.locator('#captureCloseBtn').click()
    direct_editor(page)
    expect(page.locator('#noDeadline')).to_be_checked()
    cancel_empty(page)


def check_composition(page):
    for task_form in (False, True):
        before = get_task_records(page)
        if task_form:
            direct_editor(page)
            field, form = page.locator('#taskName'), page.locator('#taskForm')
        else:
            field, form = ensure_capture(page), page.locator('#quickAddForm')
        text = '完整表单组词任务' if task_form else '快速记录组词任务'
        field.fill(text)
        compose(field, True)
        key(field, 'Enter', 'tracked')
        key(field, 'Escape', 'tracked')
        form.evaluate('(form) => form.requestSubmit()')
        records_unchanged(page, before, 'Submitting during a tracked composition')
        expect(field).to_have_value(text)
        if task_form:
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
        compose(field, False)
        field.press('Enter')
        if task_form:
            expect(page.locator('#taskModal')).to_be_hidden()
        else:
            expect(field).to_have_value('')
        after = get_task_records(page)
        assert len(after) == len(before) + 1 and all(task in after for task in before)
        assert next(task for task in after if task not in before)['name'] == text
        if page.locator('#captureShelf').is_visible():
            page.locator('#captureCloseBtn').click()


def check_failed_storage(page):
    before = get_task_records(page)
    raw = '存储恢复后才能保存的任务 #保留 /个人'
    ensure_capture(page).fill(raw)
    inject_quota_failure(page)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    page.locator('#captureCloseBtn').click()
    expect(page.locator('#captureShelf')).to_be_hidden()
    expect(page.locator('#openModalBtn')).to_be_enabled()
    page.locator('#openModalBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    field = page.locator('#quickAddInput')
    expect(field).to_be_visible()
    expect(field).to_have_value(raw)
    expect(field).to_have_attribute('readonly', '')
    field.evaluate('(input) => input.setSelectionRange(0, input.value.length)')
    assert field.evaluate('(input) => input.value.slice(input.selectionStart, input.selectionEnd)') == raw
    records_unchanged(page, before, 'Failed storage and direct-entry read-only fallback')
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    expect(field).not_to_have_attribute('readonly', '')
    expect(field).to_have_value(raw)
    records_unchanged(page, before, 'Storage Retry')
    direct_editor(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(field).to_have_value('')
    after = get_task_records(page)
    assert len(after) == len(before) + 1 and all(task in after for task in before)
    assert next(task for task in after if task not in before)['name'] == '存储恢复后才能保存的任务'


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    index_hash = hashlib.sha256((REPO_ROOT / 'index.html').read_bytes()).hexdigest()
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'index_sha256': index_hash,
              'composition_scope': 'Browser DOM composition events; no native OS IME',
              'passed': False, 'runs': []}
    selected_url = args.url or os.environ.get('TASK_TRACER_URL')
    server = contextlib.nullcontext(selected_url) if selected_url else local_server()
    try:
        with server as url, sync_playwright() as playwright:
            options = browser_launch_options()
            if args.executable:
                options['executable_path'] = args.executable
            browser = playwright.chromium.launch(**options)
            report['browser'] = {'engine': 'chromium', 'version': browser.version}
            for width in args.widths:
                context = browser.new_context(viewport={'width': width, 'height': 900 if width == 1280 else 844},
                                              timezone_id='UTC', reduced_motion='reduce')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                entry = {'width': width, 'passed': False, 'checks': [], 'page_errors': errors}
                report['runs'].append(entry)
                try:
                    clear_app_data(page, url)
                    expect(page.locator('#quickCaptureBtn')).to_be_visible()
                    for name, check in (
                        ('direct entry and cancel retain all four views and settings', lambda: check_views(page, args.output, width)),
                        ('parsed quick draft, cancel/discard, independent shortcut, explicit save', lambda: check_capture_draft(page, args.output, width)),
                        ('calendar draft retains date; cancelled/saved date never leaks', lambda: check_calendar_context(page)),
                        ('quick and full forms preserve active composition then save once', lambda: check_composition(page)),
                        ('failed storage reopens selectable text; Retry retains; explicit save once', lambda: check_failed_storage(page)),
                    ):
                        started = time.perf_counter()
                        check()
                        entry['checks'].append({'name': name, 'passed': True, 'seconds': round(time.perf_counter() - started, 2)})
                        print(f'Direct capture {width}px passed: {name}', flush=True)
                    assert not errors, errors
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Workspace overflows the viewport'
                    page.screenshot(path=str(args.output / f'{width}-complete.png'))
                    entry['tasks_saved'] = len(get_task_records(page))
                    entry['passed'] = True
                except Exception:
                    page.screenshot(path=str(args.output / f'{width}-failure.png'))
                    raise
                finally:
                    context.close()
            browser.close()
        assert hashlib.sha256((REPO_ROOT / 'index.html').read_bytes()).hexdigest() == index_hash, 'Application source changed during the run'
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-4.13.1-capture'))
    parser.add_argument('--widths', type=int, nargs='+', default=[1280, 390, 320])
    parser.add_argument('--url')
    parser.add_argument('--executable', help='Optional installed Chromium executable')
    run(parser.parse_args())
