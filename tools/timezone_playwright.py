#!/usr/bin/env python3
"""Verify stored instants and wall times across DST, unusual offsets and zone changes."""
from __future__ import annotations

import argparse

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, exercise_export_backup, get_task_records,
    import_payload_replace, local_server, task_locator, wait_for_app_ready,
)


CASES = [
    ('NY spring before', '2026-03-08T06:30:00.000Z', 'America/New_York', '2026-03-08', '01:30'),
    ('NY spring after', '2026-03-08T07:30:00.000Z', 'America/New_York', '2026-03-08', '03:30'),
    ('NY fall first', '2026-11-01T05:30:00.000Z', 'America/New_York', '2026-11-01', '01:30'),
    ('NY fall second', '2026-11-01T06:30:00.000Z', 'America/New_York', '2026-11-01', '01:30'),
    ('Kathmandu quarter hour', '2026-01-15T18:30:00.000Z', 'Asia/Kathmandu', '2026-01-16', '00:15'),
    ('Lord Howe first', '2026-04-04T14:45:00.000Z', 'Australia/Lord_Howe', '2026-04-05', '01:45'),
    ('Lord Howe second', '2026-04-04T15:15:00.000Z', 'Australia/Lord_Howe', '2026-04-05', '01:45'),
    ('Kiritimati next day', '2026-10-23T12:30:00.000Z', 'Pacific/Kiritimati', '2026-10-24', '02:30'),
]


def fixture(identity, name, instant, zone):
    return {'id': identity, 'name': name, 'description': 'Synthetic timezone regression',
            'dueAt': instant, 'dueDate': instant, 'dueTimeZone': zone,
            'reminderOffset': -1, 'reminderRepeat': -1, 'repeatType': 'none',
            'completed': False, 'archived': False, 'subtasks': [],
            'createdAt': '2026-01-01T00:00:00.000Z', 'order': identity * 1000}


def import_and_wait(page, data, count):
    import_payload_replace(page, data)
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('.task-item')).to_have_count(count)
    return get_task_records(page)


def assert_due(record, instant, zone, date, time):
    assert record['dueAt'] == instant and record['dueDate'] == instant, \
        f'Exact due instant changed for {record["name"]}'
    assert record['dueTimeZone'] == zone, f'Task timezone changed for {record["name"]}'
    assert (record['dueLocalDate'], record['dueLocalTime']) == (date, time), \
        f'Wrong local date/time for {record["name"]}: {record["dueLocalDate"]} {record["dueLocalTime"]}'


def run(engine):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        context_options = {'accept_downloads': True, 'reduced_motion': 'reduce'}
        if engine != 'chromium':
            context_options['timezone_id'] = 'UTC'
        context = browser.new_context(**context_options)
        print(f'Timezone {engine}: {browser.version}', flush=True)
        try:
            page = context.new_page()
            client = context.new_cdp_session(page) if engine == 'chromium' else None
            if client:
                client.send('Emulation.setTimezoneOverride', {'timezoneId': 'UTC'})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            data = [fixture(index + 100, name, instant, zone)
                    for index, (name, instant, zone, _, _) in enumerate(CASES)]
            invalid = fixture(200, 'Invalid zone UTC fallback', '2026-10-23T04:15:00.000Z', 'Not/A_Real_Zone')
            undated = fixture(201, 'Undated invalid timezone', None, 'Not/A_Real_Zone')
            records = import_and_wait(page, data + [invalid, undated], len(data) + 2)
            by_name = {record['name']: record for record in records}
            for name, instant, zone, date, time in CASES:
                assert_due(by_name[name], instant, zone, date, time)
            assert_due(by_name[invalid['name']], invalid['dueAt'], 'UTC', '2026-10-23', '04:15')
            assert all(by_name[undated['name']][field] is None
                       for field in ('dueAt', 'dueDate', 'dueLocalDate', 'dueLocalTime', 'dueTimeZone'))
            page.reload()
            wait_for_app_ready(page)
            assert get_task_records(page) == records, 'Reload changed stored timezone fields'
            backup = exercise_export_backup(page)
            assert backup['tasks'] == records, 'JSON export changed stored timezone fields'
            assert import_and_wait(page, backup, len(records)) == records, 'JSON round-trip changed stored instants'
            print('Timezone passed: DST gaps/folds, half-hour/quarter-hour offsets, date crossing, invalid/undated zones and JSON round-trip', flush=True)

            for case_name in ('NY fall second', 'NY spring after'):
                original = by_name[case_name]
                task_locator(page, original['name']).locator('[data-action="edit"]').click()
                expect(page.locator('#taskModal')).to_be_visible()
                expect(page.locator('#dueDate')).to_have_value(original['dueLocalDate'])
                expect(page.locator('#dueTime')).to_have_value(original['dueLocalTime'])
                description = f'Edited {case_name} description without changing deadline'
                page.locator('#taskDesc').fill(description)
                page.locator('#submitBtn').click()
                expect(page.locator('#taskModal')).to_be_hidden()
                edited = next(record for record in get_task_records(page) if record['id'] == original['id'])
                assert_due(edited, original['dueAt'], original['dueTimeZone'], original['dueLocalDate'], original['dueLocalTime'])
                assert edited['description'] == description
            print('Timezone passed: unrelated edits preserve repeated-hour instants and overdue deadlines', flush=True)
            add_task(page, 'Historical planning entry', due_date='2026-03-08',
                     due_time='03:30', reminder_offset='-1')
            historical = next(record for record in get_task_records(page) if record['name'] == 'Historical planning entry')
            assert_due(historical, '2026-03-08T03:30:00.000Z', 'UTC', '2026-03-08', '03:30')
            print('Timezone passed: the full task form accepts a real historical deadline', flush=True)

            if engine == 'chromium':
                client.send('Emulation.setTimezoneOverride', {'timezoneId': 'America/New_York'})
                assert page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone') == 'America/New_York'
                shifted = fixture(202, 'Invalid zone after device zone change', invalid['dueAt'], 'Not/A_Real_Zone')
                shifted_record = import_and_wait(page, [shifted], 1)[0]
                assert_due(shifted_record, invalid['dueAt'], 'America/New_York', '2026-10-23', '00:15')
                print('Timezone passed: a previously invalid zone falls back to the current device zone after a live change', flush=True)
            else:
                print('Timezone note: live device-zone override is Chromium-only; other engines use explicit UTC context', flush=True)
            assert not errors, errors
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
