#!/usr/bin/env python3
"""Verify optional imported recurrence references and valid task ID zero."""
from __future__ import annotations

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    browser_launch_options, clear_app_data, due_fields_from_now, exercise_export_backup,
    get_task_records, import_payload_replace, local_server, select_filter, wait_for_app_ready,
)

REFERENCE_FIELDS = ('repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId')


def finish_occurrence(page, task_id):
    select_filter(page, 'all')
    button = page.locator(f'.task-item[data-task-id="{task_id}"] [data-action="toggle"]')
    expect(button).to_be_enabled()
    button.click()
    page.wait_for_function("""id => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction('tasks');
            const task = tx.objectStore('tasks').get(id);
            tx.oncomplete = () => { db.close(); resolve(task.result?.completed === true); };
            tx.onabort = () => reject(tx.error);
        };
    })""", arg=task_id)
    expect(page.locator(f'.task-item[data-task-id="{task_id}"] [data-action="toggle"]')).to_be_enabled()


def assert_nullable_references(page):
    due = due_fields_from_now(1440)
    records = [
        {'id': 0, 'name': 'Valid zero ID holder'},
        {'id': 11, 'name': 'Nullable references', 'repeatType': 'daily', **due,
         **dict.fromkeys(REFERENCE_FIELDS)},
        {'id': 12, 'name': 'Blank references',
         'repeatSourceId': '', 'repeatCreatedFrom': '  ', 'nextRepeatTaskId': '\t'},
        {'id': 13, 'name': 'Invalid references',
         'repeatSourceId': False, 'repeatCreatedFrom': 'NaN', 'nextRepeatTaskId': 'Infinity'},
        {'id': 14, 'name': 'Valid zero reference',
         'repeatSourceId': 0, 'repeatCreatedFrom': '0', 'nextRepeatTaskId': None},
    ]
    import_payload_replace(page, records)
    by_id = {record['id']: record for record in get_task_records(page)}
    for task_id in (0, 11, 12, 13):
        assert all(by_id[task_id][field] is None for field in REFERENCE_FIELDS), \
            f'Absent/invalid recurrence reference became a task link: {by_id[task_id]}'
    assert by_id[14]['repeatSourceId'] == 0 and by_id[14]['repeatCreatedFrom'] == 0
    assert by_id[14]['nextRepeatTaskId'] is None
    finish_occurrence(page, 11)
    records = get_task_records(page)
    source = next(record for record in records if record['id'] == 11)
    children = [record for record in records if record.get('repeatCreatedFrom') == 11]
    assert len(children) == 1 and source['nextRepeatTaskId'] == children[0]['id'], \
        'An unrelated task with ID zero suppressed the next occurrence'
    print('Import references passed: null/blank/invalid stay absent; real zero links stay valid', flush=True)



def assert_invalid_ids_do_not_claim_zero(page):
    import_payload_replace(page, [
        {'id': None, 'name': 'Null task ID'},
        {'id': '', 'name': 'Blank task ID'},
        {'id': False, 'name': 'Boolean task ID'},
        {'id': 'Infinity', 'name': 'Nonfinite task ID'},
        {'id': 0, 'name': 'Explicit zero task ID'},
        {'id': 41, 'name': 'Explicit zero child', 'repeatSourceId': 0, 'repeatCreatedFrom': '0'},
    ])
    records = get_task_records(page)
    by_name = {record['name']: record for record in records}
    assert by_name['Explicit zero task ID']['id'] == 0, 'An invalid raw ID claimed the valid explicit ID zero'
    assert len({record['id'] for record in records}) == len(records)
    for name in ('Null task ID', 'Blank task ID', 'Boolean task ID', 'Nonfinite task ID'):
        assert by_name[name]['id'] != 0
    child = by_name['Explicit zero child']
    assert child['repeatSourceId'] == 0 and child['repeatCreatedFrom'] == 0, 'Invalid IDs made a valid zero reference ambiguous'
    print('Import references passed: invalid task IDs cannot claim explicit zero or erase its links', flush=True)


def assert_zero_lineage(page):
    import_payload_replace(page, [{
        'id': 0, 'name': 'Zero root recurrence', 'repeatType': 'daily', 'repeatInterval': 1,
        **due_fields_from_now(1440), **dict.fromkeys(REFERENCE_FIELDS),
    }])
    finish_occurrence(page, 0)
    records = get_task_records(page)
    assert len(records) == 2, 'Completing recurring task zero did not create its next occurrence'
    child = next(record for record in records if record['id'] != 0)
    assert child['repeatSourceId'] == 0 and child['repeatCreatedFrom'] == 0
    finish_occurrence(page, child['id'])
    records = get_task_records(page)
    assert len(records) == 3, 'Completing the child did not create a grandchild'
    grandchild = next(record for record in records if record['id'] not in (0, child['id']))
    assert grandchild['repeatSourceId'] == 0, 'The zero-valued recurrence root was lost'
    assert grandchild['repeatCreatedFrom'] == child['id']
    assert grandchild['nextRepeatTaskId'] is None
    page.reload()
    wait_for_app_ready(page)
    assert get_task_records(page) == records, 'Reload changed recurrence links'
    backup = exercise_export_backup(page)
    import_payload_replace(page, backup)
    assert get_task_records(page) == records, 'JSON round-trip changed recurrence links'
    print('Import references passed: zero-root recurrence survives two generations, reload and JSON round-trip', flush=True)



def assert_self_link_recovery(page):
    import_payload_replace(page, [{
        'id': 0, 'name': 'Previously corrupted self link', 'repeatType': 'daily',
        **due_fields_from_now(1440), 'repeatSourceId': 0,
        'repeatCreatedFrom': 0, 'nextRepeatTaskId': 0,
    }])
    finish_occurrence(page, 0)
    records = get_task_records(page)
    assert len(records) == 2, 'A self-linked old recurrence could not recover its next occurrence'
    root = next(record for record in records if record['id'] == 0)
    child = next(record for record in records if record['id'] != 0)
    assert root['nextRepeatTaskId'] == child['id'] and child['repeatSourceId'] == 0
    print('Import references passed: a previously corrupted self-link can resume recurrence', flush=True)


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            assert_nullable_references(page)
            assert_invalid_ids_do_not_claim_zero(page)
            assert_zero_lineage(page)
            assert_self_link_recovery(page)
            assert not errors, errors
            context.close()
        finally:
            browser.close()


if __name__ == '__main__':
    run()
