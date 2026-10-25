#!/usr/bin/env python3
"""Preserve edited future occurrences when old recurring tasks are reopened."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from import_reference_playwright import finish_occurrence
from recovery_management_playwright import stored
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, exercise_export_backup,
    get_task_records, import_payload_replace, local_server, select_filter, wait_for_app_ready,
)


def row(page, identity):
    return page.locator(f'.task-item[data-task-id="{identity}"]')


def record(page, identity):
    return next(task for task in get_task_records(page) if task['id'] == identity)


def reopen(page, identity):
    row(page, identity).locator('[data-action="toggle"]').click()
    page.wait_for_function("""id => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const request = db.transaction('tasks').objectStore('tasks').get(id);
            request.onsuccess = () => {db.close(); resolve(request.result?.completed === false);};
            request.onerror = () => reject(request.error);
        };
    })""", arg=identity)
    expect(row(page, identity).locator('[data-action="toggle"]')).to_be_enabled()


def delete(page, identity):
    row(page, identity).locator('[data-action="delete"]').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(row(page, identity)).to_have_count(0)


def seed_legacy_deleted_occurrence(page, identity):
    page.evaluate("""id => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            tx.objectStore('tasks').delete(id);
            const config = tx.objectStore('config');
            const revision = config.get('taskRevision');
            revision.onsuccess = () => config.put({key: 'taskRevision', value: (revision.result?.value || 0) + 1});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", identity)
    page.reload()
    wait_for_app_ready(page)
    select_filter(page, 'all')


def prepare(page, url, length=3, root_zero=False):
    clear_app_data(page, url)
    if root_zero:
        import_payload_replace(page, [{
            'id': 0, 'name': 'Lineage root', 'description': 'Original series record',
            'dueAt': '2027-01-01T08:30:00.000Z', 'dueDate': '2027-01-01T08:30:00.000Z',
            'dueTimeZone': 'UTC', 'repeatType': 'daily', 'repeatInterval': 1,
            'reminderOffset': -1, 'reminderRepeat': -1,
            'subtasks': [{'id': 31, 'text': 'Original checklist', 'completed': True}],
        }])
    else:
        add_task(page, 'Lineage root', due_date='2027-01-01', due_time='08:30',
                 repeat_type='daily', reminder_offset='-1', subtasks=['Original checklist'])
    select_filter(page, 'all')
    identities = [get_task_records(page)[0]['id']]
    for _ in range(length - 1):
        finish_occurrence(page, identities[-1])
        children = [task for task in get_task_records(page) if task.get('repeatCreatedFrom') == identities[-1]]
        assert len(children) == 1
        identities.append(children[0]['id'])
    return identities


