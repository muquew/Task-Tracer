"""Shared repeat lineage fixtures and assertions; no test entry point."""
from __future__ import annotations
from playwright.sync_api import expect
from tests.support.import_reference import finish_occurrence
from tests.support.browser import click_task_action
from tests.support.browser import (
    add_task,
    clear_app_data,
    get_task_records,
    import_payload_replace,
    select_filter,
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
    click_task_action(row(page, identity), 'edit')
    page.locator('#taskName').fill('Manually planned future')
    page.locator('#taskDesc').fill('Preserve future-only description and checklist')
    page.locator('#dueDate').fill('2026-12-15')
    page.locator('#dueTime').fill('15:45')
    page.locator('#subtaskInput').fill(extra_subtask)
    page.locator('#addSubtaskBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    return record(page, identity)
