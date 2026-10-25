#!/usr/bin/env python3
"""Keep recurrence calendar arithmetic independent of the device timezone."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import (
    browser_launch_options, clear_app_data, get_task_records,
    import_payload_replace, local_server, task_locator, wait_for_app_ready,
)


@dataclass(frozen=True)
class Case:
    name: str
    repeat: str
    start: str
    next_date: str
    time: str = '02:30'
    zone: str = 'UTC'
    interval: int = 1
    weekdays: tuple[int, ...] = ()


CASES = (
    Case('daily foreign spring gap', 'daily', '2026-03-07', '2026-03-08'),
    Case('weekly foreign spring gap', 'weekly', '2026-03-01', '2026-03-08'),
    Case('selected Sunday foreign spring gap', 'weekly-days', '2026-03-06', '2026-03-08', weekdays=(0,)),
    Case('monthly foreign spring gap', 'monthly', '2026-02-08', '2026-03-08'),
    Case('last day next month', 'monthly-last', '2026-02-28', '2026-03-31'),
    Case('custom foreign spring gap', 'custom', '2026-03-05', '2026-03-08', interval=3),
    Case('monthly clamp', 'monthly', '2026-01-31', '2026-02-28'),
    Case('monthly leap clamp', 'monthly', '2024-01-31', '2024-02-29'),
    Case('weekly year boundary', 'weekly', '2025-12-29', '2026-01-05'),
    Case('NY target spring', 'daily', '2026-03-07', '2026-03-08', '10:30', 'America/New_York'),
    Case('NY target fall', 'daily', '2026-10-31', '2026-11-01', '10:30', 'America/New_York'),
    Case('Lord Howe target half-hour', 'daily', '2026-04-04', '2026-04-05', '10:30', 'Australia/Lord_Howe'),
    Case('Kathmandu target quarter-hour', 'daily', '2026-01-15', '2026-01-16', '00:15', 'Asia/Kathmandu'),
    Case('UTC date skipped by foreign host', 'daily', '2011-12-29', '2011-12-30'),
    Case('legacy selected weekday fallback', 'weekly-days', '2011-12-30', '2012-01-06'),
)


def instant(date, time, zone):
    wall = datetime.fromisoformat(f'{date}T{time}').replace(tzinfo=ZoneInfo(zone))
    return wall.astimezone(ZoneInfo('UTC')).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def fixture(identity, name, case, paused=False):
    due = instant(case.start, case.time, case.zone)
    return {
        'id': identity, 'name': name, 'description': 'Synthetic timezone-independent recurrence',
        'dueAt': due, 'dueDate': due, 'dueLocalDate': case.start, 'dueLocalTime': case.time,
        'dueTimeZone': case.zone, 'repeatType': case.repeat, 'repeatInterval': case.interval,
        'repeatWeekdays': list(case.weekdays), 'repeatPaused': paused,
        'reminderOffset': -1, 'reminderRepeat': -1, 'project': 'Recurrence regression',
        'tags': ['repeat', '中文'], 'subtasks': [{'id': identity * 10, 'text': 'Repeat child', 'completed': True}],
        'completed': False, 'archived': False, 'createdAt': '2026-01-01T00:00:00.000Z',
        'order': identity * 1000,
    }


def assert_due(task, case):
    expected = {
        'dueAt': instant(case.next_date, case.time, case.zone),
        'dueDate': instant(case.next_date, case.time, case.zone),
        'dueLocalDate': case.next_date, 'dueLocalTime': case.time, 'dueTimeZone': case.zone,
    }
    assert all(task[key] == value for key, value in expected.items()), \
        f'{case.name}: expected {expected}, got { {key: task[key] for key in expected} }'


def assert_others_unchanged(before, after, changed_id):
    by_id = {task['id']: task for task in after}
    for record in before:
        if record['id'] != changed_id:
            assert by_id.get(record['id']) == record, f'Recurrence changed unrelated task {record["id"]}'


def run_host(browser, url, host):
    context = browser.new_context(timezone_id=host, accept_downloads=True, reduced_motion='reduce')
    observed = []
    try:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(page, url)
        data = []
        for index, case in enumerate(CASES):
            data.append(fixture(1000 + index * 2, f'Skip {case.name}', case))
            data.append(fixture(1001 + index * 2, f'Complete {case.name}', case))
        none_case = Case('disabled recurrence', 'none', '2026-03-07', '2026-03-08')
        paused_case = Case('paused recurrence', 'daily', '2026-03-07', '2026-03-08')
        data.extend([fixture(3000, 'No recurrence control', none_case),
                     fixture(3001, 'Paused recurrence control', paused_case, paused=True)])
        import_payload_replace(page, data)
        expect(page.locator('#taskModal')).to_be_hidden()
        expect(page.locator('.task-item')).to_have_count(len(data))
        legacy_ids = [1000 + index * 2 + offset for index, case in enumerate(CASES)
                      if case.repeat == 'weekly-days' and not case.weekdays for offset in (0, 1)]
        page.evaluate("""ids => new Promise((resolve, reject) => {
            const open = indexedDB.open('TaskTrackerDB', 2);
            open.onerror = () => reject(open.error);
            open.onsuccess = () => {
                const db = open.result;
                const tx = db.transaction('tasks', 'readwrite');
                const store = tx.objectStore('tasks');
                ids.forEach(id => {
                    const request = store.get(id);
                    request.onsuccess = () => store.put({...request.result, repeatWeekdays: []});
                });
                tx.oncomplete = () => {db.close(); resolve();};
                tx.onabort = () => reject(tx.error);
            };
        })""", legacy_ids)
        page.reload()
        wait_for_app_ready(page)
        legacy = [task for task in get_task_records(page) if task['id'] in legacy_ids]
        assert all(task['repeatWeekdays'] == [5] for task in legacy), 'Legacy task weekday depends on the device calendar'
        for index, case in enumerate(CASES):
            skip_id = 1000 + index * 2
            complete_id = skip_id + 1
            before = get_task_records(page)
            task_locator(page, f'Skip {case.name}').locator('[data-action="skip-repeat"]').click()
            expect(page.locator('#notificationText')).to_contain_text(re.compile('下一期|next occurrence', re.I))
            skipped = get_task_records(page)
            assert len(skipped) == len(before)
            updated = next(task for task in skipped if task['id'] == skip_id)
            assert_due(updated, case)
            assert not updated['completed']
            assert_others_unchanged(before, skipped, skip_id)
            task_locator(page, f'Complete {case.name}').locator('[data-action="toggle"]').click()
            expect(page.locator('#notificationText')).to_contain_text(re.compile('下一期|next occurrence', re.I))
            after = get_task_records(page)
            child = next(task for task in after if task.get('repeatCreatedFrom') == complete_id)
            completed = next(task for task in after if task['id'] == complete_id)
            assert len(after) == len(skipped) + 1 and completed['completed']
            assert completed['nextRepeatTaskId'] == child['id']
            assert child['repeatSourceId'] == complete_id and not child['completed']
            assert child['subtasks'][0]['completed'] is False
            assert child['project'] == completed['project'] and child['tags'] == completed['tags']
            assert_due(child, case)
            assert_others_unchanged(skipped, after, complete_id)
            observed.append({'case': case.name, 'dueAt': child['dueAt'], 'dueLocalDate': child['dueLocalDate'],
                             'dueLocalTime': child['dueLocalTime'], 'dueTimeZone': child['dueTimeZone']})
        for name, identity in (('No recurrence control', 3000), ('Paused recurrence control', 3001)):
            target = task_locator(page, name)
            expect(target.locator('[data-action="skip-repeat"]')).to_be_hidden()
            before = get_task_records(page)
            target.locator('[data-action="toggle"]').click()
            after = get_task_records(page)
            assert len(after) == len(before)
            assert next(task for task in after if task['id'] == identity)['completed']
            assert_others_unchanged(before, after, identity)
        before_reload = get_task_records(page)
        page.reload()
        wait_for_app_ready(page)
        assert get_task_records(page) == before_reload, 'Reload changed recurrence data'
        assert not errors, errors
        print(f'Recurrence host {host}: {len(CASES)} skip/completion cases plus none/paused controls passed', flush=True)
        return observed
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with local_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if args.browser == 'chromium' else {'headless': True}
        browser = getattr(playwright, args.browser).launch(**options)
        try:
            hosts = ['UTC', 'America/New_York', 'Pacific/Apia']
            baseline = run_host(browser, url, hosts[0])
            for host in hosts[1:]:
                assert baseline == run_host(browser, url, host), 'The device timezone changed next-occurrence records'
            report = {'browser': args.browser, 'browser_version': browser.version,
                      'hosts': hosts, 'cases_per_host': len(CASES),
                      'operations': ['skip', 'complete', 'none control', 'paused control', 'reload'],
                      'passed': True, 'cases': baseline}
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report), flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
