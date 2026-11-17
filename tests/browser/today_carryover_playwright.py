#!/usr/bin/env python3
"""Keep unfinished earlier plans discoverable across midnight without rewriting them.

Uses a fresh profile, two real UI-created tasks and synthetic boundary records.
Planning, Undo, language switching and paging use actual visible controls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from tests.support.browser import (
    browser_launch_options,
    get_task_records,
    navigate_workbench,
    select_language,
    wait_for_app_ready,
)
from tests.support.http import local_server
from tests.support.workbench_navigation import assert_today_focus_reachable, create_on_current_page
from tests.support.capture import capture


DAY = '2026-11-16'
NEXT_DAY = '2026-11-17'
FUTURE = '2026-11-20'


def records(page):
    return {str(task['id']): task for task in get_task_records(page)}


def seed_boundary_records(page, template):
    """Prepare meaningful stored states without using application internals."""
    additions = []
    for index in range(9):
        additions.append({**template, 'id': 80_000 + index,
                          'name': f'较早的未完成计划 {index + 1}',
                          'focusDate': '2026-11-15', 'order': 50_000 + index * 1000})
    for index, changes in enumerate((
        {'name': '已完成的旧计划', 'completed': True, 'completedAt': '2026-11-16T12:00:00Z'},
        {'name': '已归档的旧计划', 'archived': True, 'archivedAt': '2026-11-16T12:00:00Z'},
        {'name': '未来计划', 'focusDate': '2026-11-18'},
        {'name': '尚未安排的任务', 'focusDate': None},
    )):
        additions.append({**template, 'id': 81_000 + index,
                          'order': 70_000 + index * 1000, **changes})
    page.evaluate("""tasks => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('tasks', 'readwrite');
            for (const task of tasks) tx.objectStore('tasks').put(task);
            tx.oncomplete = () => { db.close(); resolve(); };
            tx.onabort = () => { db.close(); reject(tx.error); };
        };
    })""", additions)
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)


def visible_candidate_ids(page):
    return page.locator('.today-candidates [data-workbench-task]').evaluate_all(
        'rows => rows.map(row => row.dataset.workbenchTask)')


def reveal_all_candidates(page):
    more = page.locator('[data-workbench-action="more-candidates"]')
    if more.is_visible():
        more.click()


def verify(page, output):
    undated = create_on_current_page(page, '整理昨日未完成笔记', project='研究')
    dated = create_on_current_page(page, '完成周会材料', project='工作', deadline=FUTURE)
    seed_boundary_records(page, undated)
    navigate_workbench(page, 'today')
    before = records(page)
    candidates = page.locator('.today-candidates')
    expect(candidates.locator('[data-workbench-task]')).to_have_count(8)
    expect(candidates.locator('.workbench-count')).to_have_text('9 tasks')
    expect(page.locator('.today-plan .workbench-task:not(.is-completed)')).to_have_count(2)
    expect(page.locator('.today-plan .workbench-task.is-completed')).to_have_count(1)

    page.clock.fast_forward(3 * 60_000)
    expect(page.locator('.today-plan [data-workbench-task]')).to_have_count(0)
    expect(candidates.locator('.workbench-count')).to_have_text('11 tasks')
    expect(candidates.locator('[data-workbench-task]')).to_have_count(8)
    reveal_all_candidates(page)
    expected_ids = {str(undated['id']), str(dated['id'])} | {str(80_000 + i) for i in range(9)}
    ids = visible_candidate_ids(page)
    assert len(ids) == len(set(ids)) == 11 and set(ids) == expected_ids, ids
    assert records(page) == before, 'Crossing midnight or paging changed stored records'
    for key in expected_ids:
        expect(candidates.locator(f'[data-workbench-task="{key}"] .workbench-task-carryover')).to_have_text('Previously planned')
    capture(page, output, '01-previous-plans-after-midnight')

    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    navigate_workbench(page, 'today')
    expect(candidates.locator('.workbench-count')).to_have_text('11 tasks')
    reveal_all_candidates(page)
    assert set(visible_candidate_ids(page)) == expected_ids
    assert records(page) == before, 'Refreshing Today changed stored plans or deadlines'

    select_language(page, 'zh-CN')
    navigate_workbench(page, 'today')
    reveal_all_candidates(page)
    for key in expected_ids:
        expect(candidates.locator(f'[data-workbench-task="{key}"] .workbench-task-carryover')).to_have_text('此前未完成')
    assert records(page) == before, 'Changing language rewrote task data'
    capture(page, output, '02-previous-plans-chinese')

    for task in (undated, dated):
        key = str(task['id'])
        row = candidates.locator(f'[data-workbench-task="{key}"]')
        action = row.locator('[data-workbench-action="plan"]')
        expect(action).to_have_accessible_name('加入今天: ' + task['name'])
        action.focus()
        page.keyboard.press('Enter')
        planned = page.locator(f'.today-plan [data-workbench-task="{key}"]')
        expect(planned).to_have_count(1)
        expect(page.locator(f'#todayWorkspace [data-workbench-task="{key}"]')).to_have_count(1)
        expect(planned.locator('.workbench-task-carryover')).to_be_hidden()
        assert_today_focus_reachable(page)
        changed = records(page)
        assert changed[key] == {**before[key], 'focusDate': NEXT_DAY}, 'Planning changed a deadline or another task field'
        assert {k: v for k, v in changed.items() if k != key} == {k: v for k, v in before.items() if k != key}
        page.locator('#undoBtn').click()
        expect(candidates.locator(f'[data-workbench-task="{key}"]')).to_have_count(1)
        expect(candidates.locator(f'[data-workbench-task="{key}"] .workbench-task-carryover')).to_have_text('此前未完成')
        assert records(page) == before, 'Undo did not restore the exact original focus date and deadline'
    capture(page, output, '03-planning-and-undo-preserve-original-tasks')
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    return {
        'candidate_count': len(expected_ids),
        'excluded': ['completed earlier plan', 'archived earlier plan', 'future plan', 'never planned undated task'],
        'checks': ['live midnight refresh', 'normal reload', 'paging without duplicate rows',
                   'English and Chinese reason labels', 'keyboard planning and reachable focus',
                   'dated and undated planning only changes focusDate', 'Undo restores exact original tasks'],
    }


def run(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'scope': 'Isolated synthetic profile; Asia/Shanghai; local HTTP only',
              'clock_anchor': DAY + 'T23:58:00+08:00', 'browser_engine': args.browser,
              'passed': False, 'viewports': []}
    try:
        with local_server() as url, sync_playwright() as p:
            options = browser_launch_options(args.browser)
            browser = getattr(p, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                for width in args.widths:
                    folder = output / str(width)
                    folder.mkdir()
                    context = browser.new_context(viewport={'width': width, 'height': 960 if width > 779 else 844},
                                                  timezone_id='Asia/Shanghai', locale='en-US', reduced_motion='reduce')
                    page = context.new_page()
                    page.clock.install(time=datetime(2026, 11, 16, 23, 58, tzinfo=timezone(timedelta(hours=8))))
                    errors = []
                    page.on('pageerror', lambda error, sink=errors: sink.append(str(error)))
                    entry = {'width': width, 'passed': False, 'page_errors': errors}
                    report['viewports'].append(entry)
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        wait_for_app_ready(page)
                        entry.update(verify(page, folder))
                        assert not errors, errors
                        entry['passed'] = True
                        print(f'Previous-plan carryover {args.browser} {width}px passed', flush=True)
                    except Exception:
                        page.screenshot(path=str(folder / 'failure.png'), full_page=False)
                        raise
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
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-today-carryover'))
    run(parser.parse_args())
