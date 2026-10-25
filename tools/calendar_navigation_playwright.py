#!/usr/bin/env python3
"""Exercise real calendar edits, cross-month search and keyboard return targets."""
from __future__ import annotations

import argparse
import json

from playwright.sync_api import expect, sync_playwright

from calendar_performance_playwright import open_day, seed
from performance_playwright import read_workspace
from smoke_playwright import (
    browser_launch_options, calendar_month_title, clear_app_data, get_task_records,
    local_server, select_view, wait_for_app_ready,
)


DAY = '2039-01-01'
FUTURE_NAME = 'Future March target'
UNDATED_NAME = 'Unscheduled reference target'


def verify_edit_return_focus(page, url):
    clear_app_data(page, url)
    seed(page, 4)
    before = {task['id']: task for task in get_task_records(page)}
    select_view(page, 'calendar')
    open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(4)
    entry = page.locator('.calendar-detail-task').first
    edited_id = int(entry.get_attribute('data-calendar-task-id'))
    entry.click()
    expect(page.locator('#taskName')).to_have_value(before[edited_id]['name'])
    page.locator('#noDeadline').check()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('.calendar-detail-task')).to_have_count(3)
    expect(page.locator(f'[data-calendar-detail-date="{DAY}"]')).to_have_count(0)
    after = {task['id']: task for task in get_task_records(page)}
    assert set(after) == set(before), 'Changing one task deadline added or removed task records'
    assert after[edited_id]['dueAt'] is None and after[edited_id]['dueLocalDate'] is None
    assert {key:value for key,value in after.items() if key != edited_id} == {
        key:value for key,value in before.items() if key != edited_id
    }, 'Changing a calendar task deadline changed an unrelated task'
    page.locator('.calendar-detail-close').click()
    expect(page.locator('.calendar-day-detail')).to_have_count(0)
    expect(page.locator(f'[data-calendar-add-date="{DAY}"]')).to_be_focused()
    assert {task['id']:task for task in get_task_records(page)} == after, 'Closing date details wrote task data'
    print('Calendar navigation passed: after a real edit removes the day More button, closing details focuses that date button', flush=True)


def seed_search_dates(page):
    seed(page, 4)
    page.evaluate("""({futureName, undatedName}) => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('tasks', 'readwrite');
            const store = tx.objectStore('tasks');
            const future = store.get(200003);
            future.onsuccess = () => store.put({...future.result, name:futureName,
                dueDate:'2039-03-15T12:00:00.000Z', dueAt:'2039-03-15T12:00:00.000Z',
                dueLocalDate:'2039-03-15', dueLocalTime:'12:00', dueTimeZone:'UTC'});
            const undated = store.get(100003);
            undated.onsuccess = () => store.put({...undated.result, name:undatedName});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", {'futureName':FUTURE_NAME, 'undatedName':UNDATED_NAME})
    page.reload()
    wait_for_app_ready(page)


def verify_cross_month_search(page, url):
    clear_app_data(page, url)
    seed_search_dates(page)
    before = read_workspace(page)
    select_view(page, 'calendar')
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 0))
    page.locator('#searchInput').fill(FUTURE_NAME)
    expect(page.locator('.calendar-task')).to_have_count(1)
    expect(page.locator('.calendar-task')).to_have_text(FUTURE_NAME)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 2))
    expect(page.locator('.date-view-undated .task-item')).to_have_count(0)

    page.locator('[data-calendar-action="next"]').click()
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    expect(page.locator('.calendar-task')).to_have_count(0)
    page.locator('[data-calendar-action="prev"]').click()
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 2))
    expect(page.locator('.calendar-task')).to_have_text(FUTURE_NAME)
    page.locator('#searchInput').fill('calendar-scale')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(4)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 2))
    expect(page.locator('.calendar-task')).to_have_text(FUTURE_NAME)
    page.locator('#searchInput').fill(FUTURE_NAME)
    expect(page.locator('.date-view-undated .task-item')).to_have_count(0)
    page.locator('[data-calendar-action="next"]').click()
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    page.locator('#searchInput').fill('No matching item before returning to the same query')
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    page.locator('#searchInput').fill(FUTURE_NAME)
    expect(page.locator('.calendar-task')).to_have_count(1)
    expect(page.locator('.calendar-task')).to_have_text(FUTURE_NAME)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 2))
    page.locator('[data-calendar-action="next"]').click()
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    page.locator('#searchInput').fill('')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(4)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    print('Calendar navigation passed: unique cross-month search reveals its task; manual month navigation and clearing search retain the chosen month', flush=True)
    print('Calendar navigation passed: a query with a visible date retains its month, and returning through no results restarts the same-query search', flush=True)

    page.locator('#searchInput').fill('No such synthetic calendar item')
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    expect(page.locator('.calendar-view')).to_have_count(0)
    page.locator('#searchInput').fill('')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(4)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    page.locator('#searchInput').fill(UNDATED_NAME)
    expect(page.locator('.date-view-undated .task-item')).to_have_count(1)
    expect(page.locator('.date-view-undated .task-name')).to_have_text(UNDATED_NAME)
    expect(page.locator('.calendar-task')).to_have_count(0)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    page.locator('#searchInput').fill('')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(4)
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, 2039, 3))
    assert read_workspace(page) == before, 'Calendar search or month navigation wrote task/config records'
    print('Calendar navigation passed: absent and undated-only searches preserve the month and all IndexedDB records', flush=True)


def diagnostics(page):
    return page.evaluate("""() => ({month:document.querySelector('.calendar-title')?.textContent,
        previewTasks:document.querySelectorAll('.calendar-task').length,
        detailTasks:document.querySelectorAll('.calendar-detail-task').length,
        taskCards:document.querySelectorAll('.task-item').length,
        activeTag:document.activeElement?.tagName, activeId:document.activeElement?.id,
        activeDate:document.activeElement?.dataset.calendarAddDate})""")


def run(engine, case):
    expect.set_options(timeout=10000)
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(**options)
        context = browser.new_context(locale='en-US', timezone_id='UTC', reduced_motion='reduce')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            if case in ('all', 'focus'):
                verify_edit_return_focus(page, url)
            if case in ('all', 'search'):
                verify_cross_month_search(page, url)
            assert not errors, errors
            print(json.dumps({'browser_engine':engine, 'browser':browser.version,
                              'case':case, 'passed':True}), flush=True)
        except Exception:
            print('Calendar navigation failure: ' + json.dumps({'state':diagnostics(page), 'pageerrors':errors}, ensure_ascii=False), flush=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'focus', 'search'), default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
