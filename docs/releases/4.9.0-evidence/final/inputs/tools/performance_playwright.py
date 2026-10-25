#!/usr/bin/env python3
"""Measure a synthetic large workspace and verify that search never loses tasks."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import time

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import add_task, browser_launch_options, clear_app_data, local_server, select_sort, select_view, task_locator, wait_for_app_ready



def read_workspace(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => { db.close(); resolve({tasks:tasks.result, config:config.result}); };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def exercise_timeline(page, size, metrics):
    page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('tasks', 'readwrite');
            const store = tx.objectStore('tasks');
            const all = store.getAll();
            all.onsuccess = () => all.result.forEach((task, index) => {
                const key = ['2039-01-03', '2039-01-01', '2039-01-02', null][index % 4];
                const instant = key ? `${key}T12:00:00.000Z` : null;
                store.put({...task, dueDate:instant, dueAt:instant, dueLocalDate:key,
                    dueLocalTime:key ? '12:00' : null, dueTimeZone:key ? 'UTC' : null});
            });
            tx.oncomplete = () => { db.close(); resolve(); };
            tx.onabort = () => reject(tx.error);
        };
    })""")
    page.reload()
    wait_for_app_ready(page)
    before = read_workspace(page)
    by_id = {str(task['id']): task for task in before['tasks']}
    group_counts = {}
    for task in before['tasks']:
        key = task['dueLocalDate'] or '__none__'
        group_counts[key] = group_counts.get(key, 0) + 1

    def check_groups():
        keys = []
        for group in page.locator('.timeline-group').all():
            ids = group.locator('.task-item').evaluate_all('items => items.map(item => item.dataset.taskId)')
            assert ids, 'Timeline rendered an empty date group'
            dates = {by_id[task_id]['dueLocalDate'] or '__none__' for task_id in ids}
            assert len(dates) == 1, 'Timeline mixed distinct dates into a group'
            key = dates.pop()
            keys.append(key)
            count = int(re.search(r'\d+', group.locator('.timeline-count').inner_text()).group())
            assert count == group_counts[key], 'Date heading omitted tasks beyond the rendered page'
        assert keys == sorted(keys, key=lambda key: (key == '__none__', key)), 'Timeline dates are out of chronological order'

    if size > 100:
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.task-item')).to_have_count(min(200, size), timeout=20000)
    start = time.perf_counter()
    select_view(page, 'timeline')
    expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    metrics['timeline_load_ms'] = round((time.perf_counter() - start) * 1000, 1)
    metrics['timeline_initial_nodes'] = page.locator('.timeline-view .task-item').count()
    check_groups()
    if size > 100:
        expect(page.locator('#taskPaginationSummary')).to_contain_text(f'100')
        expect(page.locator('#taskPaginationSummary')).to_contain_text(str(size))
        previous_ids = set(page.locator('.timeline-view .task-item').evaluate_all('items => items.map(item => item.dataset.taskId)'))
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.timeline-view .task-item')).to_have_count(min(200, size), timeout=20000)
        focused_id = page.evaluate('document.activeElement.closest(".task-item")?.dataset.taskId')
        assert focused_id and focused_id not in previous_ids, 'Timeline Show more did not focus newly displayed content'
        check_groups()
    if size > 200:
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.timeline-view .task-item')).to_have_count(min(300, size), timeout=20000)
        check_groups()
    last = max(before['tasks'], key=lambda task: (task['dueLocalDate'] is None, task['dueLocalDate'] or '', task['id']))
    start = time.perf_counter()
    page.locator('#searchInput').fill(last['name'])
    expect(task_locator(page, last['name'])).to_have_count(1, timeout=20000)
    expect(page.locator('.timeline-view .task-item')).to_have_count(1, timeout=20000)
    metrics['timeline_search_ms'] = round((time.perf_counter() - start) * 1000, 1)
    page.locator('#searchInput').fill('')
    expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    if size > 100:
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.timeline-view .task-item')).to_have_count(min(200, size), timeout=20000)
    select_view(page, 'stats')
    select_view(page, 'timeline')
    expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    if size > 100:
        page.locator('#loadMoreTasksBtn').click()
    select_view(page, 'list')
    expect(page.locator('.task-item')).to_have_count(min(100, size), timeout=20000)
    if size > 100:
        page.locator('#loadMoreTasksBtn').click()
    select_view(page, 'timeline')
    expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    if size <= 1000:
        select_sort(page, 'manual')
        expect(page.locator('.timeline-view .task-item')).to_have_count(size, timeout=20000)
        expect(page.locator('#taskPagination')).to_be_hidden()
        select_sort(page, 'smart')
        expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    page.locator('#batchModeBtn').click()
    select_view(page, 'timeline')
    expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    metrics['batch_timeline_initial_nodes'] = page.locator('.timeline-view .task-item').count()
    page.locator('#batchSelectVisibleBtn').click()
    expect(page.locator('#batchSelectionSummary')).to_contain_text(re.compile(rf'(?<!\d){size}(?!\d)'))
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(min(100, size))
    check_groups()
    if size > 100:
        expect(page.locator('#taskPaginationSummary')).to_contain_text(re.compile(rf'(?<!\d){size}(?!\d)'))
        previous_ids = set(page.locator('.timeline-view .task-item').evaluate_all('items => items.map(item => item.dataset.taskId)'))
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.timeline-view .task-item')).to_have_count(min(200, size))
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(min(200, size))
        focus = page.evaluate("""() => ({id:document.activeElement.closest('.task-item')?.dataset.taskId,
            checkbox:document.activeElement.matches('.task-select-checkbox')})""")
        assert focus['checkbox'] and focus['id'] not in previous_ids, 'Timeline batch Show more did not focus a new selected checkbox'
        expect(page.locator('#batchSelectionSummary')).to_contain_text(re.compile(rf'(?<!\d){size}(?!\d)'))
        check_groups()
    if size <= 1000:
        select_sort(page, 'manual')
        expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size))
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(min(100, size))
        expect(page.locator('#batchSelectionSummary')).to_contain_text(re.compile(rf'(?<!\d){size}(?!\d)'))
        if size > 100:
            expect(page.locator('#taskPagination')).to_be_visible()
        check_groups()
        page.locator('#exitBatchModeBtn').click()
        expect(page.locator('.timeline-view .task-item')).to_have_count(size)
        expect(page.locator('#taskPagination')).to_be_hidden()
        select_sort(page, 'smart')
    else:
        page.locator('#exitBatchModeBtn').click()
    expect(page.locator('.timeline-view .task-item')).to_have_count(min(100, size), timeout=20000)
    expect(page.locator('.task-select-checkbox')).to_have_count(0)
    assert read_workspace(page) == before, 'Timeline pagination/search/view switching modified stored tasks or settings'
    print('Timeline passed: bounded ordinary/batch cards, full date and selection counts, checkbox paging focus, chronology, far-end search, manual restoration and read-only rendering', flush=True)


