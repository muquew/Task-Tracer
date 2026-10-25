#!/usr/bin/env python3
"""Check batch scope and never let Undo include another window's later writes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import (add_task, browser_launch_options, clear_app_data,
                              get_task_records, local_server, select_filter,
                              select_project, select_sort, task_locator,
                              wait_for_app_ready)


def by_name(page):
    return {task['name']: task for task in get_task_records(page)}


def assert_selected(page, count):
    language = page.locator('html').get_attribute('lang') or 'en'
    translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
    expect(page.locator('#batchSelectionSummary')).to_have_text(translations['batch']['selected'].format(count=count))


def show_more_selected(page, count, total):
    previous = set(page.locator('.task-item').evaluate_all('items => items.map(item => item.dataset.taskId)'))
    page.locator('#loadMoreTasksBtn').click()
    expect(page.locator('.task-item')).to_have_count(count)
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(count)
    assert_selected(page, total)
    focus = page.evaluate("""() => ({id:document.activeElement.closest('.task-item')?.dataset.taskId,
        checkbox:document.activeElement.matches('.task-select-checkbox')})""")
    assert focus['checkbox'] and focus['id'] not in previous, 'Batch Show more did not focus a newly displayed task checkbox'


def transaction_state(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const revision = tx.objectStore('config').get('taskRevision');
            const history = tx.objectStore('config').get('recoveryHistory');
            tx.oncomplete = () => {
                db.close();
                resolve({tasks:tasks.result, revision:revision.result, history:history.result});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def install_completion_hold(page):
    page.evaluate("""() => {
        const completion = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, 'oncomplete');
        Object.defineProperty(IDBTransaction.prototype, 'oncomplete', {
            configurable: true,
            get: completion.get,
            set(handler) {
                const tx = this;
                const hasTasks = Array.from(tx.objectStoreNames).includes('tasks');
                const holdWrite = hasTasks && tx.mode === 'readwrite' && window.holdNextTaskWrite;
                const holdRead = hasTasks && tx.mode === 'readonly' && window.holdNextTaskRead;
                if (holdWrite) window.holdNextTaskWrite = false;
                if (holdRead) window.holdNextTaskRead = false;
                completion.set.call(tx, function(event) {
                    if (holdWrite) {
                        window.releaseCommittedTaskWrite = () => handler.call(tx, event);
                        window.taskWriteCommitted = true;
                    } else if (holdRead) {
                        window.releaseCompletedTaskRead = () => handler.call(tx, event);
                        window.taskReadCompleted = true;
                    } else handler.call(tx, event);
                });
            }
        });
    }""")


def edit_remote_task(context, url):
    second = context.new_page()
    second.goto(url)
    wait_for_app_ready(second)
    task_locator(second, 'Unrelated task B').locator('[data-action="edit"]').click()
    second.locator('#taskDesc').fill('A remote edit committed after the original transaction')
    second.locator('#submitBtn').click()
    expect(second.locator('#taskModal')).to_be_hidden()
    return by_name(second)


def check_undo_after_remote_commit(browser, url, action):
    context = browser.new_context(reduced_motion='reduce')
    try:
        first = context.new_page()
        errors = []
        first.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(first, url)
        add_task(first, 'Batch task A', no_deadline=True)
        add_task(first, 'Unrelated task B', no_deadline=True)
        baseline = by_name(first)
        install_completion_hold(first)
        if action == 'batch':
            first.locator('#batchModeBtn').click()
            task_locator(first, 'Batch task A').locator('.task-select-checkbox').check()
        first.evaluate('window.holdNextTaskWrite = true')
        if action == 'batch':
            first.locator('#batchFocusBtn').click()
        else:
            task_locator(first, 'Batch task A').locator('[data-action="toggle"]').click()
        first.wait_for_function('window.taskWriteCommitted === true')
        committed = by_name(first)
        field = 'focusDate' if action == 'batch' else 'completed'
        assert committed['Batch task A'][field], 'The original task transaction has not committed'
        assert committed['Unrelated task B'] == baseline['Unrelated task B']
        remote = edit_remote_task(context, url)
        assert remote['Batch task A'] == committed['Batch task A']
        expected_b = remote['Unrelated task B']
        assert expected_b['description'] != baseline['Unrelated task B']['description']
        expected_transaction = transaction_state(first)
        first.evaluate('window.releaseCommittedTaskWrite()')
        expect(task_locator(first, 'Unrelated task B').locator('.task-desc')).to_contain_text(expected_b['description'])
        if action == 'batch':
            # A refresh already incorporated the newer write. Its revision must
            # never be adopted as if it were the batch transaction's own result.
            expect(first.locator('#undoBtn')).to_be_disabled()
        else:
            # A caller registering before refresh may still offer Undo, but its
            # actual attempt must refuse a later transaction's data and revision.
            expect(first.locator('#undoBtn')).to_be_enabled()
            first.locator('#undoBtn').click()
            language = first.locator('html').get_attribute('lang') or 'en'
            translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
            expect(first.locator('#notificationText')).to_have_text(translations['storage']['conflict'])
        after = by_name(first)
        assert after['Unrelated task B'] == expected_b, json.dumps({
            'problem': 'Undo reverted an unrelated later remote edit',
            'expected': expected_b, 'actual': after['Unrelated task B']}, ensure_ascii=False)
        assert after['Batch task A'] == committed['Batch task A'], 'A refused Undo changed the selected task'
        assert set(after) == set(baseline)
        assert transaction_state(first) == expected_transaction, 'Refused Undo changed tasks, revision or recovery history'

        # The refusal must not break a subsequent fresh, explicitly reviewed
        # action and its normal Undo, which may affect only the selected task.
        if action == 'batch':
            task_locator(first, 'Batch task A').locator('.task-select-checkbox').check()
            first.locator('#batchCompleteBtn').click()
        else:
            select_filter(first, 'all')
            task_locator(first, 'Batch task A').locator('[data-action="toggle"]').click()
        expect(first.locator('#undoBtn')).to_be_enabled()
        first.locator('#undoBtn').click()
        expect(first.locator('#undoBtn')).to_be_disabled()
        first.wait_for_function("""() => /Undone|已撤销/.test(document.querySelector('#notificationText').textContent)""")
        assert by_name(first) == remote, 'Fresh Undo did not restore exactly its own task operation'
        assert not errors, errors
        print(f'Undo {action} passed: refuses post-commit remote changes without writes; a fresh action still undoes only itself', flush=True)
    finally:
        context.close()


def check_delayed_after_snapshot(browser, url):
    context = browser.new_context(reduced_motion='reduce')
    try:
        first = context.new_page()
        errors = []
        first.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(first, url)
        add_task(first, 'Batch task A', no_deadline=True)
        add_task(first, 'Unrelated task B', no_deadline=True)
        install_completion_hold(first)
        first.evaluate('window.holdNextTaskWrite = true')
        task_locator(first, 'Batch task A').locator('[data-action="toggle"]').click()
        first.wait_for_function('window.taskWriteCommitted === true')
        first.evaluate("""() => {
            window.holdNextTaskRead = true;
            window.releaseCommittedTaskWrite();
        }""")
        first.wait_for_function('window.taskReadCompleted === true')
        expect(first.locator('#undoBtn')).to_be_enabled()
        remote = edit_remote_task(context, url)
        expected = transaction_state(first)
        first.locator('#undoBtn').click()
        expect(first.locator('#undoBtn')).to_be_disabled()
        assert transaction_state(first) == expected, 'Undo wrote before its real after-snapshot completed'
        first.evaluate('window.releaseCompletedTaskRead()')
        language = first.locator('html').get_attribute('lang') or 'en'
        translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
        expect(first.locator('#notificationText')).to_have_text(translations['storage']['conflict'])
        assert by_name(first) == remote, 'Delayed Undo included another window\'s later task changes'
        assert transaction_state(first) == expected, 'The transaction guard failed to roll back stale Undo'
        assert not errors, errors
        print('Undo delayed snapshot passed: native read completion remains pending; a later remote write is preserved by a refused transaction', flush=True)
    finally:
        context.close()


def check_batch_scope(browser, url):
    context = browser.new_context(reduced_motion='reduce')
    try:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(page, url)
        add_task(page, 'Scope seed', no_deadline=True)
        page.evaluate("""() => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(['tasks', 'config'], 'readwrite');
                const store = tx.objectStore('tasks');
                const all = store.getAll();
                all.onsuccess = () => {
                    const seed = all.result[0];
                    store.clear();
                    for (let i = 0; i < 240; i++) store.put({...seed, id:100000+i,
                        name:`Scope task ${String(i).padStart(3, '0')}`,
                        project:i % 2 ? 'Other scope' : 'Target scope',
                        completed:i % 4 === 0, completedAt:i % 4 === 0 ? '2030-01-01T12:00:00.000Z' : null,
                        order:i * 1000});
                    tx.objectStore('config').put({key:'recoveryHistory', value:[]});
                };
                tx.oncomplete = () => { db.close(); resolve(); };
                tx.onabort = () => reject(tx.error);
            };
        })""")
        page.reload()
        wait_for_app_ready(page)
        select_filter(page, 'all')
        baseline = by_name(page)
        expect(page.locator('.task-item')).to_have_count(100)
        page.locator('#batchModeBtn').click()
        expect(page.locator('.task-item')).to_have_count(100)
        assert_selected(page, 0)
        page.locator('#batchSelectVisibleBtn').click()
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(100)
        assert_selected(page, 240)
        show_more_selected(page, 200, 240)
        show_more_selected(page, 240, 240)
        expect(page.locator('#loadMoreTasksBtn')).to_be_hidden()
        assert by_name(page) == baseline, 'Batch selection or pagination changed persisted task data'

        # Manual order remains paged while selecting; the full matching selection
        # must survive a display-page reset and include tasks absent from the DOM.
        select_sort(page, 'manual')
        expect(page.locator('.task-item')).to_have_count(100)
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(100)
        assert_selected(page, 240)
        assert task_locator(page, 'Scope task 238').count() == 0
        page.locator('#batchFocusBtn').click()
        expect(page.locator('#undoBtn')).to_be_enabled()
        focused_all = by_name(page)
        focus_date = focused_all['Scope task 238']['focusDate']
        assert focus_date, 'An off-page matching task was omitted from the batch write'
        assert focused_all == {name: {**task, 'focusDate': focus_date} for name, task in baseline.items()}, \
            'Full matching batch write omitted an off-page task or changed a field other than focusDate'
        page.locator('#undoBtn').click()
        page.wait_for_function("""() => /Undone|已撤销/.test(document.querySelector('#notificationText').textContent)""")
        assert by_name(page) == baseline, 'Full matching batch Undo did not restore every task field'
        page.locator('#batchSelectVisibleBtn').click()
        assert_selected(page, 240)
        select_project(page, 'Target scope')
        expect(page.locator('.task-item')).to_have_count(100)
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(100)
        assert_selected(page, 120)
        select_filter(page, 'active')
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(60)
        assert_selected(page, 60)
        select_filter(page, 'all')
        expect(page.locator('.task-item')).to_have_count(100)
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(50)
        assert_selected(page, 60)
        page.locator('#searchInput').fill('Scope task 238')
        expect(page.locator('.task-item')).to_have_count(1)
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(1)
        assert_selected(page, 1)
        page.locator('#searchInput').fill('')
        expect(page.locator('.task-item')).to_have_count(100)
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(0)
        assert_selected(page, 1)
        assert task_locator(page, 'Scope task 238').count() == 0
        page.locator('#batchFocusBtn').click()
        expect(page.locator('#undoBtn')).to_be_enabled()
        focused = by_name(page)
        changed = [name for name in baseline if baseline[name] != focused[name]]
        assert changed == ['Scope task 238'], 'Batch action modified hidden or previously pruned selections'
        expected = dict(baseline['Scope task 238'])
        expected['focusDate'] = focused['Scope task 238']['focusDate']
        assert expected['focusDate'] and focused['Scope task 238'] == expected
        page.locator('#undoBtn').click()
        page.wait_for_function("""() => /Undone|已撤销/.test(document.querySelector('#notificationText').textContent)""")
        assert by_name(page) == baseline
        page.locator('#exitBatchModeBtn').click()
        expect(page.locator('.task-select-checkbox')).to_have_count(0)
        expect(page.locator('.task-item')).to_have_count(120)
        expect(page.locator('#taskPagination')).to_be_hidden()
        select_project(page, 'all')
        select_filter(page, 'active')
        select_sort(page, 'manual')
        ordered_before = sorted(baseline.values(), key=lambda task: (task['order'], task['id']))
        visible_names = [task['name'] for task in ordered_before if not task['completed']]
        task_locator(page, visible_names[-1]).locator('.drag-handle').focus()
        page.keyboard.press('Home')
        expected_names = iter([visible_names[-1], *visible_names[:-1]])
        expected_order = [task['name'] if task['completed'] else next(expected_names) for task in ordered_before]
        page.wait_for_function("""expected => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('tasks');
                const all = tx.objectStore('tasks').getAll();
                tx.oncomplete = () => {
                    db.close();
                    const names = all.result.sort((a,b) => a.order-b.order || a.id-b.id).map(task => task.name);
                    resolve(JSON.stringify(names) === JSON.stringify(expected));
                };
            };
        })""", arg=expected_order)
        after_order = by_name(page)
        for name, before in baseline.items():
            assert {**after_order[name], 'order':before['order']} == before, 'Manual reorder changed another task field'
        assert not errors, errors
        print('Batch scope passed: 100/200/partial pages, full matching selection/writes across hidden pages, checkbox focus, exact Undo, scope pruning and preserved manual-order slots', flush=True)
    finally:
        context.close()


def main(browser_name):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if browser_name == 'chromium' else {'headless':True}
        browser = getattr(p, browser_name).launch(**options)
        try:
            print(f'Batch/Undo regression: {browser_name} {browser.version}', flush=True)
            check_undo_after_remote_commit(browser, url, 'batch')
            check_undo_after_remote_commit(browser, url, 'single')
            check_delayed_after_snapshot(browser, url)
            check_batch_scope(browser, url)
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    main(parser.parse_args().browser)
