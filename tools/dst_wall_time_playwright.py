#!/usr/bin/env python3
"""Exercise real task forms at gaps/folds; persist canonical deadlines after reload."""
from __future__ import annotations

import argparse

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, exercise_export_backup,
    get_task_records, local_server, task_locator, wait_for_app_ready,
)


CASES = [
    ('New York spring gap', 'America/New_York', '2026-03-08', '02:30',
     '2026-03-08T07:30:00.000Z', '2026-03-08', '03:30'),
    ('New York autumn fold', 'America/New_York', '2026-11-01', '01:30',
     '2026-11-01T05:30:00.000Z', '2026-11-01', '01:30'),
    ('Berlin spring gap', 'Europe/Berlin', '2026-03-29', '02:30',
     '2026-03-29T01:30:00.000Z', '2026-03-29', '03:30'),
    ('Berlin autumn fold', 'Europe/Berlin', '2026-10-25', '02:30',
     '2026-10-25T00:30:00.000Z', '2026-10-25', '02:30'),
    ('Lord Howe half-hour gap', 'Australia/Lord_Howe', '2026-10-04', '02:15',
     '2026-10-03T15:45:00.000Z', '2026-10-04', '02:45'),
    ('Lord Howe half-hour fold', 'Australia/Lord_Howe', '2026-04-05', '01:45',
     '2026-04-04T14:45:00.000Z', '2026-04-05', '01:45'),
    ('Apia skipped day', 'Pacific/Apia', '2011-12-30', '12:00',
     '2011-12-30T22:00:00.000Z', '2011-12-31', '12:00'),
    ('Kathmandu quarter offset', 'Asia/Kathmandu', '2026-01-16', '00:15',
     '2026-01-15T18:30:00.000Z', '2026-01-16', '00:15'),
]


def assert_due(record, zone, instant, date, time):
    assert record['dueAt'] == record['dueDate'] == instant, record
    assert (record['dueLocalDate'], record['dueLocalTime']) == (date, time), record
    aliases = {'Asia/Kathmandu', 'Asia/Katmandu'} if zone == 'Asia/Kathmandu' else {zone}
    assert record['dueTimeZone'] in aliases, record


def run(engine: str) -> None:
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'Deadline wall time {engine}: {browser.version}', flush=True)
        try:
            for name, zone, entered_date, entered_time, instant, actual_date, actual_time in CASES:
                context = browser.new_context(timezone_id=zone, reduced_motion='reduce', accept_downloads=True)
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    clear_app_data(page, url)
                    add_task(page, name, due_date=entered_date, due_time=entered_time, reminder_offset='-1')
                    expect(page.locator('#taskModal')).to_be_hidden()
                    records = get_task_records(page)
                    assert len(records) == 1
                    assert_due(records[0], zone, instant, actual_date, actual_time)
                    task_locator(page, name).locator('[data-action="edit"]').click()
                    expect(page.locator('#dueDate')).to_have_value(actual_date)
                    expect(page.locator('#dueTime')).to_have_value(actual_time)
                    page.locator('#taskDesc').fill('Synthetic description; deadline unchanged')
                    page.locator('#submitBtn').click()
                    expect(page.locator('#taskModal')).to_be_hidden()
                    edited = get_task_records(page)
                    assert len(edited) == 1
                    assert_due(edited[0], zone, instant, actual_date, actual_time)
                    assert edited[0]['description'] == 'Synthetic description; deadline unchanged'
                    page.reload()
                    wait_for_app_ready(page)
                    assert get_task_records(page) == edited, 'Reload changed a canonical deadline'
                    exported = exercise_export_backup(page)
                    assert exported['tasks'] == edited, 'Downloaded backup changed the saved deadline'
                    assert not errors, errors
                    print(f'Wall time passed: {name}; {entered_date} {entered_time} -> {actual_date} {actual_time}', flush=True)
                finally:
                    context.close()
        finally:
            browser.close()
    print(f'Deadline wall time {engine}: all {len(CASES)} form/edit/reload/export cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
