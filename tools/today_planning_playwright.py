#!/usr/bin/env python3
"""Choose today's tasks through a temporary, accessible planning context."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, click_task_action, get_task_records,
    ensure_capture, enter_batch_mode, local_server, navigate_workbench, select_filter, select_project,
    task_locator, wait_for_app_ready,
)


def records(page):
    return {task['name']: task for task in get_task_records(page)}


def enter_planning(page, keyboard=False):
    navigate_workbench(page, 'today')
    choose = page.locator('#todayWorkspace .workbench-choose-tasks')
    expect(choose).to_be_visible()
    if keyboard:
        choose.focus()
        choose.press('Enter')
    else:
        choose.click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'tasks')
    expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'true')
    expect(page.locator('#workspaceTitle')).to_have_text('选择今日计划')
    expect(page.locator('#planningDoneBtn')).to_be_visible()
    expect(page.locator('#workspaceViewNavHost')).to_be_hidden()


def plan_button(page, name):
    return task_locator(page, name).locator('[data-task-plan]')


def capture(page, output, name):
    notice = page.locator('#workspaceNotificationClose')
    if notice.is_visible():
        notice.click()
    page.screenshot(path=str(output / (name + '.png')), animations='disabled')


def exercise(page, output):
    undated = '整理今天的重点'
    future = '完成下周评审'
    add_task(page, undated, description='没有截止日期，也可以进入今天的计划。',
             no_deadline=True, project='工作')
    add_task(page, future, description='选择今天推进，同时保留原截止日期。',
             due_date='2035-06-14', due_time='20:30', project='研究')
    add_task(page, '归档项目参考', no_deadline=True)
    archived = task_locator(page, '归档项目参考')
    click_task_action(archived, 'toggle')
    select_filter(page, 'completed')
    click_task_action(archived, 'archive')
    expect(archived).to_have_count(0)
    before = records(page)
    select_filter(page, 'active')
    enter_batch_mode(page)
    for name in (undated, future):
        task_locator(page, name).locator('.task-select-checkbox').check()
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(2)
    navigate_workbench(page, 'today')
    navigate_workbench(page, 'tasks')
    expect(page.locator('#batchModeBtn')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(2)
    enter_planning(page, keyboard=True)
    expect(page.locator('#workspaceTitle')).to_be_focused()
    expect(page.locator('#batchModeBtn')).to_have_attribute('aria-pressed', 'false')
    expect(page.locator('#batchToolbar')).to_be_hidden()
    expect(page.locator('.task-select-checkbox')).to_have_count(0)
    page.locator('#batchModeBtn').click()
    expect(page.locator('.task-select-checkbox')).to_have_count(2)
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(0)
    expect(page.locator('#batchCompleteBtn')).to_be_disabled()
    page.locator('#exitBatchModeBtn').click()
    expect(page.locator('#batchToolbar')).to_be_hidden()
    assert records(page) == before, 'Entering planning from bulk mode changed saved tasks'
    task_locator(page, future).locator('[data-task-open]').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert records(page) == before, 'Editing an unplanned task implicitly added it to today'
    expect(plan_button(page, undated)).to_have_attribute('aria-pressed', 'false')
    expect(task_locator(page, undated).locator('.task-plan-badge')).to_be_hidden()
    plan_button(page, undated).click()
    expect(plan_button(page, undated)).to_have_attribute('aria-pressed', 'true')
    expect(plan_button(page, undated)).to_be_enabled()
    expect(plan_button(page, undated)).to_be_focused()
    today = records(page)[undated]['focusDate']
    assert today and records(page)[undated] == {**before[undated], 'focusDate': today}
    page.locator('#undoBtn').click()
    expect(plan_button(page, undated)).to_have_attribute('aria-pressed', 'false')
    assert records(page) == before, 'Planning undo changed a deadline or another task field'

    plan_button(page, undated).focus()
    plan_button(page, undated).press('Space')
    expect(plan_button(page, undated)).to_have_attribute('aria-pressed', 'true')
    plan_button(page, future).focus()
    plan_button(page, future).press('Enter')
    expect(plan_button(page, future)).to_have_attribute('aria-pressed', 'true')
    expect(plan_button(page, future)).to_be_enabled()
    expect(plan_button(page, future)).to_be_focused()
    planned = records(page)
    assert planned[future] == {**before[future], 'focusDate': today}, 'Planning rewrote the real due date'
    assert planned[undated] == {**before[undated], 'focusDate': today}
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('规划中用编辑器新增')
    page.locator('#noDeadline').uncheck()
    page.locator('#dueDate').fill('2035-07-18')
    page.locator('#dueTime').fill('18:15')
    page.locator('#submitBtn').click()
    expect(plan_button(page, '规划中用编辑器新增')).to_have_attribute('aria-pressed', 'true')
    created = records(page)['规划中用编辑器新增']
    assert created['focusDate'] == today and created['dueLocalDate'] == '2035-07-18' and created['dueLocalTime'] == '18:15'
    page.locator('#undoBtn').click()
    expect(task_locator(page, '规划中用编辑器新增')).to_have_count(0)
    assert records(page) == planned
    ensure_capture(page)
    quick = page.locator('#quickAddInput')
    quick.fill('2035-08-19 16:45 规划中快速记录')
    quick.press('Enter')
    expect(plan_button(page, '规划中快速记录')).to_have_attribute('aria-pressed', 'true')
    created = records(page)['规划中快速记录']
    assert created['focusDate'] == today and created['dueLocalDate'] == '2035-08-19' and created['dueLocalTime'] == '16:45'
    page.locator('#undoBtn').click()
    expect(task_locator(page, '规划中快速记录')).to_have_count(0)
    assert records(page) == planned
    page.locator('#captureCloseBtn').click()
    page.locator('#searchInput').fill('下周评审')
    expect(task_locator(page, undated)).to_have_count(0)
    expect(plan_button(page, future)).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#workspaceTitle')).to_have_text('选择今日计划')
    page.locator('#searchInput').fill('')
    select_project(page, '研究')
    expect(plan_button(page, future)).to_be_visible()
    expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'true')
    select_project(page, 'all')
    select_filter(page, 'archived')
    expect(archived).to_be_visible()
    expect(archived.locator('[data-task-plan]')).to_be_hidden()
    click_task_action(archived, 'archive')
    select_filter(page, 'active')
    expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'true')
    capture(page, output, '01-desktop-planning')
    page.locator('#planningDoneBtn').click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'today')
    expect(page.locator('#todayWorkspace .workbench-task-name', has_text=undated)).to_be_visible()
    expect(page.locator('#todayWorkspace .workbench-task-name', has_text=future)).to_be_visible()
    assert records(page)[future] == planned[future]

    enter_planning(page)
    page.locator('[data-workbench-screen="tasks"]:visible').first.click()
    expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'false')
    expect(page.locator('#planningDoneBtn')).to_be_hidden()
    expect(page.locator('#workspaceViewNavHost')).to_be_visible()
    for name in (undated, future):
        expect(task_locator(page, name).locator('.task-plan-badge')).to_be_visible()
        expect(task_locator(page, name).locator('.task-plan-badge')).to_have_text('今日计划')
        expect(plan_button(page, name)).to_be_hidden()
        expect(task_locator(page, name)).to_have_count(1)
    capture(page, output, '02-ordinary-task-membership')

    page.set_viewport_size({'width': 390, 'height': 844})
    enter_planning(page)
    control = plan_button(page, future)
    control.focus()
    control.press('Space')
    expect(control).to_have_attribute('aria-pressed', 'false')
    expect(control).to_be_enabled()
    expect(control).to_be_focused()
    removed = records(page)
    assert removed[future] == before[future]
    capture(page, output, '03-mobile-planning')
    page.set_viewport_size({'width': 320, 'height': 568})
    for name in (undated, future):
        compact = plan_button(page, name)
        compact.scroll_into_view_if_needed()
        bounds = compact.bounding_box()
        assert bounds and bounds['width'] >= 44 and bounds['height'] >= 44
        compact.focus()
        compact.press('Tab')
        page.keyboard.press('Shift+Tab')
        expect(compact).to_be_focused()
        page.wait_for_function('''id => {
            const node = document.getElementById(id);
            const box = node.getBoundingClientRect();
            const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
            return hit === node || node.contains(hit);
        }''', arg=compact.get_attribute('id'))
    title = task_locator(page, undated).locator('[data-task-open]')
    title.focus()
    title.press('Shift+Tab')
    page.keyboard.press('Tab')
    expect(title).to_be_focused()
    for index, target in enumerate((title, plan_button(page, undated), task_locator(page, undated).locator('.task-more-toggle'))):
        if index:
            page.keyboard.press('Tab')
        expect(target).to_be_focused()
        page.wait_for_function('''() => {
            const node = document.activeElement, box = node.getBoundingClientRect();
            const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
            return hit === node || node.contains(hit);
        }''')
    capture(page, output, '04-compact-planning')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#undoBtn').click()
    expect(control).to_have_attribute('aria-pressed', 'true')
    assert records(page)[future] == planned[future]
    page.locator('#planningDoneBtn').focus()
    page.locator('#planningDoneBtn').press('Enter')
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'today')
    capture(page, output, '05-mobile-today-after-planning')

    for destination in ('projects', 'review', 'settings'):
        enter_planning(page)
        navigate_workbench(page, destination)
        navigate_workbench(page, 'tasks')
        expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'false')
        expect(page.locator('#planningDoneBtn')).to_be_hidden()
    for view in ('calendar', 'timeline'):
        enter_planning(page)
        page.keyboard.press('Control+p')
        query = page.locator('#commandPaletteInput')
        query.fill(view)
        expect(page.locator('#commandPaletteList .command-item')).to_have_count(1)
        query.press('Enter')
        expect(page.locator('#commandPalette')).to_be_hidden()
        expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'false')
        expect(page.locator('#planningDoneBtn')).to_be_hidden()
        expect(page.locator('#workspaceViewNavHost')).to_be_visible()

    enter_planning(page)
    stable = records(page)
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    navigate_workbench(page, 'tasks')
    expect(page.locator('#tasksWorkspace')).to_have_attribute('data-planning', 'false')
    expect(page.locator('#planningDoneBtn')).to_be_hidden()
    assert records(page) == stable, 'Exiting or refreshing planning wrote task data'
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    return ['Today entry and Done form a planning loop', 'direct per-row keyboard and pointer planning',
            'planning clears old bulk mode and selection; ordinary navigation preserves both',
            'editor/capture create planned tasks with original due fields; both undo exactly',
            'only focusDate changes; due/reminder fields stay exact', 'undo restores exact records',
            'filters/search preserve planning; archived menus remain usable',
            'ordinary Tasks show membership without duplicate task nodes',
            '390px removal, undo and keyboard return to Today',
            'navigation and Calendar/Timeline commands end planning',
            'refresh ends temporary context without task writes']


def main(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'passed': False, 'browser': args.browser, 'page_errors': []}
    try:
        with local_server() as url, sync_playwright() as p:
            browser = getattr(p, args.browser).launch(**browser_launch_options(args.browser))
            report['browser_version'] = browser.version
            try:
                context = browser.new_context(viewport={'width': 1280, 'height': 900},
                                              locale='zh-CN', reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    wait_for_app_ready(page)
                    report['checks'] = exercise(page, output)
                    assert not report['page_errors'], report['page_errors']
                    report['passed'] = True
                except Exception:
                    page.screenshot(path=str(output / 'failure.png'), animations='disabled')
                    raise
                finally:
                    context.close()
            finally:
                browser.close()
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'passed': report['passed'], 'report': str(output / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-today-planning'))
    main(parser.parse_args())
