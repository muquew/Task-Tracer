#!/usr/bin/env python3
"""Follow a completed daily plan into unfiltered completion history without writes."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from tests.support.storage import stored
from tests.support.browser import (
    add_task,
    browser_launch_options,
    click_task_action,
    get_task_records,
    navigate_workbench,
    select_language,
    select_project,
    task_locator,
    wait_for_app_ready,
)
from tests.support.http import local_server
from tests.support.capture import capture


DAY = '2026-11-17'
PLANNED = 'Finish the daily plan'
OTHER = 'Completion outside the plan'


def upgrade_without_record_writes(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 3);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => {db.close(); resolve({tasks:tasks.result, config:config.result});};
            tx.onabort = () => reject(tx.error);
        };
    })""")


def verify(page, output):
    review = page.locator('.workbench-review-link')
    complete_state = page.locator('.today-plan .workbench-empty')
    expect(review).to_be_hidden()
    expect(complete_state).not_to_have_class(re.compile(r'\bis-complete\b'))
    expect(page.locator('.today-candidates')).to_be_hidden()
    capture(page, output, '01-empty-today')

    add_task(page, PLANNED, description='', no_deadline=True, project='Delivery')
    add_task(page, OTHER, description='', no_deadline=True, project='Personal')
    click_task_action(task_locator(page, PLANNED), 'focus')
    click_task_action(task_locator(page, OTHER), 'toggle')

    navigate_workbench(page, 'review')
    select_project(page, 'Personal')
    page.locator('#searchInput').fill('status:active tag:missing')
    expect(page.locator('button.stats-review-total')).to_be_disabled()
    navigate_workbench(page, 'today')
    expect(review).to_be_hidden()
    row = page.locator('.today-plan .workbench-task:not(.is-completed)')
    expect(row).to_have_count(1)
    row.locator('[data-workbench-action="toggle"]').click()
    expect(page.locator('.today-plan .workbench-task.is-completed')).to_have_count(1)
    expect(complete_state).to_have_class(re.compile(r'\bis-complete\b'))
    expect(review).to_be_visible()
    expect(review).to_be_enabled()
    expect(review).to_have_text('Review activity')
    expect(page.locator('.workbench-progress-label')).to_have_text('1 of 1 completed')
    expect(page.locator('.workbench-choose-tasks')).to_be_visible()
    expect(page.locator('.today-candidates')).to_be_hidden()
    capture(page, output, '02-completed-plan')
    before = stored(page)

    review.focus()
    page.keyboard.press('Enter')
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'review')
    expect(page.locator('#workspaceTitle')).to_be_focused()
    expect(page.locator('#searchInput')).to_have_value('')
    project = page.locator('#projectDropdown [aria-selected="true"]').get_attribute('data-project')
    assert json.loads(project) == {'kind': 'all'}, project
    expect(page.locator('button.stats-review-total')).to_have_text('2 tasks completed')
    day = page.locator(f'button.stats-trend-item[data-stats-date="{DAY}"]')
    expect(day.locator('.stats-trend-count')).to_have_text('2')
    assert stored(page) == before, 'Opening Review rewrote task or configuration records'
    capture(page, output, '03-unfiltered-review')

    day.click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'tasks')
    expect(page.locator('#searchInput')).to_have_value(f'completed:{DAY}')
    expect(page.locator('#workspaceTitle')).to_be_focused()
    expect(page.locator('.task-item')).to_have_count(2)
    expect(task_locator(page, PLANNED)).to_have_count(1)
    expect(task_locator(page, OTHER)).to_have_count(1)
    assert stored(page) == before, 'Opening the completion day wrote task or configuration records'
    capture(page, output, '04-today-completion-records')
    page.locator('#statsReturnBtn').click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'review')
    expect(day).to_be_focused()
    expect(page.locator('#searchInput')).to_have_value('')
    assert stored(page) == before, 'Returning from completion records wrote data'
    capture(page, output, '05-returned-to-review-day')

    navigate_workbench(page, 'today')
    select_language(page, 'zh-CN')
    expect(review).to_have_text('查看回顾')
    expect(page.locator('.today-plan .workbench-task.is-completed')).to_have_count(1)
    before_failure = stored(page)
    after_upgrade = upgrade_without_record_writes(page)
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(review).to_be_hidden()
    expect(review).to_be_disabled()
    expect(page.locator('.workbench-choose-tasks')).to_be_disabled()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'today')
    assert after_upgrade == before_failure, 'Database version change rewrote task or configuration records'
    capture(page, output, '06-storage-unavailable')
    return ['empty and active plans hide Review; complete plans retain their task list and choice action',
            'completed state opens whole-workspace Review without remembered search/project scope',
            'today and seven-day counts include the planned and other real completions',
            'keyboard activation, day drilldown and return restore the correct focus',
            'navigation leaves task/configuration records unchanged',
            'Chinese copy and real database version-change storage boundary remain usable']


def run(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'browser': args.browser, 'passed': False, 'scope': 'Isolated synthetic local profiles', 'viewports': []}
    try:
        with local_server() as url, sync_playwright() as p:
            browser = getattr(p, args.browser).launch(**browser_launch_options(args.browser))
            report['browser_version'] = browser.version
            try:
                for width in args.widths:
                    folder = output / str(width)
                    folder.mkdir()
                    context = browser.new_context(viewport={'width': width, 'height': 960 if width > 779 else 844},
                        locale='en-US', timezone_id='Asia/Shanghai', reduced_motion='reduce')
                    page = context.new_page()
                    page.clock.install(time=datetime.fromisoformat('2026-11-17T12:00:00+08:00'))
                    errors = []
                    page.on('pageerror', lambda error, sink=errors: sink.append(str(error)))
                    entry = {'width': width, 'page_errors': errors, 'passed': False}
                    report['viewports'].append(entry)
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        wait_for_app_ready(page)
                        entry['checks'] = verify(page, folder)
                        assert not errors, errors
                        entry['passed'] = True
                        print(f'Today review {args.browser} {width}px passed', flush=True)
                    except Exception:
                        page.screenshot(path=str(folder / 'failure.png'))
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
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-today-review'))
    run(parser.parse_args())
