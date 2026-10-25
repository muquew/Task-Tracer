#!/usr/bin/env python3
"""Protect project and Today-plan context when creating or recovering tasks."""
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

from direct_capture_playwright import cancel_empty, direct_editor, records_unchanged
from smoke_playwright import (
    REPO_ROOT, browser_launch_options, clear_app_data, ensure_capture,
    get_task_records, local_server, reveal_workspace_control, select_filter,
    select_project, task_locator,
)
from task_draft_playwright import downloaded_drafts, inject_quota_failure


PROJECT = '当前项目'


def assert_added(page, before, name, project, focus_date=None):
    after = get_task_records(page)
    added = [task for task in after if task['id'] not in {item['id'] for item in before}]
    assert len(after) == len(before) + 1 and len(added) == 1
    assert all(task in after for task in before), 'Creating a task changed an existing record'
    task = added[0]
    assert task['name'] == name and task['project'] == project, task
    assert task.get('focusDate') == focus_date, task
    return task


def save_form(page, name, project, focus_date=None, *, override_project=None):
    before = get_task_records(page)
    direct_editor(page)
    expect(page.locator('#taskProject')).to_have_value(project)
    page.locator('#taskName').fill(name)
    if override_project is not None:
        page.locator('#taskProject').fill(override_project)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    if page.locator('#captureShelf').is_visible():
        page.locator('#captureCloseBtn').click()
    return assert_added(page, before, name, project if override_project is None else override_project, focus_date)


def save_quick(page, name, project, focus_date=None, *, explicit_project=None):
    before = get_task_records(page)
    text = name + (f' /{explicit_project}' if explicit_project is not None else '')
    ensure_capture(page).fill(text)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    page.locator('#captureCloseBtn').click()
    return assert_added(page, before, name, project if explicit_project is None else explicit_project, focus_date)


def seed_projects(page):
    save_form(page, 'Outside Today: assigned baseline', 'Inbox', override_project=PROJECT)
    save_form(page, 'Outside Today: unassigned baseline', 'Inbox', override_project='')


def check_project_scopes(page):
    for scope, expected, label in (('all', 'Inbox', 'All'), (PROJECT, PROJECT, 'Project'), ('__none__', '', 'Unassigned')):
        select_project(page, scope)
        before = get_task_records(page)
        direct_editor(page)
        expect(page.locator('#taskProject')).to_have_value(expected)
        cancel_empty(page)
        records_unchanged(page, before, f'{label} empty cancellation')
        form_name, quick_name = f'{label} form creation', f'{label} quick creation'
        save_form(page, form_name, expected)
        expect(task_locator(page, form_name)).to_be_visible()
        save_quick(page, quick_name, expected)
        expect(task_locator(page, quick_name)).to_be_visible()
        # A later form must still inherit the same scope after each successful save.
        before = get_task_records(page)
        direct_editor(page)
        expect(page.locator('#taskProject')).to_have_value(expected)
        cancel_empty(page)
        records_unchanged(page, before, f'{label} scope inspection')


def check_explicit_project(page):
    select_project(page, PROJECT)
    save_quick(page, 'Explicit slash project overrides scope', PROJECT, explicit_project='显式项目')
    expect(task_locator(page, 'Explicit slash project overrides scope')).to_have_count(0)
    before = get_task_records(page)
    ensure_capture(page).fill('2032-04-09 14:25 显式项目草稿 /显式项目 #检查')
    direct_editor(page)
    expect(page.locator('#taskProject')).to_have_value('显式项目')
    expect(page.locator('#taskName')).to_have_value('显式项目草稿')
    expect(page.locator('#dueDate')).to_have_value('2032-04-09')
    page.locator('#cancelBtn').click()
    expect(page.locator('#quickAddInput')).to_have_value('2032-04-09 14:25 显式项目草稿 /显式项目 #检查')
    records_unchanged(page, before, 'Cancelling an explicit-project capture handoff')
    direct_editor(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#quickAddInput')).to_have_value('')
    assert_added(page, before, '显式项目草稿', '显式项目')
    select_project(page, 'all')
    expect(task_locator(page, 'Explicit slash project overrides scope')).to_be_visible()
    expect(task_locator(page, '显式项目草稿')).to_be_visible()


def enter_today(page):
    if page.locator('#focusModeToggleBtn').get_attribute('aria-pressed') != 'true':
        reveal_workspace_control(page, '#focusModeToggleBtn').click()
    expect(page.locator('#focusModeBar')).to_be_visible()
    expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'true')


def today_key(page):
    return page.evaluate("""() => {
        const date = new Date();
        return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
            String(date.getDate()).padStart(2, '0')].join('-');
    }""")


