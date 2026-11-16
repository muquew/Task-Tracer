#!/usr/bin/env python3
"""Trace completion history through visible dates without changing stored data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from recovery_management_playwright import stored
from smoke_playwright import (
    add_task, browser_launch_options, ensure_capture, get_task_records, local_server,
    navigate_workbench, select_filter, select_language, select_project, wait_for_app_ready,
)
from workbench_navigation_playwright import capture


QUERY = 'tag:review due:none'
ZONE = 'Asia/Shanghai'


def seed(page, fixtures):
    add_task(page, 'Completion history template', no_deadline=True)
    template = get_task_records(page)[0]
    records = []
    for identity, name, completed_at, archived, project, tag, completed in fixtures:
        records.append({**template, 'id': identity, 'name': name,
                        'description': 'Synthetic completion history fixture',
                        'completed': completed, 'completedAt': completed_at,
                        'archived': archived, 'archivedAt': '2026-11-17T01:00:00.000Z' if archived else None,
                        'project': project, 'tags': [tag], 'order': identity * 1000,
                        'focusDate': None})
    page.evaluate("""records => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const tasks = tx.objectStore('tasks');
            tasks.clear();
            records.forEach(record => tasks.put(record));
            const config = tx.objectStore('config');
            const revision = config.get('taskRevision');
            revision.onsuccess = () => config.put({key: 'taskRevision', value: (revision.result?.value || 0) + 1});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", records)
    page.reload()
    wait_for_app_ready(page)


def assert_ids(page, expected):
    expect(page.locator('.task-item')).to_have_count(len(expected))
    actual = set(page.locator('.task-item').evaluate_all('tasks => tasks.map(task => Number(task.dataset.taskId))'))
    assert actual == set(expected), f'Unexpected completion history records: {actual}, expected {expected}'


def scope(page):
    return {'query': page.locator('#searchInput').input_value(),
            'project': page.locator('#projectDropdown [aria-selected="true"]').get_attribute('data-project'),
            'filter': page.locator('#filterDropdown [aria-selected="true"]').get_attribute('data-filter')}


def open_history(page, selector, expected, token, before, keyboard=False):
    control = page.locator(selector)
    expect(control).to_be_enabled()
    control.evaluate("element => element.scrollIntoView({block: 'center', behavior: 'instant'})")
    control.focus()
    origin = {'scope': scope(page), 'scroll': page.evaluate('scrollY')}
    control.evaluate("""element => {
        delete window.reviewHistoryClickedScroll;
        element.addEventListener('click', () => {window.reviewHistoryClickedScroll = scrollY;}, {capture: true, once: true});
    }""")
    if keyboard:
        page.keyboard.press('Enter')
    else:
        control.click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'tasks')
    expect(page.locator('#workspaceTitle')).to_be_focused()
    expect(page.locator('#statsReturnBar')).to_be_visible()
    origin['clicked_scroll'] = page.evaluate('window.reviewHistoryClickedScroll')
    expect(page.locator('#searchInput')).to_have_value(f"{origin['scope']['query']} {token}")
    assert scope(page)['project'] == origin['scope']['project'], 'History lost the project scope'
    assert_ids(page, expected)
    assert stored(page) == before, 'Opening completion history wrote tasks or configuration'
    return origin


def return_to_review(page, selector, origin, before):
    page.locator('#statsReturnBtn').click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'review')
    expect(page.locator(selector)).to_be_focused()
    assert scope(page) == origin['scope'], 'Return did not restore the original search/project/filter scope'
    try:
        page.wait_for_function("""original => Math.abs(scrollY - Math.min(original,
            Math.max(0, document.scrollingElement.scrollHeight - document.scrollingElement.clientHeight))) <= 1""", arg=origin['clicked_scroll'])
    except Exception as error:
        geometry = page.evaluate('({scroll:scrollY, maxScroll:Math.max(0,document.scrollingElement.scrollHeight-document.scrollingElement.clientHeight), active:document.activeElement?.outerHTML})')
        raise AssertionError(f'Review return mismatch: origin={origin}, final={geometry}') from error
    assert stored(page) == before, 'Returning to Review wrote task or configuration data'


