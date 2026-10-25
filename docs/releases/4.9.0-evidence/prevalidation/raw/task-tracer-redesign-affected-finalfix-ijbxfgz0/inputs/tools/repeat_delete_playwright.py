#!/usr/bin/env python3
"""Atomically reconnect proven repeat links when deleting occurrences."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

from import_reference_playwright import finish_occurrence
from recovery_management_playwright import config, stored
from repeat_lineage_playwright import edit_future, prepare, reopen, row
from smoke_playwright import click_task_action
from smoke_playwright import (
    browser_launch_options, exercise_export_backup, get_task_records, import_payload_replace,
    local_server, select_filter, wait_for_app_ready,
)


def open_delete(page, ids, mode):
    if mode == 'single':
        click_task_action(row(page, ids[0]), 'delete')
    elif mode == 'batch':
        if page.locator('#batchModeBtn').get_attribute('aria-pressed') != 'true':
            page.locator('#batchModeBtn').click()
        for identity in ids:
            row(page, identity).locator('.task-select-checkbox').check()
        page.locator('#batchDeleteBtn').click()
    else:
        page.locator('#openMenuBtn').click()
        page.locator('#clearCompletedBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()


def confirm_delete(page):
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def prepare_chain(page, url, mode):
    identities = prepare(page, url, length=4 if mode == 'single' else 5, root_zero=True)
    root, old, *rest = identities
    future = rest[-1]
    edit_future(page, future)
    reopen(page, old)
    if mode == 'clear':
        reopen(page, root)
    return identities, rest[:-1]


def expected_deletion(before, deleted, predecessor, successor):
    expected = []
    for task in before:
        if task['id'] in deleted:
            continue
        change = {}
        if task['id'] == predecessor:
            change['nextRepeatTaskId'] = successor
        if task['id'] == successor:
            change['repeatCreatedFrom'] = predecessor
        expected.append({**task, **change})
    return expected


def assert_checkpoint(before, after):
    previous, current = config(before), config(after)
    assert current['taskRevision'] == previous['taskRevision'] + 1
    assert current['recoveryHistory'][0]['tasks'] == before['tasks'], \
        'Delete checkpoint did not preserve exact pre-delete links and task fields'
    assert {key: value for key, value in current.items() if key not in {'taskRevision', 'recoveryHistory'}} == \
           {key: value for key, value in previous.items() if key not in {'taskRevision', 'recoveryHistory'}}, \
        'Deletion changed unrelated configuration or backup metadata'


def delete_and_roundtrip(page, url, mode):
    identities, deleted = prepare_chain(page, url, mode)
    root, old, *rest = identities
    future = rest[-1]
    before = stored(page)
    expected = expected_deletion(before['tasks'], deleted, old, future)
    open_delete(page, deleted, mode)
    confirm_delete(page)
    assert get_task_records(page) == expected, 'Delete failed to reconnect only the proven repeat metadata'
    assert_checkpoint(before, stored(page))
    page.locator('#undoBtn').click()
    expect(row(page, deleted[0])).to_have_count(1)
    assert get_task_records(page) == before['tasks'], 'Undo did not restore exact deleted tasks and repeat metadata'
    open_delete(page, deleted, mode)
    confirm_delete(page)
    assert get_task_records(page) == expected
    if mode == 'batch':
        page.locator('#exitBatchModeBtn').click()
    backup = exercise_export_backup(page)
    assert backup['tasks'] == expected, 'Actual download changed reconnected metadata or task content'
    import_payload_replace(page, backup)
    select_filter(page, 'all')
    assert get_task_records(page) == expected, 'Replace import erased reconnected non-root repeat links'
    finish_occurrence(page, old)
    current = get_task_records(page)
    assert {task['id'] for task in current} == {task['id'] for task in expected}, \
        'Completing the old non-root occurrence after transfer duplicated its edited future'
    assert next(task for task in current if task['id'] == old)['completed']
    for task in expected:
        if task['id'] != old:
            assert next(item for item in current if item['id'] == task['id']) == task
    assert next(task for task in current if task['id'] == future)['repeatSourceId'] == root


def abort_delete(page, url, mode):
    identities, deleted = prepare_chain(page, url, mode)
    old = identities[1]
    before = stored(page)
    open_delete(page, deleted, mode)
    page.evaluate("""identity => {
        const original = IDBObjectStore.prototype.put;
        window.repeatDeleteAbortInjected = false;
        IDBObjectStore.prototype.put = function(value, ...rest) {
            if (this.name !== 'tasks' || value?.id !== identity) return original.call(this, value, ...rest);
            IDBObjectStore.prototype.put = original;
            const request = original.call(this, value, ...rest);
            window.repeatDeleteAbortInjected = true;
            this.transaction.abort();
            return request;
        };
    }""", old)
    page.locator('#submitBtn').click()
    if mode == 'clear':
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#submitBtn')).to_be_enabled()
    else:
        expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    assert page.evaluate('window.repeatDeleteAbortInjected === true'), 'Metadata write did not reach the abort injection'
    assert stored(page) == before, 'Aborted deletion changed tasks, links, revision, history, config or backup metadata'
    if mode == 'clear':
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
    page.reload()
    wait_for_app_ready(page)
    assert stored(page) == before, 'Aborted deletion changed persisted state after reload'


def stale_delete(page, url, mode):
    identities, deleted = prepare_chain(page, url, mode)
    before = stored(page)
    open_delete(page, deleted, mode)
    remote = deepcopy(before['tasks'][-1])
    remote['description'] = 'A newer write from another database client'
    page.evaluate("""task => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const revision = tx.objectStore('config').get('taskRevision');
            revision.onsuccess = () => {
                tx.objectStore('tasks').put(task);
                tx.objectStore('config').put({key:'taskRevision',value:revision.result.value+1});
            };
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", remote)
    remote_state = stored(page)
    confirm_delete(page)
    language = page.locator('html').get_attribute('lang')
    translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
    expect(page.locator('#notificationText')).to_have_text(translations['storage']['conflict'])
    assert stored(page) == remote_state, 'Stale deletion changed newer remote tasks, links, revision or history'


