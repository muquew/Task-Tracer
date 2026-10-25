#!/usr/bin/env python3
"""Protect planned recurrence and useful statistics with small synthetic data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from recovery_management_playwright import stored
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, click_batch_action,
    click_task_action, enter_batch_mode, get_task_records, local_server,
    reveal_workspace_control, select_filter, select_language, select_project,
    select_sort, select_view, task_locator, wait_for_app_ready,
)


NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
TODAY = '2026-10-25'
ROOT = Path(__file__).resolve().parents[1]


def messages(page):
    code = page.locator('html').get_attribute('lang')
    return json.loads((ROOT / 'resources' / f'{code}.json').read_text())


def assert_plan(page, completed, total):
    labels = messages(page)['focus']
    key = 'summaryOne' if total == 1 else 'summary'
    expect(page.locator('#focusModeSummary')).to_have_text(
        labels[key].format(completed=completed, total=total))


def undo(page):
    expect(page.locator('#undoBtn')).to_be_enabled()
    page.locator('#undoBtn').click()
    prefix = messages(page)['undo']['restored'].split('{action}')[0]
    expect(page.locator('#notificationText')).to_contain_text(prefix)


def by_id(records):
    return {task['id']: task for task in records}


def assert_successors(before, after, root_ids):
    original = by_id(before)
    actual = by_id(after)
    assert len(after) == len(before) + len(root_ids), 'Completing selected occurrences added missing or duplicate successors'
    for identity, task in original.items():
        if identity not in root_ids:
            assert actual[identity] == task, 'Completing planned recurrence changed an unrelated task'
            continue
        current = actual[identity]
        assert current['completed'] and current['focusDate'] == TODAY
        successors = [task for task in after if task.get('repeatCreatedFrom') == identity]
        assert len(successors) == 1, 'A completed occurrence must have exactly one immediate successor'
        child = successors[0]
        assert child['id'] not in original and current['nextRepeatTaskId'] == child['id']
        assert child['focusDate'] is None, 'A future recurring occurrence silently joined today’s plan'
        assert not child['completed'] and not child['archived']
        assert child['dueLocalDate'] == '2026-10-26' and child['dueLocalTime'] == '09:00'


def planned_recurrence(page, url):
    clear_app_data(page, url)
    select_language(page, 'en')
    add_task(page, 'Planned single repeat', project='Plan', due_date=TODAY,
             due_time='09:00', repeat_type='daily', reminder_offset='-1')
    add_task(page, 'Protected unrelated task', project='Other', no_deadline=True)
    click_task_action(task_locator(page, 'Planned single repeat'), 'focus')
    reveal_workspace_control(page, '#focusModeToggleBtn').click()
    assert_plan(page, 0, 1)
    single_before = get_task_records(page)
    single_id = next(task['id'] for task in single_before if task['name'] == 'Planned single repeat')
    task_locator(page, 'Planned single repeat').locator('[data-action="toggle"]').click()
    assert_plan(page, 1, 1)
    assert_successors(single_before, get_task_records(page), {single_id})
    undo(page)
    assert_plan(page, 0, 1)
    assert get_task_records(page) == single_before, 'Single completion Undo failed to restore the exact pre-completion tasks'

    page.locator('#exitFocusModeBtn').click()
    add_task(page, 'Planned batch repeat', project='Plan', due_date=TODAY,
             due_time='09:00', repeat_type='daily', reminder_offset='-1')
    click_task_action(task_locator(page, 'Planned batch repeat'), 'focus')
    reveal_workspace_control(page, '#focusModeToggleBtn').click()
    assert_plan(page, 0, 2)
    batch_before = get_task_records(page)
    selected_ids = {task['id'] for task in batch_before if task['name'] in (
        'Planned single repeat', 'Planned batch repeat')}
    enter_batch_mode(page)
    for name in ('Planned single repeat', 'Planned batch repeat'):
        task_locator(page, name).locator('.task-select-checkbox').check()
    click_batch_action(page, 'complete')
    assert_plan(page, 2, 2)
    assert_successors(batch_before, get_task_records(page), selected_ids)
    undo(page)
    assert_plan(page, 0, 2)
    assert get_task_records(page) == batch_before, 'Batch completion Undo failed to restore the original occurrences and plan'
    print('Planned recurrence passed: single and batch completion keep the denominator, create unplanned successors, and Undo restores exact tasks', flush=True)


def seed_statistics(page):
    template = get_task_records(page)[0]

    def record(identity, name, due=None, completed=None, archived=False,
               project='Work', tag='review', focus=False):
        instant = f'{due[0]}T{due[1]}:00.000Z' if due else None
        return {**template, 'id': identity, 'name': name,
                'description': 'Synthetic craft statistics fixture',
                'createdAt': '2026-09-01T08:00:00.000Z', 'order': identity * 1000,
                'project': project, 'tags': [tag], 'focusDate': TODAY if focus else None,
                'completed': completed is not None,
                'completedAt': f'{completed}T10:00:00.000Z' if completed else None,
                'archived': archived, 'archivedAt': '2026-10-25T10:30:00.000Z' if archived else None,
                'dueDate': instant, 'dueAt': instant,
                'dueLocalDate': due[0] if due else None,
                'dueLocalTime': due[1] if due else None,
                'dueTimeZone': 'UTC' if due else None,
                'reminderOffset': -1, 'reminderRepeat': -1,
                'repeatType': 'none', 'repeatInterval': 1,
                'repeatSourceId': None, 'repeatCreatedFrom': None,
                'nextRepeatTaskId': None, 'subtasks': []}

    records = [
        record(100, 'Review finished today', completed='2026-10-25'),
        record(101, 'Review finished yesterday', completed='2026-10-24'),
        record(102, 'Review finished two days ago', completed='2026-10-23'),
        record(103, 'Review finished six days ago', completed='2026-10-19', archived=True),
        record(104, 'Review finished outside seven days', completed='2026-10-18'),
        record(105, 'Review finished without a recorded date', completed=''),
        record(201, 'Review overdue earlier day', due=('2026-10-24', '09:00')),
        record(202, 'Review today past deadline', due=(TODAY, '09:00')),
        record(203, 'Review today future deadline', due=(TODAY, '19:00')),
        record(204, 'Review future planned task', due=('2026-10-27', '09:00'), focus=True),
        record(205, 'Review without deadline'),
        record(301, 'Legacy archived unfinished', due=('2026-10-23', '09:00'), archived=True),
        record(302, 'Other tag overdue', due=('2026-10-23', '09:00'), tag='other'),
        record(303, 'Other project overdue', due=('2026-10-23', '09:00'), project='Personal'),
        record(304, 'Other project finished today', completed=TODAY, project='Personal'),
    ]
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
            revision.onsuccess = () => config.put({key:'taskRevision', value:(revision.result?.value || 0) + 1});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", records)
    page.reload()
    wait_for_app_ready(page)
    return get_task_records(page)


def statistics_history_and_actions(page, url):
    clear_app_data(page, url)
    select_language(page, 'en')
    add_task(page, 'Statistics fixture template', no_deadline=True)
    seed_statistics(page)
    reveal_workspace_control(page, '#focusModeToggleBtn').click()
    expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'true')
    select_project(page, 'Work')
    query = 'tag:review'
    page.locator('#searchInput').fill(query)
    select_view(page, 'stats')
    expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'false')
    before = stored(page)

    def phrase(section, key, count, **values):
        labels = messages(page)[section]
        key = key + 'One' if count == 1 and key + 'One' in labels else key
        return labels[key].format(count=count, **values)

    def assert_review():
        expect(page.locator('.stats-review-total')).to_have_text(
            phrase('statsInsights', 'reviewCompleted', 4))
        expect(page.locator('.stats-review-meta')).to_contain_text(
            phrase('statsInsights', 'todayReview', 1))
        expect(page.locator('.stats-review-meta')).to_contain_text(
            phrase('stats', 'streakDetail', 3))
        expected_days = [1, 0, 0, 0, 1, 1, 1]
        assert page.locator('.stats-trend-bar').evaluate_all(
            'bars => bars.map(bar => Number(bar.dataset.trendCount))') == expected_days
        assert page.locator('.stats-trend-count').all_text_contents() == [str(value) for value in expected_days]

    def assert_inventory(total, completed, archived, completion_percent):
        details = page.locator('details.stats-inventory')
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()
        for filter_name, count in (('all', total), ('completed', completed), ('overdue', 2), ('archived', archived)):
            expect(details.locator(f'.stats-mini[data-stats-filter="{filter_name}"] strong')).to_have_text(str(count))
        labels = messages(page)['stats']
        completed_card = details.locator('.stat-card').filter(
            has=page.locator('.stat-label').filter(has_text=labels['completionRate']))
        overdue_card = details.locator('.stat-card').filter(
            has=page.locator('.stat-label').filter(has_text=labels['overdueRate']))
        expect(completed_card.locator('.stat-value')).to_have_text(completion_percent)
        expect(overdue_card.locator('.stat-value')).to_have_text('50%')
        expect(completed_card.locator('.stat-detail')).to_have_text(
            phrase('stats', 'completedDetail', total, completed=completed, total=total))
        expect(overdue_card.locator('.stat-detail')).to_have_text(
            phrase('stats', 'overdueDetail', 4, overdue=2, total=4))

    assert_review()
    assert_inventory(10, 5, 2, '50%')
    assert stored(page) == before, 'Reading statistics mutated task records, recovery history, revision or settings'

    select_view(page, 'list')
    select_filter(page, 'completed')
    target = task_locator(page, 'Review finished today')
    click_task_action(target, 'archive')
    expect(target).to_have_count(0)
    after_archive = stored(page)
    original = by_id(before['tasks'])
    archived = by_id(after_archive['tasks'])
    assert archived[100]['archived'] and archived[100]['archivedAt']
    assert archived[100] == {**original[100], 'archived': True, 'archivedAt': archived[100]['archivedAt']}
    for identity, task in original.items():
        if identity != 100:
            assert archived[identity] == task, 'Archiving a reviewed completion changed another record'
    select_view(page, 'stats')
    assert_review()
    assert_inventory(9, 4, 3, '44%')
    assert stored(page) == after_archive, 'Reviewing archived completion history wrote data'

    expected_actions = (
        ('overdue', 'overdue', {201, 202}),
        ('today', 'today', {202, 203}),
        ('undated', 'none', {205}),
    )
    for action, due_term, expected_ids in expected_actions:
        page.locator('#searchInput').fill(query)
        select_view(page, 'stats')
        card = page.locator(f'button.stats-action-card[data-stats-action="{action}"]')
        expect(card.locator('.stats-action-value')).to_have_text(str(len(expected_ids)))
        expect(card).to_be_enabled()
        card.click()
        expect(page.locator('#viewTab-list')).to_have_attribute('aria-current', 'page')
        expect(page.locator('#workspaceTitle')).to_be_focused()
        expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'false')
        expect(page.locator('#focusModeBar')).to_be_hidden()
        actual_query = page.locator('#searchInput').input_value()
        assert actual_query.startswith(query), 'Statistics shortcut replaced the original search'
        assert 'status:active' in actual_query.split() and f'due:{due_term}' in actual_query.split()
        project = page.locator('#projectDropdown .dropdown-option[aria-selected="true"]').get_attribute('data-project')
        assert json.loads(project) == {'kind': 'project', 'name': 'Work'}, 'Statistics shortcut lost the selected project'
        actual_ids = set(page.locator('.task-item').evaluate_all(
            'tasks => tasks.map(task => Number(task.dataset.taskId))'))
        assert actual_ids == expected_ids, f'{action} shortcut count does not match the actual displayed task set'
        assert stored(page) == after_archive, 'Statistics shortcut wrote task or configuration data'

    page.locator('#searchInput').fill('tag:no-such-craft-tag')
    select_view(page, 'stats')
    for action, _, _ in expected_actions:
        card = page.locator(f'button.stats-action-card[data-stats-action="{action}"]')
        expect(card.locator('.stats-action-value')).to_have_text('0')
        expect(card).to_be_disabled()
    details = page.locator('details.stats-inventory')
    if details.get_attribute('open') is None:
        details.locator(':scope > summary').click()
    expect(details.locator('.stat-card .stat-value')).to_have_text(['—', '—'])
    expect(details.locator('[role="meter"]')).to_have_count(0)
    assert stored(page) == after_archive, 'Empty statistics scope wrote stored data'
    print('Statistics passed: archived completions retain today/7-day/streak history, inventory uses its own denominator, and three actionable counts match exact scoped task sets without writes', flush=True)


def statistics_drilldown_return(page, url):
    clear_app_data(page, url)
    select_language(page, 'en')
    add_task(page, 'Statistics return fixture template', no_deadline=True)
    baseline = seed_statistics(page)
    original_query = '  tag:review  '
    original_scope = {'query': original_query, 'project': {'kind': 'project', 'name': 'Work'},
                      'filter': 'completed'}

    def scope():
        project = page.locator('#projectDropdown .dropdown-option[aria-selected="true"]').get_attribute('data-project')
        status = page.locator('#filterDropdown .dropdown-option[aria-selected="true"]').get_attribute('data-filter')
        return {'query': page.locator('#searchInput').input_value(),
                'project': json.loads(project), 'filter': status}

    def assert_scope(expected):
        expect(page.locator('#searchInput')).to_have_value(expected['query'])
        assert scope() == expected, 'Returning to statistics changed the wrong visible search/project/status scope'

    def assert_ids(expected):
        expect(page.locator('.task-item')).to_have_count(len(expected))
        for identity in expected:
            expect(page.locator(f'.task-item[data-task-id="{identity}"]')).to_have_count(1)
        actual = set(page.locator('.task-item').evaluate_all(
            'items => items.map(item => Number(item.dataset.taskId))'))
        assert actual == expected, 'The visible task collection does not match the reviewed scope'

    def assert_counts(overdue=2, today=2, undated=1, week=4, completed_today=1):
        for action, count in (('overdue', overdue), ('today', today), ('undated', undated)):
            expect(page.locator(f'.stats-action-card[data-stats-action="{action}"] .stats-action-value')).to_have_text(str(count))
        labels = messages(page)
        week_key = 'reviewCompletedOne' if week == 1 else 'reviewCompleted'
        today_key = 'todayReviewOne' if completed_today == 1 else 'todayReview'
        expect(page.locator('.stats-review-total')).to_have_text(
            labels['statsInsights'][week_key].format(count=week))
        expect(page.locator('.stats-review-meta')).to_contain_text(
            labels['statsInsights'][today_key].format(count=completed_today))

    def begin_origin():
        select_view(page, 'list')
        select_project(page, 'Work')
        select_filter(page, original_scope['filter'])
        page.locator('#searchInput').fill(original_query)
        select_view(page, 'stats')
        assert_scope(original_scope)
        expect(page.locator('#statsReturnBtn')).to_be_hidden()
        assert_counts()

    def assert_return_visible():
        button = page.locator('#statsReturnBtn')
        expect(button).to_be_visible()
        expect(button).to_contain_text(messages(page)['craft']['returnToStats'])

    def drill(action, expected):
        card = page.locator(f'.stats-action-card[data-stats-action="{action}"]')
        expect(card.locator('.stats-action-value')).to_have_text(str(len(expected)))
        card.click()
        assert_return_visible()
        assert_ids(expected)
        target = scope()
        assert target['project'] == original_scope['project'] and target['filter'] == 'active'
        assert target['query'].startswith(original_query.strip())
        return target

    def return_to_origin(*, navigation=False, **counts):
        before_return = stored(page)
        if navigation:
            select_view(page, 'stats')
        else:
            page.locator('#statsReturnBtn').click()
        expect(page.locator('#viewTab-stats')).to_have_attribute('aria-current', 'page')
        expect(page.locator('#statsReturnBtn')).to_be_hidden()
        assert_scope(original_scope)
        assert_counts(**counts)
        assert stored(page) == before_return, 'Returning to statistics wrote tasks, revision, recovery history or settings'

    select_project(page, 'Work')
    select_filter(page, 'active')
    page.locator('#searchInput').fill('tag:other')
    page.locator('#saveSmartViewBtn').click()
    expect(page.locator('#savedViewNameInput')).to_be_visible()
    page.locator('#savedViewNameInput').fill('Craft return other tag')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    saved_view = page.locator('#savedViewsList .saved-view-apply').filter(has_text='Craft return other tag')
    expect(saved_view).to_have_count(1)
    assert get_task_records(page) == baseline, 'Saving a review view changed task records'

    begin_origin()
    target = drill('overdue', {201, 202})
    select_sort(page, 'created-desc')
    assert_return_visible()
    assert_scope(target)
    task_locator(page, 'Review overdue earlier day').locator('[data-action="toggle"]').click()
    assert_ids({202})
    assert_return_visible()
    completed = by_id(get_task_records(page))
    assert completed[201]['completed'] and completed[201]['completedAt']
    for identity, task in by_id(baseline).items():
        expected = {**task, 'completed': True, 'completedAt': completed[201]['completedAt']} if identity == 201 else task
        assert completed[identity] == expected, 'Completing a drilled task changed unrelated fields'
    return_to_origin(overdue=1, week=5, completed_today=2)
    expect(page.locator('#sortDropdown .dropdown-option[data-sort="created-desc"]')).to_have_attribute('aria-selected', 'true')
    undo(page)
    assert_counts()
    assert get_task_records(page) == baseline, 'Completion Undo after returning did not restore the original task records'

    begin_origin()
    drill('today', {202, 203})
    click_task_action(task_locator(page, 'Review today past deadline'), 'archive')
    assert_ids({203})
    assert_return_visible()
    archived = by_id(get_task_records(page))
    assert archived[202]['archived'] and archived[202]['archivedAt']
    for identity, task in by_id(baseline).items():
        expected = {**task, 'archived': True, 'archivedAt': archived[202]['archivedAt']} if identity == 202 else task
        assert archived[identity] == expected, 'Archiving a drilled task changed completion or another field'
    return_to_origin(navigation=True, overdue=1, today=1)
    undo(page)
    assert_counts()
    assert get_task_records(page) == baseline, 'Archive Undo after returning did not restore the original task records'

    begin_origin()
    target = drill('undated', {205})
    task_locator(page, 'Review without deadline').locator('[data-action="toggle"]').click()
    assert_ids(set())
    assert_return_visible()
    undo(page)
    assert_ids({205})
    assert_return_visible()
    assert_scope(target)
    assert get_task_records(page) == baseline, 'Undo within an empty drill did not restore exact task data'
    return_to_origin()

    for change in ('search', 'project', 'status', 'saved-view'):
        begin_origin()
        if change == 'status':
            inventory = page.locator('details.stats-inventory')
            if inventory.get_attribute('open') is None:
                inventory.locator(':scope > summary').click()
            inventory.locator('.stats-mini[data-stats-filter="all"]').click()
            assert_return_visible()
            assert_ids({100, 101, 102, 104, 105, 201, 202, 203, 204, 205})
            select_filter(page, 'active')
            expected_ids = {201, 202, 203, 204, 205}
            expected_counts = {'overdue': 2, 'today': 2, 'undated': 1}
        else:
            drill('overdue', {201, 202})
            if change == 'search':
                page.locator('#searchInput').fill('tag:other')
                expected_ids = {302}
            elif change == 'project':
                select_project(page, 'Personal')
                expected_ids = {303}
            else:
                reveal_workspace_control(page, saved_view).click()
                expected_ids = {302}
            expected_counts = {'overdue': 1, 'today': 0, 'undated': 0}
        expect(page.locator('#statsReturnBtn')).to_be_hidden()
        assert_ids(expected_ids)
        changed_scope = scope()
        before_navigation = stored(page)
        select_view(page, 'stats')
        expect(page.locator('#statsReturnBtn')).to_be_hidden()
        assert_scope(changed_scope)
        for action, count in expected_counts.items():
            expect(page.locator(f'.stats-action-card[data-stats-action="{action}"] .stats-action-value')).to_have_text(str(count))
        assert stored(page) == before_navigation, 'Statistics navigation wrote data after a real scope change'
    assert get_task_records(page) == baseline, 'Drilldown scope navigation changed task records'
    print('Statistics return passed: visible return survives completion/archive/empty-result Undo, recalculates latest data, preserves new sort, and real scope changes prevent stale restoration', flush=True)


def run(engine, selected):
    cases = {'focus': planned_recurrence, 'stats': statistics_history_and_actions,
             'return': statistics_drilldown_return}
    with local_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(playwright, engine).launch(**options)
        try:
            print(f'Craft plan/statistics: {engine} {browser.version}', flush=True)
            for name, check in cases.items():
                if selected not in ('all', name):
                    continue
                context = browser.new_context(timezone_id='UTC', reduced_motion='reduce',
                                              viewport={'width': 1280, 'height': 900})
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.clock.install(time=NOW)
                    check(page, url)
                    assert not errors, errors
                finally:
                    context.close()
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'focus', 'stats', 'return'), default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