def run(size: int, output: str | None, bounded: bool) -> None:
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        page = browser.new_page()
        clear_app_data(page, url)
        add_task(page, 'Benchmark seed', no_deadline=True)
        page.evaluate("""size => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(['tasks', 'config'], 'readwrite');
                const store = tx.objectStore('tasks');
                const seed = store.getAll();
                seed.onsuccess = () => {
                    const template = seed.result[0];
                    store.clear();
                    for (let i = 0; i < size; i++) store.put({...template,
                        id: 100000 + i, name: `Benchmark task ${String(i).padStart(5, '0')}`,
                        description: `Synthetic workspace entry ${i}`, project: `Project ${i % 10}`,
                        order: i * 1000, tags: ['benchmark', `tag${i % 20}`]});
                    tx.objectStore('config').put({key: 'recoveryHistory', value: []});
                };
                tx.oncomplete = () => { db.close(); resolve(); };
                tx.onabort = () => reject(tx.error);
            };
            request.onerror = () => reject(request.error);
        })""", size)
        start = time.perf_counter()
        page.reload()
        wait_for_app_ready(page)
        expect(page.locator('.task-item').first).to_be_visible(timeout=20000)
        load_ms = (time.perf_counter() - start) * 1000
        initial_nodes = page.locator('.task-item').count()
        if bounded and initial_nodes > 100:
            raise AssertionError(f'Initial DOM contains {initial_nodes} task cards, expected at most 100')
        start = time.perf_counter()
        target = f'Benchmark task {size - 1:05d}'
        page.locator('#searchInput').fill(target)
        expect(task_locator(page, target)).to_have_count(1, timeout=10000)
        expect(page.locator('.task-item')).to_have_count(1)
        search_ms = (time.perf_counter() - start) * 1000
        page.locator('#searchInput').fill('')
        expect(page.locator('.task-item')).to_have_count(min(100, size) if bounded else size, timeout=20000)
        if bounded and size > 100:
            previous_ids = set(page.locator('.task-item').evaluate_all('items => items.map(item => item.dataset.taskId)'))
            page.locator('#loadMoreTasksBtn').click()
            expect(page.locator('.task-item')).to_have_count(min(200, size))
            focused_id = page.evaluate('document.activeElement.closest(".task-item")?.dataset.taskId')
            if not focused_id or focused_id in previous_ids:
                raise AssertionError('Loading more tasks did not focus newly displayed content')
        metrics = {'tasks': size, 'browser': browser.version, 'initial_task_nodes': initial_nodes,
                   'load_ms': round(load_ms, 1), 'search_ms': round(search_ms, 1)}
        if load_ms > 15000 or search_ms > 5000:
            raise AssertionError(f'Generous regression budget exceeded: {metrics}')
        if bounded:
            exercise_timeline(page, size, metrics)
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(metrics, indent=2) + '\n')
        print(json.dumps(metrics))
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=1000)
    parser.add_argument('--output')
    parser.add_argument('--baseline', action='store_true', help='Measure before bounded rendering is enabled')
    args = parser.parse_args()
    if args.size < 1:
        parser.error('--size must be positive')
    run(args.size, args.output, not args.baseline)
