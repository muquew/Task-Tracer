#!/usr/bin/env python3
"""Choose existing tasks from Today before, during and after a daily plan.

Uses isolated synthetic tasks and real navigation, task menus and completion
controls. A separate blocked-storage profile checks the disabled entry point.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import (
    add_task, browser_launch_options, click_task_action, get_task_records,
    local_server, navigate_workbench, task_locator, wait_for_app_ready,
)
from workbench_navigation_playwright import capture


TODAY = '2026-11-17'
NAMES = ['整理研究笔记', '准备项目评审', '检查下一阶段任务']


def records(page):
    return {str(task['id']): task for task in get_task_records(page)}


def chooser(page):
    control = page.locator('#todayWorkspace .workbench-choose-tasks')
    expect(control).to_have_count(1)
    expect(control).to_be_visible()
    expect(control).to_be_enabled()
    expect(control.locator('xpath=ancestor::*[contains(@class,"workbench-section-actions")]')).to_have_count(1)
    expect(page.locator('.today-plan .workbench-empty .workbench-link')).to_have_count(0)
    return control


def open_library_without_writes(page):
    before = records(page)
    chooser(page).click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'tasks')
    expect(page.locator('#searchInput')).to_have_value('')
    assert records(page) == before, 'Choosing tasks changed records before a task was selected'
    return before


def add_existing_to_today(page, name):
    before = open_library_without_writes(page)
    task = next(task for task in before.values() if task['name'] == name)
    expect(task_locator(page, name)).to_be_visible()
    click_task_action(task_locator(page, name), 'focus')
    after = records(page)
    key = str(task['id'])
    assert after[key] == {**before[key], 'focusDate': TODAY}, 'Planning changed task content or its deadline'
    assert {k: v for k, v in after.items() if k != key} == {k: v for k, v in before.items() if k != key}
    navigate_workbench(page, 'today')
    expect(page.locator(f'.today-plan [data-workbench-task="{key}"]')).to_have_count(1)
    chooser(page)
    return key


def verify_selection(page, output):
    before = records(page)
    assert before == {}, 'Expected a fresh isolated task store'
    chooser(page)
    capture(page, output, '01-empty-plan-stable-selection')
    open_library_without_writes(page)
    navigate_workbench(page, 'today')
    for name in NAMES:
        add_task(page, name, description='', no_deadline=True, project='研究')
    navigate_workbench(page, 'today')
    original = records(page)
    assert all(task.get('focusDate') is None for task in original.values())

    first = add_existing_to_today(page, NAMES[0])
    capture(page, output, '02-active-plan-stable-selection')
    second = add_existing_to_today(page, NAMES[1])
    for key in (first, second):
        page.locator(f'.today-plan [data-workbench-task="{key}"] [data-workbench-action="toggle"]').click()
        expect(page.locator(f'.today-plan [data-workbench-task="{key}"]')).to_have_class('workbench-task is-completed')
    expect(page.locator('.today-plan .workbench-task:not(.is-completed)')).to_have_count(0)
    expect(page.locator('.today-plan .workbench-task.is-completed')).to_have_count(2)
    chooser(page)
    capture(page, output, '03-completed-plan-stable-selection')

    third_before = records(page)
    third = add_existing_to_today(page, NAMES[2])
    expect(page.locator('.today-plan .workbench-task:not(.is-completed)')).to_have_count(1)
    expect(page.locator('.today-plan .workbench-task.is-completed')).to_have_count(2)
    page.locator('#undoBtn').click()
    expect(page.locator(f'.today-plan [data-workbench-task="{third}"]')).to_have_count(0)
    assert records(page) == third_before, 'Undo did not restore the exact state before the added plan'
    chooser(page)
    capture(page, output, '04-new-selection-undo')
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    return ['empty, active and completed plans expose one stable choice action',
            'opening the task library is read-only', 'existing tasks can be planned without deadline/content changes',
            'completed plans can accept another existing task', 'Undo restores original records']


def verify_blocked_storage(browser, url, output, width):
    context = browser.new_context(viewport={'width': width, 'height': 960 if width > 779 else 844},
                                  locale='en-US', reduced_motion='reduce')
    context.add_init_script("""Object.defineProperty(window, 'indexedDB', {
        configurable: true,
        value: {open() {throw new DOMException('Synthetic blocked storage', 'SecurityError');}}
    });""")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(url, wait_until='domcontentloaded')
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        control = page.locator('#todayWorkspace .workbench-choose-tasks')
        expect(control).to_have_count(1)
        expect(control).to_be_visible()
        expect(control).to_be_disabled()
        expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'today')
        capture(page, output, '05-storage-unavailable-selection-disabled')
        assert not errors, errors
    finally:
        context.close()


def run(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'browser_engine': args.browser, 'passed': False,
              'scope': 'Fresh synthetic profiles; local HTTP only', 'viewports': []}
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
                    page.clock.install(time=datetime(2026, 11, 17, 12, tzinfo=timezone(timedelta(hours=8))))
                    errors = []
                    page.on('pageerror', lambda error, sink=errors: sink.append(str(error)))
                    entry = {'width': width, 'page_errors': errors, 'passed': False}
                    report['viewports'].append(entry)
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        wait_for_app_ready(page)
                        entry['checks'] = verify_selection(page, folder)
                        assert not errors, errors
                    except Exception:
                        page.screenshot(path=str(folder / 'failure.png'))
                        raise
                    finally:
                        context.close()
                    verify_blocked_storage(browser, url, folder, width)
                    entry['checks'].append('blocked storage disables the stable choice action')
                    entry['passed'] = True
                    print(f'Today existing-task selection {args.browser} {width}px passed', flush=True)
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
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-today-selection'))
    run(parser.parse_args())