def verify_history(page, output):
    fixtures = [
        (100, 'Completed after local midnight', '2026-11-16T16:05:00.000Z', False, 'Work', 'review', True),
        (101, 'Completed before local midnight', '2026-11-16T15:55:00.000Z', False, 'Work', 'review', True),
        (102, 'Archived completion on first day', '2026-11-10T16:30:00.000Z', True, 'Work', 'review', True),
        (103, 'Older completion outside seven days', '2026-11-10T15:59:00.000Z', False, 'Work', 'review', True),
        (104, 'Completion dated tomorrow', '2026-11-17T16:01:00.000Z', False, 'Work', 'review', True),
        (105, 'Completed without recorded date', None, False, 'Work', 'review', True),
        (106, 'Unfinished with stale completion date', '2026-11-17T01:00:00.000Z', False, 'Work', 'review', False),
        (107, 'Another project completion', '2026-11-17T01:00:00.000Z', False, 'Personal', 'review', True),
        (108, 'Another tag completion', '2026-11-17T01:00:00.000Z', False, 'Work', 'other', True),
        (109, 'Metadata-like names remain separate', '2026-11-17T01:00:00.000Z', False, 'Work completed:week', 'review completed:week', True),
    ]
    seed(page, fixtures)
    navigate_workbench(page, 'review')
    select_project(page, 'Work')
    page.locator('#searchInput').fill(QUERY)
    week = 'button.stats-review-total[data-stats-action="review-week"]'
    day = 'button.stats-trend-item[data-stats-date="2026-11-16"]'
    expect(page.locator(week)).to_have_text('3 tasks completed')
    expect(page.locator('button.stats-trend-item')).to_have_count(7)
    expect(page.locator('button.stats-trend-item:disabled')).to_have_count(4)
    assert page.locator(day).get_attribute('aria-label') == 'Mon · View tasks completed on Nov 16, 2026: 1'
    before = stored(page)
    page.locator('.stats-review').scroll_into_view_if_needed()
    capture(page, output, '01-review-history-actions')

    origin = open_history(page, week, {100, 101, 102}, 'completed:week', before, keyboard=True)
    expect(page.locator('#count-all')).to_have_text('(8)')
    capture(page, output, '02-visible-seven-day-condition')
    return_to_review(page, week, origin, before)
    origin = open_history(page, day, {101}, 'completed:2026-11-16', before)
    capture(page, output, '03-local-day-completions')
    return_to_review(page, day, origin, before)
    capture(page, output, '04-returned-to-same-day')

    origin = open_history(page, week, {100, 101, 102}, 'completed:week', before)
    for selected, expected in [('active', set()), ('archived', {102}), ('completed', {100, 101}), ('all', {100, 101, 102})]:
        select_filter(page, selected)
        assert_ids(page, expected)
        expect(page.locator('#searchInput')).to_have_value(f'{QUERY} completed:week')
        assert stored(page) == before, 'The status dropdown wrote completion history records'
    navigate_workbench(page, 'review')
    page.locator('#searchInput').fill('project:Work tag:review completed:"week"')
    expect(page.locator(week)).to_have_text('3 tasks completed')
    origin = open_history(page, week, {100, 101, 102}, 'completed:week', before)
    return_to_review(page, week, origin, before)
    page.locator('#searchInput').fill(QUERY)
    expect(page.locator(week)).to_have_text('3 tasks completed')

    for status, count, expected in [('completed', 2, {100, 101}), ('archived', 1, {102})]:
        query = f'{QUERY} status:{status}'
        page.locator('#searchInput').fill(query)
        expect(page.locator(week)).to_contain_text(str(count))
        scoped_before = stored(page)
        origin = open_history(page, week, expected, 'completed:week', scoped_before)
        return_to_review(page, week, origin, scoped_before)

    page.locator('#searchInput').fill(f'{QUERY} status:active')
    expect(page.locator(week)).to_be_disabled()
    expect(page.locator(week)).to_have_text('0 tasks completed')
    expect(page.locator('.stats-trend-empty')).to_be_visible()
    assert stored(page) == before, 'Scope changes wrote task/configuration records'
    page.locator('#searchInput').fill(QUERY)
    expect(page.locator(week)).to_be_enabled()
    select_language(page, 'zh-CN')
    expect(page.locator(week)).to_have_attribute('aria-label', '完成 3 项 · 查看最近 7 天完成的任务：3 项')
    assert '查看' in page.locator(day).get_attribute('aria-label')
    capture(page, output, '05-chinese-history-actions')
    return ['seven-day total and nonzero days are real buttons; zero days disabled',
            'local completion dates include retained archives and exclude old/future/undated/unfinished records',
            'original project, tag, due and explicit status scope preserved',
            'status dropdown remains effective; metadata-like project/tag names cannot absorb completion conditions',
            'visible date query, keyboard activation, return scroll and exact source focus',
            'task/configuration records unchanged; English and Chinese accessible names']