def check_today_creation(page):
    enter_today(page)
    today = today_key(page)
    before = get_task_records(page)
    direct_editor(page)
    cancel_empty(page)
    records_unchanged(page, before, 'Today empty cancellation')
    save_form(page, 'Today all-project form creation', 'Inbox', today)
    expect(task_locator(page, 'Today all-project form creation')).to_be_visible()
    save_quick(page, 'Planned all-project quick creation', 'Inbox', today)
    expect(task_locator(page, 'Planned all-project quick creation')).to_be_visible()
    select_project(page, PROJECT)
    save_form(page, 'Today project form creation', PROJECT, today)
    expect(task_locator(page, 'Today project form creation')).to_be_visible()
    save_quick(page, 'Planned project quick creation', PROJECT, today)
    expect(task_locator(page, 'Planned project quick creation')).to_be_visible()
    select_project(page, '__none__')
    save_form(page, 'Today unassigned form creation', '', today)
    expect(task_locator(page, 'Today unassigned form creation')).to_be_visible()
    save_quick(page, 'Planned unassigned quick creation', '', today)
    expect(task_locator(page, 'Planned unassigned quick creation')).to_be_visible()
    select_project(page, 'all')
    expect(task_locator(page, 'Outside Today: assigned baseline')).to_have_count(0)
    expect(task_locator(page, 'Outside Today: unassigned baseline')).to_have_count(0)


def check_today_no_matches(page, output, width):
    before = get_task_records(page)
    enter_today(page)
    for constrain in ('search', 'status', 'project'):
        if constrain == 'search':
            page.locator('#searchInput').fill('No matching planned task 938514')
        elif constrain == 'status':
            select_filter(page, 'completed')
        else:
            select_project(page, '显式项目')
        expect(page.locator('#taskList .empty-state h2')).to_have_text('没有匹配的任务')
        expect(page.locator('#taskList [data-reset-filters="today"]')).to_be_visible()
        if constrain == 'search':
            page.screenshot(path=str(output / f'{width}-today-no-matches.png'))
        page.locator('#taskList [data-reset-filters="today"]').click()
        expect(page.locator('#searchInput')).to_have_value('')
        expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#focusModeBar')).to_be_visible()
        expect(task_locator(page, 'Today all-project form creation')).to_be_visible()
        expect(task_locator(page, 'Planned project quick creation')).to_be_visible()
        expect(task_locator(page, 'Outside Today: assigned baseline')).to_have_count(0)
        records_unchanged(page, before, f'Resetting Today {constrain} constraints')


def check_today_recovery(page):
    enter_today(page)
    select_project(page, PROJECT)
    today = today_key(page)
    before = get_task_records(page)
    direct_editor(page)
    page.locator('#taskName').fill('Recovered Today project draft')
    page.locator('#taskDesc').fill('This unsaved form retains its original plan and project.')
    inject_quota_failure(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    drafts = downloaded_drafts(page)
    assert len(drafts) == 1 and drafts[0]['creationFocusDate'] == today
    assert drafts[0]['form']['values']['project'] == PROJECT
    records_unchanged(page, before, 'Failed Today draft save')
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    # Resume in a different context to prove recovery uses the original draft.
    page.locator('#exitFocusModeBtn').click()
    select_project(page, '__none__')
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskName')).to_have_value('Recovered Today project draft')
    expect(page.locator('#taskProject')).to_have_value(PROJECT)
    records_unchanged(page, before, 'Retry and resume a Today draft')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
    assert_added(page, before, 'Recovered Today project draft', PROJECT, today)
    enter_today(page)
    expect(task_locator(page, 'Recovered Today project draft')).to_be_visible()


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((REPO_ROOT / 'index.html').read_bytes()).hexdigest()
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'index_sha256': digest, 'passed': False, 'runs': []}
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
                                              timezone_id='UTC', reduced_motion='reduce', accept_downloads=True)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                entry = {'width': width, 'passed': False, 'checks': [], 'page_errors': errors}
                report['runs'].append(entry)
                try:
                    clear_app_data(page, url)
                    seed_projects(page)
                    for name, check in (
                        ('All, project and unassigned form/quick creation retain their scope; cancel never writes', lambda: check_project_scopes(page)),
                        ('Explicit slash project overrides current scope and survives cancelled handoff', lambda: check_explicit_project(page)),
                        ('Today forms and quick capture inherit focusDate across all/project/unassigned scopes', lambda: check_today_creation(page)),
                        ('Today no-match search/status/project reset restores tasks while retaining the plan', lambda: check_today_no_matches(page, args.output, width)),
                        ('Failed Today form retains original focusDate and project through recovery in another scope', lambda: check_today_recovery(page)),
                    ):
                        started = time.perf_counter()
                        check()
                        entry['checks'].append({'name': name, 'passed': True, 'seconds': round(time.perf_counter() - started, 2)})
                        print(f'Creation context {width}px passed: {name}', flush=True)
                    assert not errors, errors
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Workspace overflows the viewport'
                    page.screenshot(path=str(args.output / f'{width}-today-recovered.png'))
                    entry['tasks_saved'] = len(get_task_records(page))
                    entry['passed'] = True
                except Exception:
                    page.screenshot(path=str(args.output / f'{width}-failure.png'))
                    raise
                finally:
                    context.close()
            browser.close()
        assert hashlib.sha256((REPO_ROOT / 'index.html').read_bytes()).hexdigest() == digest, 'Application source changed during the run'
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-context-creation'))
    parser.add_argument('--widths', type=int, nargs='+', default=[1280, 390, 320])
    parser.add_argument('--url')
    parser.add_argument('--executable', help='Optional installed Chromium executable')
    run(parser.parse_args())
