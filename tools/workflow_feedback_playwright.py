#!/usr/bin/env python3
"""Exercise saved-task feedback, notification timing and Undo through real UI.

Every task is created or edited through the application form in a fresh browser
context. Database access is read-only evidence; no app state, task fixtures,
clock, notification timeout or pagination threshold is replaced by this tool.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
import threading
import traceback

from playwright.sync_api import expect, sync_playwright

from security_playwright import ProductionHeaderHandler
from smoke_playwright import (
    browser_launch_options, click_task_action, ensure_capture, enter_batch_mode,
    get_task_records, open_task_editor, select_project, ThreadingHTTPServer,
    select_view, task_locator, wait_for_app_ready,
)


OUTSIDE_MESSAGE = re.compile(r'任务已保存[，,].*未在当前视图显示')


@contextmanager
def production_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def records(page):
    return {task['id']: task for task in get_task_records(page)}


def current_scope(page):
    """Read the actual selected controls, including the visible calendar month."""
    return page.evaluate("""() => ({
        search: document.querySelector('#searchInput').value,
        project: document.querySelector('#projectDropdown [aria-selected="true"]')?.dataset.project,
        filter: document.querySelector('#filterDropdown [aria-selected="true"]')?.dataset.filter,
        sort: document.querySelector('#sortDropdown [aria-selected="true"]')?.dataset.sort,
        view: document.querySelector('#viewSwitcher .view-tab.selected')?.dataset.view,
        month: document.querySelector('.calendar-title')?.textContent || null,
        selectedDate: document.querySelector('.calendar-agenda-add')?.dataset.calendarAddDate || null
    })""")


def create_task(page, name, *, project='反馈检查', due_date=None):
    """Submit once without assuming the saved task belongs in the current view."""
    before = records(page)
    open_task_editor(page)
    page.locator('#taskName').fill(name)
    page.locator('#taskDesc').fill('Synthetic workflow feedback regression: ' + name)
    page.locator('#taskProject').fill(project)
    if due_date:
        page.locator('#noDeadline').uncheck()
        page.locator('#dueDate').fill(due_date)
        page.locator('#dueTime').fill('12:00')
    else:
        page.locator('#noDeadline').check()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = records(page)
    added = [task for task_id, task in after.items() if task_id not in before]
    assert len(after) == len(before) + 1 and len(added) == 1, 'One save created zero or duplicate tasks'
    assert {task_id: after[task_id] for task_id in before} == before, 'Creating a task changed an existing task'
    assert added[0]['name'] == name
    return added[0]


def expect_outside_feedback(page):
    expect(page.locator('#notification')).to_have_class(re.compile(r'\bshow\b'))
    expect(page.locator('#notificationText')).to_have_text(OUTSIDE_MESSAGE)
    expect(page.locator('#notificationOpenTaskBtn')).to_be_visible()
    expect(page.locator('#notificationOpenTaskBtn')).to_be_enabled()
    assert not page.locator('#notificationOpenTaskBtn').evaluate(
        'node => node === document.activeElement'
    ), 'Saved-task notification stole keyboard focus'


def open_exact_saved_task(page, saved, scope):
    """Opening/cancelling is inspection, not another task save or a filter reset."""
    before = records(page)
    page.locator('#notificationOpenTaskBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value(saved['name'])
    expect(page.locator('#taskDesc')).to_have_value(saved['description'])
    expect(page.locator('#taskProject')).to_have_value(saved['project'])
    expect(page.locator('#submitBtn')).to_have_text('保存更改')
    if saved['dueLocalDate']:
        expect(page.locator('#dueDate')).to_have_value(saved['dueLocalDate'])
        expect(page.locator('#dueTime')).to_have_value(saved['dueLocalTime'])
    else:
        expect(page.locator('#noDeadline')).to_be_checked()
    assert current_scope(page) == scope, 'Open saved task changed the search, filters or visible month'
    assert records(page) == before, 'Open saved task wrote or duplicated task data'
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert records(page) == before, 'Cancelling saved-task inspection wrote task data'
    assert current_scope(page) == scope


def assert_mobile_feedback_layout(page):
    """Check action text stays horizontal and the notification fits its viewport."""
    problems = page.evaluate("""() => {
        const problems = [];
        const width = innerWidth;
        const notification = document.querySelector('#notification');
        const box = notification.getBoundingClientRect();
        if (document.documentElement.scrollWidth > width + 1) problems.push('document horizontal overflow');
        if (box.left < -1 || box.right > width + 1) problems.push('notification outside viewport');
        for (const button of notification.querySelectorAll('button')) {
            const rect = button.getBoundingClientRect();
            if (!rect.width || !rect.height || getComputedStyle(button).visibility === 'hidden') continue;
            if (rect.left < box.left - 1 || rect.right > box.right + 1) problems.push(button.id + ' outside notification');
            const tops = new Set();
            const walker = document.createTreeWalker(button, NodeFilter.SHOW_TEXT);
            let text;
            while ((text = walker.nextNode())) {
                if (!text.textContent.trim()) continue;
                const range = document.createRange();
                range.selectNodeContents(text);
                for (const line of range.getClientRects()) if (line.width) tops.add(Math.round(line.top));
            }
            if (tops.size > 1) problems.push(button.id + ' action text wraps into multiple lines');
        }
        const messageNode = document.querySelector('#notificationText');
        const message = messageNode.getBoundingClientRect();
        const characterWidth = parseFloat(getComputedStyle(messageNode).fontSize);
        if (message.width < characterWidth * 4) problems.push('message squeezed below four characters per line');
        return problems;
    }""")
    assert not problems, problems


def capture(page, output, name):
    page.screenshot(path=str(output / f'{name}.png'), full_page=False)


def search_empty_scope(page, query):
    page.locator('#searchInput').fill(query)
    # Initial empty-workspace UI has no Reset filters action. Its appearance
    # proves the real debounced search reached the constrained empty state.
    expect(page.locator('#taskList [data-reset-filters]')).to_be_visible()


def search_saved_task(page, output):
    search_empty_scope(page, '只查看会议')
    scope = current_scope(page)
    saved = create_task(page, '检查已保存但未显示的手机任务')
    expect(task_locator(page, saved['name'])).to_have_count(0)
    expect_outside_feedback(page)
    assert current_scope(page) == scope
    assert len(records(page)) == 1
    for width in (320, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        assert_mobile_feedback_layout(page)
        capture(page, output, f'search-outside-{width}')

    # Use actual time: an action with keyboard focus must survive the longest
    # existing notification lifetime, without a mocked clock or altered timer.
    page.locator('#notificationOpenTaskBtn').focus()
    page.wait_for_timeout(7000)
    expect(page.locator('#notificationOpenTaskBtn')).to_be_focused()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\bshow\b'))
    open_exact_saved_task(page, saved, scope)
    assert len(records(page)) == 1
    print('Feedback passed: hidden search save is persisted exactly once; focused Open survives 7 seconds and opens the correct edit form without changing scope', flush=True)


def edit_project(page, output):
    saved = create_task(page, '编辑后离开项目范围', project='当前项目')
    select_project(page, '当前项目')
    scope = current_scope(page)
    before = records(page)
    click_task_action(task_locator(page, saved['name']), 'edit')
    page.locator('#taskProject').fill('另一个项目')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_locator(page, saved['name'])).to_have_count(0)
    expect_outside_feedback(page)
    after = records(page)
    assert len(after) == 1 and set(after) == set(before), 'Editing project created another task'
    saved = after[saved['id']]
    assert saved['project'] == '另一个项目'
    assert current_scope(page) == scope
    capture(page, output, 'edit-project-outside')
    open_exact_saved_task(page, saved, scope)
    print('Feedback passed: project-changing edit remains saved under the same ID and can be opened from the unchanged project filter', flush=True)


def edit_calendar_date(page, output):
    today = datetime.now(timezone.utc).date()
    saved = create_task(page, '编辑后移到日历范围外', due_date=today.isoformat())
    select_view(page, 'calendar')
    task_button = page.locator(f'.calendar-detail-task[data-calendar-task-id="{saved["id"]}"]')
    expect(task_button).to_be_visible()
    scope = current_scope(page)
    before = records(page)
    task_button.click()
    expect(page.locator('#taskModal')).to_be_visible()
    target_date = (today + timedelta(days=70)).isoformat()
    page.locator('#dueDate').fill(target_date)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_button).to_have_count(0)
    expect_outside_feedback(page)
    after = records(page)
    assert len(after) == 1 and set(after) == set(before), 'Editing due date created another task'
    saved = after[saved['id']]
    assert saved['dueLocalDate'] == target_date
    assert current_scope(page) == scope, 'Saving an off-month edit navigated the calendar'
    capture(page, output, 'edit-calendar-outside')
    open_exact_saved_task(page, saved, scope)
    print('Feedback passed: an off-month date edit gives saved-task feedback while retaining the visible month and task ID', flush=True)


def replace_action(page, output):
    search_empty_scope(page, '可见范围')
    original = create_task(page, '第一条隐藏任务')
    expect_outside_feedback(page)
    visible = create_task(page, '可见范围中的普通新增任务')
    expect(task_locator(page, visible['name'])).to_have_count(1)
    expect(page.locator('#notificationText')).to_have_text('任务已添加')
    expect(page.locator('#notificationOpenTaskBtn')).to_be_hidden()
    expect(page.locator('#notificationUndoBtn')).to_be_visible()

    latest = create_task(page, '替换通知所指向的第二条隐藏任务')
    expect_outside_feedback(page)
    scope = current_scope(page)
    open_exact_saved_task(page, latest, scope)
    assert set(task['name'] for task in records(page).values()) == {original['name'], visible['name'], latest['name']}

    # A later, unrelated success must clear both the old Open action and its ID.
    page.locator('#saveSmartViewBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#savedViewNameInput').fill('反馈检查保存视图')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#notificationText')).to_have_text('视图已保存')
    expect(page.locator('#notificationOpenTaskBtn')).to_be_hidden()
    expect(page.locator('#notificationUndoBtn')).to_be_hidden()
    capture(page, output, 'replacement-clears-open-action')
    assert len(records(page)) == 3
    print('Feedback passed: ordinary visible saves retain success/Undo, newer hidden saves open their own task, and unrelated messages clear the old action', flush=True)


def quick_draft(page, output):
    search_empty_scope(page, '只显示这个范围')
    create_task(page, '隐藏任务与未提交快速记录')
    expect_outside_feedback(page)
    ensure_capture(page)
    draft = '不能因打开保存任务而丢失的快速记录 #草稿 /个人'
    page.locator('#quickAddInput').fill(draft)
    before = records(page)
    page.locator('#notificationOpenTaskBtn').click()
    expect(page.locator('#quickAddInput')).to_have_value(draft)
    assert records(page) == before, 'Opening a saved task submitted or modified the unsubmitted quick draft'
    capture(page, output, 'open-preserves-quick-draft')
    print('Feedback passed: Open saved task preserves unsubmitted quick-capture text and does not create another record', flush=True)


def notification_pause(page, output, interaction):
    saved = create_task(page, '通知真实计时检查 ' + interaction)
    notification = page.locator('#notification')
    action = page.locator('#notificationUndoBtn')
    expect(action).to_be_visible()
    expect(page.locator('#notificationOpenTaskBtn')).to_be_hidden()
    before = records(page)
    page.mouse.move(0, 0)
    assert not notification.evaluate('node => node.contains(document.activeElement)'), 'Ordinary success notification stole focus'
    page.wait_for_timeout(2500)
    if interaction == 'focus':
        action.focus()
    else:
        action.hover()
    page.wait_for_timeout(7000)
    expect(notification).to_have_class(re.compile(r'\bshow\b'))
    expect(action).to_be_visible()
    expect(action).to_be_enabled()
    if interaction == 'focus':
        expect(action).to_be_focused()
    capture(page, output, f'notification-paused-{interaction}')
    if interaction == 'focus':
        page.locator('#searchInput').focus()
    else:
        page.mouse.move(0, 0)
    resumed_at = time.monotonic()
    page.wait_for_timeout(900)
    expect(notification).to_have_class(re.compile(r'\bshow\b'))
    # About four seconds remained before pausing. A reset to 6.5 seconds would
    # violate this bound; immediate expiration would violate the check above.
    expect(notification).not_to_have_class(re.compile(r'\bshow\b'), timeout=4500)
    elapsed = time.monotonic() - resumed_at
    assert elapsed < 5.8, f'{interaction} restarted the full timeout instead of resuming the remaining lifetime: {elapsed:.2f}s'
    assert records(page) == before and len(before) == 1 and saved['id'] in before
    print(f'Feedback passed: {interaction} pauses real notification time for 7 seconds; leaving resumes the remaining lifetime ({elapsed:.2f}s)', flush=True)
    return {'interaction': interaction, 'resumed_seconds': round(elapsed, 3)}


def plain_notification_pause(page, output):
    page.locator('#saveSmartViewBtn').click()
    page.locator('#savedViewNameInput').fill('三秒通知真实计时')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    notification = page.locator('#notification')
    expect(page.locator('#notificationText')).to_have_text('视图已保存')
    expect(page.locator('#notificationUndoBtn')).to_be_hidden()
    expect(page.locator('#notificationOpenTaskBtn')).to_be_hidden()
    page.mouse.move(0, 0)
    page.wait_for_timeout(1000)
    page.locator('#workspaceNotificationClose').focus()
    page.wait_for_timeout(3500)
    expect(notification).to_have_class(re.compile(r'\bshow\b'))
    expect(page.locator('#workspaceNotificationClose')).to_be_focused()
    capture(page, output, 'plain-notification-paused')
    page.locator('#searchInput').focus()
    resumed_at = time.monotonic()
    page.wait_for_timeout(400)
    expect(notification).to_have_class(re.compile(r'\bshow\b'))
    expect(notification).not_to_have_class(re.compile(r'\bshow\b'), timeout=2300)
    elapsed = time.monotonic() - resumed_at
    assert elapsed < 2.8, f'Plain notification restarted its full three-second timer: {elapsed:.2f}s'
    assert records(page) == {}, 'Saving a view or waiting on a plain notification wrote task records'
    print(f'Feedback passed: ordinary three-second notification pauses while focused and resumes remaining time ({elapsed:.2f}s)', flush=True)
    return {'resumed_seconds': round(elapsed, 3)}


def undo_focus(page, output):
    created = [create_task(page, '批量撤销焦点任务 ' + str(index)) for index in range(3)]
    before = records(page)
    for origin in ('header', 'notification'):
        enter_batch_mode(page)
        for task in created[:2]:
            task_locator(page, task['name']).locator('.task-select-checkbox').check()
        page.locator('#batchCompleteBtn').click()
        expect(page.locator('#notificationUndoBtn')).to_be_visible()
        expect(page.locator('.task-item')).to_have_count(1)
        after = records(page)
        assert set(after) == set(before)
        for task in created[:2]:
            assert after[task['id']]['completed'] and after[task['id']]['completedAt']
        assert after[created[2]['id']] == before[created[2]['id']], 'Batch completion changed an unselected task'
        page.locator('#undoBtn' if origin == 'header' else '#notificationUndoBtn').click()
        expect(page.locator('.task-item')).to_have_count(3)
        expect(page.locator('#undoBtn')).to_be_hidden()
        assert records(page) == before, 'Batch Undo did not exactly restore its original records'
        page.wait_for_function("""() => {
            const active = document.activeElement;
            return active.matches('.task-select-checkbox, .task-more-toggle') &&
                Boolean(active.closest('.task-item')) && !active.disabled &&
                active.getBoundingClientRect().width > 0;
        }""")
        focused_id = page.evaluate('document.activeElement.closest(".task-item").dataset.taskId')
        assert focused_id in {str(task['id']) for task in created}, 'Undo focused a control outside the actual task list'
        capture(page, output, f'undo-focus-{origin}')
        page.keyboard.press('Tab')
        assert not page.evaluate('Boolean(document.activeElement.closest(".workspace-topbar"))'), 'Tab after Undo jumped to the top bar'
    print('Feedback passed: header and notification bulk Undo restore exact data and return focus to a live task control', flush=True)


def native_input_undo(page, output):
    create_task(page, '输入撤销不能撤回此任务')
    before = records(page)
    expect(page.locator('#undoBtn')).to_be_enabled()
    search = page.locator('#searchInput')
    search.focus()
    page.keyboard.type('native input undo', delay=25)
    expect(search).to_have_value('native input undo')
    page.keyboard.press('Control+z')
    expect(search).to_have_value('')
    expect(search).to_be_focused()
    expect(page.locator('#undoBtn')).to_be_enabled()
    assert records(page) == before, 'Ctrl+Z inside an input consumed the task Undo or changed task data'
    capture(page, output, 'native-input-undo')
    print('Feedback passed: Ctrl+Z in the search input keeps native text Undo and leaves task data/history intact', flush=True)


CASES = {
    'search': search_saved_task,
    'edit-project': edit_project,
    'edit-calendar': edit_calendar_date,
    'replacement': replace_action,
    'quick-draft': quick_draft,
    'pause-focus': lambda page, output: notification_pause(page, output, 'focus'),
    'pause-hover': lambda page, output: notification_pause(page, output, 'hover'),
    'pause-plain': plain_notification_pause,
    'undo-focus': undo_focus,
    'native-input-undo': native_input_undo,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', action='append', choices=tuple(CASES))
    parser.add_argument('--output-dir', type=Path, default=Path('/tmp/task-tracer-4.13.2-feedback'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=10000)
    results = []
    with production_server() as url, sync_playwright() as playwright:
        browser = getattr(playwright, args.browser).launch(**browser_launch_options())
        try:
            for name in args.case or CASES:
                context = browser.new_context(
                    viewport={'width': 390, 'height': 844}, locale='zh-CN',
                    timezone_id='UTC', reduced_motion='reduce',
                )
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                started = time.monotonic()
                try:
                    page.goto(url)
                    wait_for_app_ready(page)
                    assert get_task_records(page) == [], 'Regression context did not start with an empty task database'
                    detail = CASES[name](page, args.output_dir)
                    assert not errors, errors
                    results.append({'case': name, 'passed': True, 'seconds': round(time.monotonic() - started, 3), 'detail': detail})
                except Exception:
                    capture(page, args.output_dir, name + '-failure')
                    (args.output_dir / f'{name}-failure.txt').write_text(
                        traceback.format_exc() + '\n\n' + page.locator('body').aria_snapshot(), encoding='utf-8'
                    )
                    results.append({'case': name, 'passed': False, 'seconds': round(time.monotonic() - started, 3), 'page_errors': errors})
                    raise
                finally:
                    (args.output_dir / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
                    context.close()
        finally:
            browser.close()
    print('Workflow feedback passed: ' + ', '.join(result['case'] for result in results), flush=True)


if __name__ == '__main__':
    main()