def verify_midnight(page, output):
    fixtures = [
        (201, 'Oldest day falls out at midnight', '2026-11-11T02:00:00.000Z', False, 'Work', 'review', True),
        (202, 'Recent completion remains', '2026-11-17T02:00:00.000Z', True, 'Work', 'review', True),
        (203, 'New local day completion enters', '2026-11-17T16:00:01.000Z', False, 'Work', 'review', True),
    ]
    seed(page, fixtures)
    navigate_workbench(page, 'review')
    page.locator('#searchInput').fill('tag:review')
    week = 'button.stats-review-total'
    expect(page.locator(week)).to_have_text('2 tasks completed')
    before = stored(page)
    origin = open_history(page, week, {201, 202}, 'completed:week', before)
    page.clock.fast_forward(120_000)
    assert_ids(page, {202, 203})
    expect(page.locator('#searchInput')).to_have_value('tag:review completed:week')
    assert stored(page) == before, 'Midnight completion search wrote task or configuration data'
    page.locator('#statsReturnBtn').click()
    expect(page.locator(week)).to_be_focused()
    expect(page.locator('button.stats-trend-item[data-stats-date="2026-11-18"]')).to_be_enabled()
    expect(page.locator('button.stats-trend-item[data-stats-date="2026-11-11"]')).to_have_count(0)
    assert scope(page) == origin['scope']
    assert stored(page) == before
    capture(page, output, '06-midnight-history-range')


def verify_capture_literal(page):
    navigate_workbench(page, 'tasks')
    ensure_capture(page)
    raw = 'Keep completed:week as title /Work'
    page.locator('#quickAddInput').fill(raw)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    task = next(task for task in get_task_records(page) if task['name'] == 'Keep completed:week as title')
    assert task['project'] == 'Work' and not task['completed'] and not task['completedAt']


