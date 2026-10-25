#!/usr/bin/env python3
"""Keep large calendar sections bounded without losing full-workspace tasks."""
from __future__ import annotations

from smoke_playwright import enter_batch_mode

import argparse
import json
from pathlib import Path
import re
import time

from playwright.sync_api import expect, sync_playwright

from performance_playwright import read_workspace
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, local_server, select_filter,
    select_project, select_sort, select_view, wait_for_app_ready,
)


def ids(page, selector, attribute):
    return set(page.locator(selector).evaluate_all(
        '(nodes, attribute) => nodes.map(node => node.getAttribute(attribute))', attribute))


def seed(page, per_section):
    add_task(page, 'Calendar scale seed', no_deadline=True)
    page.evaluate("""perSection => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const store = tx.objectStore('tasks');
            const all = store.getAll();
            all.onsuccess = () => {
                const template = all.result[0];
                store.clear();
                for (let i = 0; i < perSection; i++) {
                    for (const dated of [false, true]) {
                        const key = dated ? '2039-01-01' : null;
                        const instant = key ? key + 'T12:00:00.000Z' : null;
                        store.put({...template, id: (dated ? 200000 : 100000) + i,
                            name: `Calendar ${dated ? 'deadline' : 'inbox'} ${String(i).padStart(5, '0')} 中文`,
                            description: `Synthetic calendar entry ${i}`, project: i % 2 ? 'Odd' : 'Even',
                            tags: ['calendar-scale'], order:i * 1000,
                            dueDate:instant, dueAt:instant, dueLocalDate:key,
                            dueLocalTime:key ? '12:00' : null, dueTimeZone:key ? 'UTC' : null,
                            reminderOffset:-1, reminderRepeat:-1});
                    }
                }
                tx.objectStore('config').put({key:'recoveryHistory', value:[]});
            };
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", per_section)
    page.reload()
    wait_for_app_ready(page)


def assert_summary(page, section, shown, total):
    summary = page.locator(section + ' .task-pagination p')
    expect(summary).to_contain_text(str(shown))
    expect(summary).to_contain_text(str(total))


def open_day(page):
    page.locator('[data-calendar-detail-date="2039-01-01"]').click()
    expect(page.locator('.calendar-day-detail')).to_be_visible()
    expect(page.locator('.calendar-detail-close')).to_be_focused()


def exercise_batch_calendar(page, per_section, metrics, sort_mode):
    select_sort(page, sort_mode)
    enter_batch_mode(page)
    select_view(page, 'calendar')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    if not page.locator('.calendar-day-detail').count():
        open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(100)
    expect(page.locator('.calendar-day-detail .task-select-checkbox')).to_have_count(0)
    assert_summary(page, '.date-view-undated', 100, per_section)
    assert_summary(page, '.calendar-day-detail', 100, per_section)
    expect(page.locator('.calendar-detail-title')).to_contain_text(str(per_section))
    metrics[f'batch_{sort_mode}_undated_nodes'] = page.locator('.date-view-undated .task-item').count()
    metrics[f'batch_{sort_mode}_detail_nodes'] = page.locator('.calendar-detail-task').count()
    page.locator('#batchSelectVisibleBtn').click()
    total_matches = per_section * 2
    count_pattern = re.compile(rf'(?<!\d){total_matches}(?!\d)')
    expect(page.locator('#batchSelectionSummary')).to_contain_text(count_pattern)
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(100)

    previous = ids(page, '.date-view-undated .task-item', 'data-task-id')
    page.locator('[data-calendar-action="undated-more"]').click()
    expect(page.locator('.date-view-undated .task-item')).to_have_count(200)
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(200)
    focus = page.evaluate("""() => ({id:document.activeElement.closest('.task-item')?.dataset.taskId,
        checkbox:document.activeElement.matches('.task-select-checkbox')})""")
    assert focus['checkbox'] and focus['id'] not in previous, 'Batch calendar Show more did not focus a newly displayed checkbox'
    expect(page.locator('#batchSelectionSummary')).to_contain_text(count_pattern)
    previous = ids(page, '.calendar-detail-task', 'data-calendar-task-id')
    page.locator('[data-calendar-action="detail-more"]').click()
    expect(page.locator('.calendar-detail-task')).to_have_count(200)
    focus = page.evaluate('document.activeElement.dataset.calendarTaskId')
    assert focus and focus not in previous, 'Batch day-detail paging did not focus a new task button'
    assert_summary(page, '.date-view-undated', 200, per_section)
    assert_summary(page, '.calendar-day-detail', 200, per_section)

    select_sort(page, 'smart' if sort_mode == 'manual' else 'manual')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    expect(page.locator('.calendar-detail-task')).to_have_count(100)
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(100)
    expect(page.locator('#batchSelectionSummary')).to_contain_text(count_pattern)
    select_sort(page, sort_mode)
    page.locator('#exitBatchModeBtn').click()
    expect(page.locator('.task-select-checkbox')).to_have_count(0)
    expected = per_section if sort_mode == 'manual' else 100
    expect(page.locator('.date-view-undated .task-item')).to_have_count(expected)
    expect(page.locator('.calendar-detail-task')).to_have_count(expected)
    if sort_mode == 'manual':
        expect(page.locator('[data-calendar-action$="-more"]')).to_have_count(0)
    print(f'Calendar batch {sort_mode} passed: bounded independent pages, full matching selection/counts, checkbox/button focus and exit behavior', flush=True)


def exercise_calendar(page, per_section, metrics):
    before = read_workspace(page)
    started = time.perf_counter()
    select_view(page, 'calendar')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    metrics['calendar_initial_ms'] = round((time.perf_counter() - started) * 1000, 1)
    metrics['initial_undated_nodes'] = page.locator('.date-view-undated .task-item').count()
    expect(page.locator('.calendar-task')).to_have_count(3)
    day_more = page.locator('[data-calendar-detail-date="2039-01-01"]')
    expect(day_more).to_have_attribute('aria-label', re.compile(str(per_section)))
    expect(day_more).to_have_attribute('aria-label', re.compile(re.escape(day_more.inner_text())))
    assert_summary(page, '.date-view-undated', 100, per_section)
    expect(page.locator('#taskPagination')).to_be_hidden()

    previous = ids(page, '.date-view-undated .task-item', 'data-task-id')
    page.locator('[data-calendar-action="undated-more"]').click()
    expect(page.locator('.date-view-undated .task-item')).to_have_count(200)
    focused = page.evaluate('document.activeElement.closest(".task-item")?.dataset.taskId')
    assert focused and focused not in previous, 'Undated Show more did not focus a new task'
    assert_summary(page, '.date-view-undated', 200, per_section)

    open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(100)
    expect(page.locator('.calendar-detail-title')).to_contain_text(str(per_section))
    assert_summary(page, '.calendar-day-detail', 100, per_section)
    previous = ids(page, '.calendar-detail-task', 'data-calendar-task-id')
    page.locator('[data-calendar-action="detail-more"]').click()
    expect(page.locator('.calendar-detail-task')).to_have_count(200)
    focused = page.evaluate('document.activeElement.dataset.calendarTaskId')
    assert focused and focused not in previous, 'Day-detail Show more did not focus a new task'
    expect(page.locator('.date-view-undated .task-item')).to_have_count(200)
    assert_summary(page, '.calendar-day-detail', 200, per_section)
    print('Calendar passed: independent bounded sections, full counts and focus on newly loaded tasks', flush=True)

    # Finish both lists, including the incomplete last page, so the far end is reachable.
    for action, selector in [('detail-more', '.calendar-detail-task'),
                             ('undated-more', '.date-view-undated .task-item')]:
        while page.locator(f'[data-calendar-action="{action}"]').count():
            count = page.locator(selector).count()
            page.locator(f'[data-calendar-action="{action}"]').click()
            expect(page.locator(selector)).to_have_count(min(count + 100, per_section))
        expect(page.locator(selector)).to_have_count(per_section)
    last_name = f'Calendar deadline {per_section - 1:05d} 中文'
    page.locator('.calendar-detail-task').filter(has_text=last_name).click()
    expect(page.locator('#taskName')).to_have_value(last_name)
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('.calendar-detail-close').click()
    expect(page.locator('[data-calendar-detail-date="2039-01-01"]')).to_be_focused()
    open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(100)
    print('Calendar passed: final partial pages reach editable tasks, and reopening a date resets its page', flush=True)

    for kind in ('inbox', 'deadline'):
        target = f'Calendar {kind} {per_section - 1:05d} 中文'
        page.locator('#searchInput').fill(target)
        if kind == 'inbox':
            expect(page.locator('.date-view-undated .task-item')).to_have_count(1)
            expect(page.locator('.date-view-undated .task-name')).to_have_text(target)
            expect(page.locator('.calendar-task')).to_have_count(0)
        else:
            expect(page.locator('.calendar-task')).to_have_count(1)
            expect(page.locator('.calendar-task')).to_have_text(target)
            expect(page.locator('.date-view-undated .task-item')).to_have_count(0)
        expect(page.locator('[data-calendar-action$="-more"]')).to_have_count(0)
        page.locator('#searchInput').fill('')
        expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    print('Calendar passed: far-end dated and undated search covers all tasks and resets display limits', flush=True)

    open_day(page)
    page.locator('[data-calendar-action="detail-more"]').click()
    page.locator('[data-calendar-action="undated-more"]').click()
    select_view(page, 'list')
    select_view(page, 'calendar')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    # An open date may be retained across view changes, but its expanded page must not be.
    if page.locator('.calendar-day-detail').count():
        expect(page.locator('.calendar-detail-task')).to_have_count(100)
        page.locator('.calendar-detail-close').click()
    open_day(page)
    page.locator('[data-calendar-action="detail-more"]').click()
    page.locator('[data-calendar-action="undated-more"]').click()
    page.locator('[data-calendar-action="next"]').click()
    expect(page.locator('.calendar-day-detail')).to_have_count(0)
    expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    page.locator('[data-calendar-action="prev"]').click()
    open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(100)

    select_project(page, 'Even')
    even_count = (per_section + 1) // 2
    expect(page.locator('.date-view-undated .task-item')).to_have_count(min(100, even_count))
    expect(page.locator('.calendar-detail-task')).to_have_count(min(100, even_count))
    expect(page.locator('.calendar-detail-title')).to_contain_text(str(even_count))
    select_filter(page, 'no-deadline')
    expect(page.locator('.calendar-day-detail')).to_have_count(0)
    expect(page.locator('.date-view-undated .task-item')).to_have_count(min(100, even_count))
    select_filter(page, 'all')
    select_project(page, 'all')
    print('Calendar passed: view/month/project/filter navigation resets bounds without stale details', flush=True)

    select_sort(page, 'manual')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(per_section)
    open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(per_section)
    expect(page.locator('[data-calendar-action$="-more"]')).to_have_count(0)
    exercise_batch_calendar(page, per_section, metrics, 'manual')
    exercise_batch_calendar(page, per_section, metrics, 'smart')
    assert read_workspace(page) == before, 'Calendar rendering, pagination, search or navigation mutated task/config records'
    print('Calendar passed: manual-order behavior is retained and all rendering operations leave IndexedDB unchanged', flush=True)


def exercise_scale_boundaries(page, per_section, metrics):
    """Exercise a much larger workspace without deliberately mounting every page."""
    before = read_workspace(page)
    started = time.perf_counter()
    select_view(page, 'calendar')
    expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    metrics['calendar_initial_ms'] = round((time.perf_counter() - started) * 1000, 1)
    metrics['initial_undated_nodes'] = page.locator('.date-view-undated .task-item').count()
    expect(page.locator('.calendar-task')).to_have_count(3)
    assert_summary(page, '.date-view-undated', 100, per_section)
    started = time.perf_counter()
    open_day(page)
    expect(page.locator('.calendar-detail-task')).to_have_count(100)
    metrics['day_detail_initial_ms'] = round((time.perf_counter() - started) * 1000, 1)
    metrics['initial_day_detail_nodes'] = page.locator('.calendar-detail-task').count()
    expect(page.locator('.calendar-detail-title')).to_contain_text(str(per_section))
    assert_summary(page, '.calendar-day-detail', 100, per_section)
    previous = ids(page, '.calendar-detail-task', 'data-calendar-task-id')
    page.locator('[data-calendar-action="detail-more"]').click()
    expect(page.locator('.calendar-detail-task')).to_have_count(200)
    focused = page.evaluate('document.activeElement.dataset.calendarTaskId')
    assert focused and focused not in previous
    previous = ids(page, '.date-view-undated .task-item', 'data-task-id')
    page.locator('[data-calendar-action="undated-more"]').click()
    expect(page.locator('.date-view-undated .task-item')).to_have_count(200)
    focused = page.evaluate('document.activeElement.closest(".task-item")?.dataset.taskId')
    assert focused and focused not in previous
    for kind in ('inbox', 'deadline'):
        target = f'Calendar {kind} {per_section - 1:05d} 中文'
        started = time.perf_counter()
        page.locator('#searchInput').fill(target)
        if kind == 'inbox':
            expect(page.locator('.date-view-undated .task-item')).to_have_count(1)
            expect(page.locator('.date-view-undated .task-name')).to_have_text(target)
            expect(page.locator('.calendar-task')).to_have_count(0)
        else:
            expect(page.locator('.calendar-task')).to_have_count(1)
            expect(page.locator('.calendar-task')).to_have_text(target)
            expect(page.locator('.date-view-undated .task-item')).to_have_count(0)
        metrics[kind + '_tail_search_ms'] = round((time.perf_counter() - started) * 1000, 1)
        page.locator('#searchInput').fill('')
        expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
    exercise_batch_calendar(page, per_section, metrics, 'smart')
    assert read_workspace(page) == before, 'Large calendar rendering or search modified task/config records'
    print('Calendar scale passed: bounded initial sections, full counts, first paging/focus, exclusive tail search and unchanged IndexedDB', flush=True)


def run(engine, per_section, output, scale_only=False):
    expect.set_options(timeout=20000)
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(**options)
        context = browser.new_context(locale='en-US', timezone_id='UTC', reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            seed(page, per_section)
            metrics = {'browser_engine':engine, 'browser':browser.version,
                       'dated_tasks':per_section, 'undated_tasks':per_section,
                       'coverage':'scale boundaries only' if scale_only else 'full pagination and navigation'}
            if scale_only:
                exercise_scale_boundaries(page, per_section, metrics)
            else:
                exercise_calendar(page, per_section, metrics)
            assert not errors, errors
            metrics['passed'] = True
            if output:
                Path(output).write_text(json.dumps(metrics, indent=2) + '\n')
            print(json.dumps(metrics), flush=True)
        except Exception:
            print(json.dumps({'page_errors':errors,
                              'remaining_undated_nodes':page.locator('.date-view-undated .task-item').count(),
                              'remaining_detail_nodes':page.locator('.calendar-detail-task').count()}, ensure_ascii=False), flush=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--per-section', type=int, default=251)
    parser.add_argument('--output')
    parser.add_argument('--scale-only', action='store_true',
                        help='Measure large initial sections and tail search; default suite covers all pages and manual ordering')
    args = parser.parse_args()
    if args.per_section <= 200:
        parser.error('--per-section must exceed 200 to cover full and partial pages')
    run(args.browser, args.per_section, args.output, args.scale_only)
