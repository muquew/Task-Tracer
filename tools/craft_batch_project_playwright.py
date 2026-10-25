#!/usr/bin/env python3
"""Protect small batch-project moves, rollback, stale review and archive parity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

from batch_selection_playwright import transaction_state
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, click_batch_action,
    click_task_action, enter_batch_mode, local_server, select_filter,
    select_language, task_locator, wait_for_app_ready,
)
from workspace_failure_playwright import inject, injection_seen


ROOT = Path(__file__).resolve().parents[1]
SELECTED = ('Move selected A', 'Move selected B')
PROTECTED = 'Protected task C'


def messages(page):
    code = page.locator('html').get_attribute('lang')
    return json.loads((ROOT / 'resources' / f'{code}.json').read_text())


def by_name(snapshot):
    return {task['name']: task for task in snapshot['tasks']}


def revision(snapshot):
    return snapshot['revision']['value']


def prepare(page, url):
    clear_app_data(page, url)
    select_language(page, 'en')
    add_task(page, SELECTED[0], description='Keep A description and recurrence',
             project='Inbox', tags=['move-alpha'], due_date='2032-04-09',
             due_time='09:00', repeat_type='daily', reminder_offset='-1',
             subtasks=['Keep A checklist'])
    add_task(page, SELECTED[1], description='Keep B description and completion',
             project='Inbox', tags=['move-beta'], no_deadline=True,
             subtasks=['Keep B checklist'])
    add_task(page, PROTECTED, description='Never overwrite unselected C',
             project='Protected', no_deadline=True)
    click_task_action(task_locator(page, SELECTED[0]), 'focus')
    task_locator(page, SELECTED[1]).locator('[data-action="toggle"]').click()
    select_filter(page, 'all')
    expect(task_locator(page, SELECTED[1]).locator('[data-action="toggle"]')).to_have_attribute('aria-pressed', 'true')
    before = transaction_state(page)
    assert len(before['tasks']) == 3
    assert by_name(before)[SELECTED[0]]['focusDate']
    assert not by_name(before)[SELECTED[0]]['completed']
    assert by_name(before)[SELECTED[1]]['completed']
    return before


def select_pair(page):
    select_filter(page, 'all')
    enter_batch_mode(page)
    for name in SELECTED:
        task_locator(page, name).locator('.task-select-checkbox').check()
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(2)


def open_move(page):
    select_pair(page)
    click_batch_action(page, 'move-project')
    expect(page.locator('#taskModal')).to_be_visible()
    field = page.locator('#batchMoveProjectInput')
    expect(field).to_be_visible()
    expect(field).to_have_attribute('list', 'batchProjectOptions')
    expect(page.locator('#batchProjectOptions option[value="Protected"]')).to_have_count(1)
    return field


def install_transaction_monitor(page):
    page.evaluate("""() => {
        const original = IDBDatabase.prototype.transaction;
        window.craftProjectTransactions = {started:0, committed:0, aborted:0};
        IDBDatabase.prototype.transaction = function(...args) {
            const tx = original.apply(this, args);
            if (tx.mode === 'readwrite' && Array.from(tx.objectStoreNames).includes('tasks')) {
                const counts = window.craftProjectTransactions;
                counts.started++;
                tx.addEventListener('complete', () => counts.committed++);
                tx.addEventListener('abort', () => counts.aborted++);
            }
            return tx;
        };
    }""")


def monitor(page):
    return page.evaluate('window.craftProjectTransactions')


def assert_transaction_delta(page, before, *, committed, aborted):
    after = monitor(page)
    assert {key: after[key] - before[key] for key in before} == {
        'started': committed + aborted, 'committed': committed, 'aborted': aborted,
    }, 'The reviewed operation used unexpected task readwrite transactions'


def assert_project_only(before, after, project):
    old = by_name(before)
    current = by_name(after)
    assert set(current) == set(old), 'A project move added or lost a task'
    for name, task in old.items():
        expected = {**task, 'project': project} if name in SELECTED else task
        assert current[name] == expected, f'A project move changed fields outside selected project: {name}'
    assert revision(after) == revision(before) + 1, 'One project move must commit one task revision'


def submit_move(page):
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def undo_tasks(page, before):
    expect(page.locator('#undoBtn')).to_be_enabled()
    page.locator('#undoBtn').click()
    prefix = messages(page)['undo']['restored'].split('{action}')[0]
    expect(page.locator('#notificationText')).to_contain_text(prefix)
    assert transaction_state(page)['tasks'] == before['tasks'], 'Undo did not restore the exact task records'


def move_and_undo(page, url):
    before = prepare(page, url)
    field = open_move(page)
    install_transaction_monitor(page)
    mark = monitor(page)
    field.fill('   ')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(field).to_have_value('   ')
    expect(field).to_be_focused()
    expect(page.locator('#notificationText')).to_have_text(messages(page)['craft']['batchProjectRequired'])
    assert transaction_state(page) == before, 'Blank project validation wrote tasks, revision or recovery history'
    assert monitor(page) == mark, 'Blank project validation began a task write'

    field.fill('  Client    Work  ')
    submit_move(page)
    assert_project_only(before, transaction_state(page), 'Client Work')
    assert_transaction_delta(page, mark, committed=1, aborted=0)
    undo_tasks(page, before)

    existing_before = transaction_state(page)
    field = open_move(page)
    field.fill('Protected')
    mark = monitor(page)
    submit_move(page)
    assert_project_only(existing_before, transaction_state(page), 'Protected')
    assert_transaction_delta(page, mark, committed=1, aborted=0)
    undo_tasks(page, existing_before)
    print('Batch project move passed: blank guard, free-text normalization, existing project, one atomic commit, selected fields only and exact Undo', flush=True)


def atomic_abort_and_retry(page, url):
    before = prepare(page, url)
    field = open_move(page)
    raw = '  Client    Work  '
    field.fill(raw)
    install_transaction_monitor(page)
    mark = monitor(page)
    inject(page, 'put', 'tasks', occurrence=2, queued=True)
    page.locator('#submitBtn').click()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_enabled()
    expect(field).to_have_value(raw)
    observation = injection_seen(page, True)
    assert observation['matched'] == 2, 'The injected rollback did not reach the second queued task put'
    assert transaction_state(page) == before, 'An aborted multi-project update partially changed tasks, revision or recovery history'
    assert_transaction_delta(page, mark, committed=0, aborted=1)
    mark = monitor(page)
    submit_move(page)
    assert_project_only(before, transaction_state(page), 'Client Work')
    assert_transaction_delta(page, mark, committed=1, aborted=0)
    undo_tasks(page, before)
    print('Batch project rollback passed: second queued put abort leaves tasks/revision/history unchanged, retains input and retries exactly once', flush=True)


def stale_move_refuses(page, url):
    baseline = prepare(page, url)
    field = open_move(page)
    field.fill('Client Work')
    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        select_filter(other, 'all')
        click_task_action(task_locator(other, SELECTED[0]), 'edit')
        remote_description = 'A newer description from another open window must survive'
        other.locator('#taskDesc').fill(remote_description)
        other.locator('#submitBtn').click()
        expect(other.locator('#taskModal')).to_be_hidden()
        latest = transaction_state(other)
        assert by_name(latest)[SELECTED[0]]['description'] == remote_description
        assert by_name(latest)[SELECTED[1]] == by_name(baseline)[SELECTED[1]]
        assert by_name(latest)[PROTECTED] == by_name(baseline)[PROTECTED]
        page.locator('#submitBtn').click()
        labels = messages(page)['storage']
        refused = re.compile('^(?:' + '|'.join(re.escape(labels[key]) for key in ('staleConfirmation', 'conflict')) + ')$')
        expect(page.locator('#notificationText')).to_have_text(refused)
        assert transaction_state(page) == latest, 'A stale project dialog overwrote remote tasks or changed their revision/history'
        if page.locator('#taskModal').is_visible():
            expect(field).to_have_value('Client Work')
        print('Batch project stale review passed: a real remote edit survives old-dialog submission with exact tasks/revision/history preserved', flush=True)
    finally:
        other.close()


def assert_archive_only(before, after, names):
    original = by_name(before)
    archived = by_name(after)
    assert set(archived) == set(original)
    for name, task in original.items():
        if name in names:
            result = archived[name]
            assert result['archived'] and result['archivedAt']
            assert result == {**task, 'archived': True, 'archivedAt': result['archivedAt']}, 'Archiving changed completion, plan or another task field'
        else:
            assert archived[name] == task, 'Archiving changed an unselected record'
    assert revision(after) == revision(before) + 1


def archive_parity(page, url):
    before = prepare(page, url)
    assert not by_name(before)[SELECTED[0]]['completed']
    click_task_action(task_locator(page, SELECTED[0]), 'archive')
    expect(task_locator(page, SELECTED[0])).to_have_count(0)
    assert_archive_only(before, transaction_state(page), {SELECTED[0]})
    undo_tasks(page, before)
    batch_before = transaction_state(page)
    select_pair(page)
    click_batch_action(page, 'archive')
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_locator(page, SELECTED[0])).to_have_count(0)
    expect(task_locator(page, SELECTED[1])).to_have_count(0)
    assert_archive_only(batch_before, transaction_state(page), set(SELECTED))
    undo_tasks(page, batch_before)
    print('Archive parity passed: single unfinished and batch mixed-status records change only archive fields and both Undo exactly', flush=True)


def run(engine, selected):
    cases = {'move': move_and_undo, 'atomic': atomic_abort_and_retry,
             'stale': stale_move_refuses, 'archive': archive_parity}
    with local_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(playwright, engine).launch(**options)
        try:
            print(f'Craft batch project: {engine} {browser.version}', flush=True)
            for name, check in cases.items():
                if selected not in ('all', name):
                    continue
                context = browser.new_context(reduced_motion='reduce', timezone_id='UTC',
                                              viewport={'width': 1280, 'height': 900})
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    check(page, url)
                    assert not errors, errors
                finally:
                    context.close()
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'move', 'atomic', 'stale', 'archive'), default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