def verify_pending_search_return(page, output):
    fixtures = [
        (301, 'Completed today', '2026-11-17T01:00:00.000Z', False, 'Work', 'review', True),
        (302, 'Archived recent completion', '2026-11-16T01:00:00.000Z', True, 'Work', 'review', True),
        (303, 'Completed earlier this week', '2026-11-12T01:00:00.000Z', False, 'Work', 'review', True),
    ]
    seed(page, fixtures)
    navigate_workbench(page, 'review')
    select_project(page, 'Work')
    page.locator('#searchInput').fill(QUERY)
    page.clock.run_for(350)
    week = 'button.stats-review-total[data-stats-action="review-week"]'
    expect(page.locator(week)).to_have_text('3 tasks completed')
    pause = datetime.fromtimestamp(page.evaluate('Date.now()') / 1000 + 1, tz=timezone.utc)
    page.clock.pause_at(pause)
    before = stored(page)
    page.locator('#searchInput').fill('project:Work tag:review completed:"week"')
    expect(page.locator(week)).to_have_text('3 tasks completed')
    origin = open_history(page, week, {301, 302, 303}, 'completed:week', before)
    page.locator('#statsReturnBtn').click()
    page.clock.run_for(20)
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'review')
    expect(page.locator(week)).to_be_focused()
    source = page.locator(week).evaluate_handle('node => node')
    page.clock.fast_forward(350)
    assert source.evaluate('node => node.isConnected && node === document.activeElement'), \
        'An already consumed search timer replaced the restored Review focus target'
    expect(page.locator(week)).to_be_focused()
    assert scope(page) == origin['scope']
    assert page.evaluate('''original => Math.abs(scrollY - Math.min(original,
        Math.max(0, document.scrollingElement.scrollHeight - document.scrollingElement.clientHeight))) <= 1''', origin['clicked_scroll'])
    assert stored(page) == before, 'A pending search or Review return changed task/configuration data'
    capture(page, output, '07-return-after-pending-search')
    page.locator('#searchInput').fill('tag:no-matching-review-tag')
    page.clock.run_for(350)
    expect(page.locator(week)).to_have_text('0 tasks completed')
    assert stored(page) == before


def run(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'passed': False, 'browser_engine': args.browser, 'timezone': ZONE,
              'scope': 'Synthetic isolated profiles; localhost only; history navigation is read-only', 'viewports': []}
    try:
        with local_server() as url, sync_playwright() as playwright:
            options = browser_launch_options(args.browser)
            browser = getattr(playwright, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                for width in args.widths:
                    folder = output / str(width)
                    folder.mkdir()
                    context = browser.new_context(viewport={'width': width, 'height': 960 if width > 779 else 844},
                                                  timezone_id=ZONE, locale='en-US', reduced_motion='reduce')
                    page = context.new_page()
                    page.clock.install(time=datetime.fromisoformat('2026-11-17T12:00:00+08:00'))
                    errors = []
                    page.on('pageerror', lambda error, sink=errors: sink.append(str(error)))
                    entry = {'width': width, 'passed': False, 'page_errors': errors}
                    report['viewports'].append(entry)
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        wait_for_app_ready(page)
                        entry['checks'] = verify_history(page, folder)
                        verify_capture_literal(page)
                        entry['checks'].append('quick capture retains completed:week as literal task title text')
                        assert not errors, errors
                        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                        entry['passed'] = True
                    except Exception:
                        page.screenshot(path=str(folder / 'failure.png'))
                        raise
                    finally:
                        context.close()
                    print(f'Review history {args.browser} {width}px passed', flush=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 960}, timezone_id=ZONE,
                                              locale='en-US', reduced_motion='reduce')
                try:
                    page = context.new_page()
                    page.clock.install(time=datetime.fromisoformat('2026-11-17T23:59:00+08:00'))
                    page.goto(url, wait_until='domcontentloaded')
                    wait_for_app_ready(page)
                    verify_midnight(page, output)
                    report['midnight_passed'] = True
                finally:
                    context.close()
                context = browser.new_context(viewport={'width': 1440, 'height': 960}, timezone_id=ZONE,
                                              locale='en-US', reduced_motion='reduce')
                try:
                    page = context.new_page()
                    page.clock.install(time=datetime.fromisoformat('2026-11-17T12:00:00+08:00'))
                    page.goto(url, wait_until='domcontentloaded')
                    wait_for_app_ready(page)
                    verify_pending_search_return(page, output)
                    report['pending_search_focus_passed'] = True
                finally:
                    context.close()
            finally:
                browser.close()
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': report['passed'], 'report': str(output / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--widths', type=int, nargs='+', default=[1440, 390])
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-review-history'))
    run(parser.parse_args())
