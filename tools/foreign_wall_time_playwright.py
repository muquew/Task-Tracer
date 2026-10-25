#!/usr/bin/env python3
"""Keep a task's civil deadline intact when the device skips that wall time."""
from __future__ import annotations

import argparse
import json

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import (
    browser_launch_options, clear_app_data, exercise_export_backup, get_task_records,
    import_payload_replace, local_server, select_view, task_locator, wait_for_app_ready,
)
from timezone_playwright import fixture


CASES = [
    ('New York foreign spring gap', 'America/New_York', '2026-03-08', '02:30'),
    ('Berlin foreign spring gap', 'Europe/Berlin', '2026-03-29', '02:30'),
    ('Lord Howe foreign half-hour gap', 'Australia/Lord_Howe', '2026-10-04', '02:15'),
    ('Apia foreign skipped date', 'Pacific/Apia', '2011-12-30', '12:00'),
    ('New York foreign autumn fold', 'America/New_York', '2026-11-01', '01:30'),
    ('Kathmandu ordinary control', 'Asia/Kathmandu', '2026-01-16', '00:15'),
]


def run(engine):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(**options)
        try:
            for name, host, day, time in CASES:
                context = browser.new_context(timezone_id=host, locale='en-US',
                                              reduced_motion='reduce', accept_downloads=True)
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    clear_app_data(page, url)
                    instant = f'{day}T{time}:00.000Z'
                    imported = [fixture(101, name, instant, 'UTC'),
                                fixture(102, 'Undated control', None, 'UTC')]
                    import_payload_replace(page, imported)
                    expect(page.locator('#taskModal')).to_be_hidden()
                    expect(page.locator('.task-item')).to_have_count(2)
                    baseline = get_task_records(page)
                    original = next(task for task in baseline if task['id'] == 101)
                    assert (original['dueLocalDate'], original['dueLocalTime']) == (day, time)

                    page.locator('#searchInput').fill(f'due:{day}')
                    expect(page.locator('.task-item .task-name')).to_have_text([name])
                    assert get_task_records(page) == baseline, 'Date search wrote task records'
                    page.locator('#clearSearchBtn').click()
                    select_view(page, 'timeline')
                    title = page.locator('.timeline-group').filter(has=task_locator(page, name))
                    expected_title = page.evaluate("""day => new Intl.DateTimeFormat(document.documentElement.lang, {
                        weekday:'long',month:'short',day:'numeric',year:'numeric',timeZone:'UTC'
                    }).format(new Date(day+'T12:00:00Z'))""", day)
                    expect(title.locator('.timeline-date-title > span').first).to_have_text(expected_title)
                    assert get_task_records(page) == baseline, 'Timeline rendering wrote task records'

                    task_locator(page, name).locator('[data-action="edit"]').click()
                    expect(page.locator('#dueDate')).to_have_value(day)
                    expect(page.locator('#dueTime')).to_have_value(time)
                    description = f'Only the description changed: {host}'
                    page.locator('#taskDesc').fill(description)
                    page.locator('#submitBtn').click()
                    expect(page.locator('#taskModal')).to_be_hidden()
                    edited = get_task_records(page)
                    expected = [{**task, 'description': description} if task['id'] == 101 else task
                                for task in baseline]
                    assert edited == expected, 'An unrelated edit changed deadline or other task fields'
                    page.reload()
                    wait_for_app_ready(page)
                    assert get_task_records(page) == expected, 'Reload changed a foreign civil deadline'
                    exported = exercise_export_backup(page)
                    assert exported['tasks'] == expected, 'Real JSON download changed task fields'
                    assert not errors, errors
                    print(f'Foreign wall time passed: {name}; exact search, timeline, edit, reload and download', flush=True)
                finally:
                    context.close()
            print(json.dumps({'browser_engine': engine, 'browser': browser.version,
                              'cases': len(CASES), 'passed': True}), flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    run(parser.parse_args().browser)