def edit_future(page, identity, extra_subtask='Future-only checklist'):
    row(page, identity).locator('[data-action="edit"]').click()
    page.locator('#taskName').fill('Manually planned future')
    page.locator('#taskDesc').fill('Preserve future-only description and checklist')
    page.locator('#dueDate').fill('2026-12-15')
    page.locator('#dueTime').fill('15:45')
    page.locator('#subtaskInput').fill(extra_subtask)
    page.locator('#addSubtaskBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    return record(page, identity)


def assert_no_new_records(before, after, changed_id):
    assert len(after) == len(before), 'An old occurrence created an extra future task'
    latest = {task['id']: task for task in after}
    assert set(latest) == {task['id'] for task in before}
    for original in before:
        if original['id'] != changed_id:
            assert latest[original['id']] == original, 'A surviving task or edited future changed'


def assert_skip_blocked(page, identity):
    before = stored(page)
    undo_title = page.locator('#undoBtn').get_attribute('title')
    action = row(page, identity).locator('[data-action="skip-repeat"]')
    expect(action).to_be_visible()
    action.click()
    language = page.locator('html').get_attribute('lang')
    translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
    expect(page.locator('#notificationText')).to_have_text(translations['messages']['task']['repeatAlreadyScheduled'])
    assert stored(page) == before, 'Blocked Skip changed tasks, revision, history or configuration'
    assert page.locator('#undoBtn').get_attribute('title') == undo_title
    assert not record(page, identity)['completed'], 'Blocked Skip falsely completed the old occurrence'


def undo_recomplete(page, url):
    identities = prepare(page, url, length=1, root_zero=True)
    baseline = get_task_records(page)
    finish_occurrence(page, identities[0])
    first_child = next(task for task in get_task_records(page) if task['id'] != identities[0])
    page.locator('#undoBtn').click()
    expect(row(page, first_child['id'])).to_have_count(0)
    assert get_task_records(page) == baseline
    finish_occurrence(page, identities[0])
    after = get_task_records(page)
    assert len(after) == 2
    child = next(task for task in after if task['id'] != identities[0])
    assert child['id'] != first_child['id'] and child['repeatSourceId'] == 0
    assert len(child['subtasks']) == 1 and not child['subtasks'][0]['completed']


def edited_future(page, url):
    root, future_id = prepare(page, url, length=2)
    future = edit_future(page, future_id)
    reopen(page, root)
    assert_skip_blocked(page, root)
    before = get_task_records(page)
    finish_occurrence(page, root)
    after = get_task_records(page)
    assert_no_new_records(before, after, root)
    assert record(page, future_id) == future
    assert [task['id'] for task in after if not task['completed']] == [future_id]


def deleted_nonroot_middle(page, url):
    root, old, middle, future_id = prepare(page, url, length=4)
    future = edit_future(page, future_id)
    reopen(page, old)
    delete(page, middle)
    assert record(page, old)['nextRepeatTaskId'] == future_id
    future = {**future, 'repeatCreatedFrom': old}
    assert record(page, future_id) == future, 'Deletion changed future user fields or reconnected the wrong predecessor'
    future = edit_future(page, future_id, 'Post-deletion edit checklist')
    assert future['repeatCreatedFrom'] == old, 'Editing from stale UI wrote the deleted predecessor back'
    assert_skip_blocked(page, old)
    before = get_task_records(page)
    finish_occurrence(page, old)
    after = get_task_records(page)
    assert_no_new_records(before, after, old)
    assert record(page, future_id) == future
    assert [task['id'] for task in after if not task['completed']] == [future_id]


def root_roundtrip(page, url):
    root, middle, future_id = prepare(page, url, length=3, root_zero=True)
    future = edit_future(page, future_id)
    reopen(page, root)
    delete(page, middle)
    future = {**future, 'repeatCreatedFrom': root}
    assert record(page, future_id) == future
    backup = exercise_export_backup(page)
    import_payload_replace(page, backup)
    select_filter(page, 'all')
    assert record(page, root)['nextRepeatTaskId'] == future_id
    assert record(page, future_id) == future and future['repeatSourceId'] == 0
    assert_skip_blocked(page, root)
    before = get_task_records(page)
    finish_occurrence(page, root)
    after = get_task_records(page)
    assert_no_new_records(before, after, root)
    assert record(page, future_id) == future


def legacy_ghost(page, url):
    root, old, middle, future_id = prepare(page, url, length=4)
    future = edit_future(page, future_id)
    reopen(page, old)
    seed_legacy_deleted_occurrence(page, middle)
    assert record(page, old)['nextRepeatTaskId'] == middle
    assert record(page, future_id) == future and future['repeatCreatedFrom'] == middle
    assert_skip_blocked(page, old)
    before = get_task_records(page)
    finish_occurrence(page, old)
    after = get_task_records(page)
    assert_no_new_records(before, after, old)
    assert record(page, future_id) == future


def legacy_roundtrip(page, url):
    root, middle, future_id = prepare(page, url, length=3, root_zero=True)
    future = edit_future(page, future_id)
    reopen(page, root)
    seed_legacy_deleted_occurrence(page, middle)
    backup = exercise_export_backup(page)
    import_payload_replace(page, backup)
    select_filter(page, 'all')
    assert record(page, root)['nextRepeatTaskId'] is None
    future = {**future, 'repeatCreatedFrom': None}
    assert record(page, future_id) == future and future['repeatSourceId'] == 0
    assert_skip_blocked(page, root)
    before = get_task_records(page)
    finish_occurrence(page, root)
    assert_no_new_records(before, get_task_records(page), root)
    assert record(page, future_id) == future


def tail_and_other_family(page, url):
    root, tail = prepare(page, url, length=2)
    reopen(page, root)
    ancestor = record(page, root)
    add_task(page, 'Different recurrence family', due_date='2027-01-01', due_time='08:30',
             repeat_type='daily', reminder_offset='-1', subtasks=['Other family checklist'])
    other = next(task for task in get_task_records(page) if task['id'] not in (root, tail))
    row(page, other['id']).locator('[data-action="edit"]').click()
    page.locator('#taskName').fill('Lineage root')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    other = record(page, other['id'])
    before = get_task_records(page)
    finish_occurrence(page, tail)
    after = get_task_records(page)
    added = [task for task in after if task['id'] not in {record['id'] for record in before}]
    assert len(added) == 1 and added[0]['repeatCreatedFrom'] == tail
    assert added[0]['repeatSourceId'] == root and added[0]['dueLocalDate'] == '2027-01-03'
    assert record(page, root) == ancestor and record(page, other['id']) == other
    before_skip = get_task_records(page)
    action = row(page, added[0]['id']).locator('[data-action="skip-repeat"]')
    action.click()
    after_skip = get_task_records(page)
    assert_no_new_records(before_skip, after_skip, added[0]['id'])
    assert record(page, added[0]['id'])['dueLocalDate'] == '2027-01-04'


def deleted_terminal(page, url):
    root, future_id = prepare(page, url, length=2)
    delete(page, future_id)
    reopen(page, root)
    finish_occurrence(page, root)
    after = get_task_records(page)
    assert len(after) == 2
    future = next(task for task in after if task['id'] != root)
    assert future['id'] != future_id and future['repeatCreatedFrom'] == root
    assert future['dueLocalDate'] == '2027-01-02'


def self_link(page, url):
    clear_app_data(page, url)
    import_payload_replace(page, [{
        'id': 0, 'name': 'Self-linked zero source', 'repeatType': 'daily',
        'dueAt': '2027-01-01T08:30:00.000Z', 'dueDate': '2027-01-01T08:30:00.000Z',
        'dueTimeZone': 'UTC', 'reminderOffset': -1, 'repeatSourceId': 0,
        'repeatCreatedFrom': 0, 'nextRepeatTaskId': 0,
    }])
    select_filter(page, 'all')
    row(page, 0).locator('[data-action="skip-repeat"]').click()
    assert record(page, 0)['dueLocalDate'] == '2027-01-02'
    finish_occurrence(page, 0)
    after = get_task_records(page)
    assert len(after) == 2
    child = next(task for task in after if task['id'] != 0)
    assert child['repeatSourceId'] == 0 and child['dueLocalDate'] == '2027-01-03'


CASES = {
    'undo': undo_recomplete,
    'edited': edited_future,
    'nonroot': deleted_nonroot_middle,
    'roundtrip': root_roundtrip,
    'legacy-ghost': legacy_ghost,
    'legacy-roundtrip': legacy_roundtrip,
    'tail': tail_and_other_family,
    'terminal': deleted_terminal,
    'self': self_link,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', *CASES), default='all')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with local_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if args.browser == 'chromium' else {'headless': True}
        browser = getattr(playwright, args.browser).launch(**options)
        passed = []
        try:
            for name, exercise in CASES.items():
                if args.case not in ('all', name):
                    continue
                context = browser.new_context(timezone_id='UTC', reduced_motion='reduce', accept_downloads=True)
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    exercise(page, url)
                    assert not errors, errors
                    passed.append(name)
                    print(f'Repeat lineage {args.browser}: {name} passed', flush=True)
                finally:
                    context.close()
            report = {'browser': args.browser, 'browser_version': browser.version, 'cases': passed, 'passed': True}
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report), flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