def deleted_boundaries(page, url):
    root, old, future = prepare(page, url, length=3, root_zero=True)
    baseline = get_task_records(page)
    open_delete(page, [root], 'single')
    confirm_delete(page)
    expected = expected_deletion(baseline, [root], None, old)
    assert get_task_records(page) == expected
    assert all(task['repeatSourceId'] == root for task in expected), 'Deleting the root silently rerooted the series'
    page.locator('#undoBtn').click()
    expect(row(page, root)).to_have_count(1)
    assert get_task_records(page) == baseline
    reopen(page, old)
    before = get_task_records(page)
    open_delete(page, [future], 'single')
    confirm_delete(page)
    expected = expected_deletion(before, [future], old, None)
    assert get_task_records(page) == expected
    finish_occurrence(page, old)
    current = get_task_records(page)
    added = [task for task in current if task['id'] not in {item['id'] for item in expected}]
    assert len(added) == 1 and added[0]['repeatCreatedFrom'] == old


def ambiguous_links(page, url):
    for direction in ('successors', 'predecessors'):
        root, old, middle, future = prepare(page, url, length=4, root_zero=True)
        edit_future(page, future)
        reopen(page, old)
        fixture = get_task_records(page)
        child = next(task for task in fixture if task['id'] == future)
        extra = {**deepcopy(child), 'id': 999, 'name': 'Another explicitly linked branch',
                 'repeatCreatedFrom': middle if direction == 'successors' else None,
                 'nextRepeatTaskId': middle if direction == 'predecessors' else None}
        stray = {**deepcopy(child), 'id': 998, 'name': 'Same source without a proven edge',
                 'repeatCreatedFrom': None, 'nextRepeatTaskId': None}
        import_payload_replace(page, [*fixture, extra, stray])
        before = stored(page)
        expected = []
        for task in before['tasks']:
            if task['id'] == middle:
                continue
            change = {}
            if direction == 'successors' and task['id'] in (future, extra['id']):
                change['repeatCreatedFrom'] = old
            if direction == 'predecessors' and task['id'] in (old, extra['id']):
                change['nextRepeatTaskId'] = future
            expected.append({**task, **change})
        open_delete(page, [middle], 'single')
        confirm_delete(page)
        assert get_task_records(page) == expected, 'Deletion guessed an ambiguous endpoint or an unrelated same-source task'
        assert_checkpoint(before, stored(page))
        ambiguous_task = old if direction == 'successors' else future
        ambiguous_field = 'nextRepeatTaskId' if direction == 'successors' else 'repeatCreatedFrom'
        assert next(task for task in expected if task['id'] == ambiguous_task)[ambiguous_field] == middle
        page.locator('#undoBtn').click()
        expect(row(page, middle)).to_have_count(1)
        assert get_task_records(page) == before['tasks']


def cyclic_links(page, url):
    root, old, middle, future = prepare(page, url, length=4, root_zero=True)
    edit_future(page, future)
    reopen(page, old)
    fixture = get_task_records(page)
    fixture = [{**task, 'nextRepeatTaskId': old} if task['id'] == middle else task for task in fixture]
    import_payload_replace(page, fixture)
    before = stored(page)
    open_delete(page, [middle], 'single')
    confirm_delete(page)
    assert get_task_records(page) == [task for task in before['tasks'] if task['id'] != middle], \
        'Deletion guessed replacement metadata inside an explicitly cyclic component'
    assert_checkpoint(before, stored(page))
    page.locator('#undoBtn').click()
    expect(row(page, middle)).to_have_count(1)
    assert get_task_records(page) == before['tasks']


CASES = {**{mode: (lambda page, url, mode=mode: delete_and_roundtrip(page, url, mode))
            for mode in ('single', 'batch', 'clear')},
         **{f'abort-{mode}': (lambda page, url, mode=mode: abort_delete(page, url, mode))
            for mode in ('single', 'batch', 'clear')},
         **{f'stale-{mode}': (lambda page, url, mode=mode: stale_delete(page, url, mode))
            for mode in ('single', 'batch', 'clear')},
         'boundaries': deleted_boundaries, 'ambiguity': ambiguous_links, 'cycles': cyclic_links}


def run(engine, case):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(**options)
        try:
            selected = CASES if case == 'all' else {case: CASES[case]}
            for name, operation in selected.items():
                context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    operation(page, url)
                    assert not errors, errors
                    print(f'Repeat delete passed: {name}; browser={engine}', flush=True)
                finally:
                    context.close()
            print(json.dumps({'browser_engine': engine, 'browser': browser.version,
                              'cases': len(selected), 'passed': True}), flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
