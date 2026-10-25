#!/usr/bin/env python3
"""Reconnect surviving recurrence links when reviewed merge conflicts are replaced."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import time

from playwright.sync_api import expect, sync_playwright

from check import atomic_report, source_identity, timestamp
from import_reference_playwright import finish_occurrence
from recovery_management_playwright import stored
from repeat_delete_playwright import assert_checkpoint, expected_deletion
from repeat_lineage_playwright import edit_future, prepare, record, reopen, row
from smoke_playwright import click_task_action
from smoke_playwright import (
    assert_backup_payload_integrity, browser_launch_options, exercise_export_backup,
    get_task_records, import_payload_replace, local_server, select_filter,
    stable_fnv1a32, stable_json, wait_for_app_ready,
)


REFERENCES = ('repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId')


def rename(page, identity, name):
    click_task_action(row(page, identity), 'edit')
    page.locator('#taskName').fill(name)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def prepare_merge(page, url, consecutive=False):
    identities = prepare(page, url, length=5 if consecutive else 4, root_zero=True)
    root, old, *rest = identities
    future = rest[-1]
    middle = rest[:-1]
    edit_future(page, future)
    for index, identity in enumerate(middle):
        rename(page, identity, f'Unique merge middle {index}')
    reopen(page, old)
    return identities, middle


def incoming_copy(task):
    return {**deepcopy(task), 'description': '  Imported replacement\r\n中文 e\u0301 👩🏽‍💻\r\n\r\n',
            'tags': ['client,private', 'a"b'], 'reminderOffset': 7.5, 'reminderRepeat': 22.5}


def payload_for(page, tasks):
    payload = exercise_export_backup(page)
    payload['tasks'] = deepcopy(tasks)
    payload.pop('checksum')
    payload['checksum'] = f'fnv1a32:{stable_fnv1a32(stable_json(payload))}'
    assert_backup_payload_integrity(payload, 'backup')
    return payload


def open_merge(page, payload, action='replace'):
    open_settings(page)
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'valid-repeat-merge.json', 'mimeType': 'application/json',
                            'buffer': json.dumps(payload, ensure_ascii=False).encode()})
    expect(page.locator('[data-import-preview]')).to_have_attribute('data-checksum-status', 'valid')
    page.locator('#mergeImportMode').check()
    if page.locator('.import-conflict-select').count():
        page.locator('#importConflictDefaultAction').select_option(action)


def submit_merge(page):
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def assert_incoming_fields(actual, expected):
    excluded = {'id', 'order', *REFERENCES}
    assert {key: value for key, value in actual.items() if key not in excluded} == \
           {key: value for key, value in expected.items() if key not in excluded}, \
        'Repairing existing recurrence links changed explicitly imported task fields'


def assert_existing_records(page, before, deleted, predecessor, successor):
    expected = expected_deletion(before['tasks'], deleted, predecessor, successor)
    current = {task['id']: task for task in get_task_records(page)}
    for task in expected:
        assert current[task['id']] == task, 'Merge repair changed unrelated existing fields or missed a proven link'
    assert not set(deleted) & set(current), 'Reviewed replacement did not delete the old conflicting records'
    assert_checkpoint(before, stored(page))
    return expected


def assert_roundtrip_and_recomplete(page, old, future):
    before = get_task_records(page)
    payload = exercise_export_backup(page)
    assert payload['tasks'] == before, 'Actual JSON download changed recurrence links or imported content'
    import_payload_replace(page, payload)
    select_filter(page, 'all')
    assert get_task_records(page) == before, 'JSON replacement import erased surviving recurrence links'
    finish_occurrence(page, old)
    current = {task['id']: task for task in get_task_records(page)}
    assert set(current) == {task['id'] for task in before}, \
        'Completing an older non-root occurrence created a parallel future after merge round-trip'
    assert current[old]['completed']
    for task in before:
        if task['id'] != old:
            assert current[task['id']] == task, 'Recompleting an older occurrence changed another task'
    assert not current[future]['completed'], 'The independently edited future was lost or completed'


def replace_and_roundtrip(page, url):
    identities, middle = prepare_merge(page, url)
    root, old, _, future = identities
    incoming = incoming_copy(record(page, middle[0]))
    payload = payload_for(page, [incoming])
    before = stored(page)
    open_merge(page, payload)
    submit_merge(page)
    expected = assert_existing_records(page, before, middle, old, future)
    current = get_task_records(page)
    added = [task for task in current if task['id'] not in {item['id'] for item in before['tasks']}]
    assert len(added) == 1 and len(current) == len(before['tasks'])
    assert added[0]['id'] != incoming['id'], 'An incoming ID collision overwrote an existing identity'
    assert_incoming_fields(added[0], incoming)
    assert all(added[0][field] is None for field in REFERENCES), 'A partial file acquired guessed recurrence links'
    assert next(task for task in expected if task['id'] == future)['repeatSourceId'] == root == 0
    page.locator('#undoBtn').click()
    expect(row(page, middle[0])).to_have_count(1)
    assert get_task_records(page) == before['tasks'], 'Undo did not restore deleted records and both repaired metadata fields'
    open_merge(page, payload)
    submit_merge(page)
    assert_roundtrip_and_recomplete(page, old, future)


def consecutive_replace(page, url):
    identities, middle = prepare_merge(page, url, consecutive=True)
    root, old, _, _, future = identities
    incoming = [incoming_copy(record(page, identity)) for identity in middle]
    payload = payload_for(page, incoming)
    before = stored(page)
    open_merge(page, payload)
    submit_merge(page)
    assert_existing_records(page, before, middle, old, future)
    added = {task['name']: task for task in get_task_records(page)
             if task['id'] not in {item['id'] for item in before['tasks']}}
    assert len(added) == 2
    first, second = [added[task['name']] for task in incoming]
    for task in incoming:
        assert_incoming_fields(added[task['name']], task)
        assert added[task['name']]['repeatSourceId'] is None
    assert first['repeatCreatedFrom'] is None and first['nextRepeatTaskId'] == second['id']
    assert second['repeatCreatedFrom'] == first['id'] and second['nextRepeatTaskId'] is None
    assert record(page, future)['repeatSourceId'] == root == 0
    assert_roundtrip_and_recomplete(page, old, future)


def keep_or_skip(page, url, action):
    identities, middle = prepare_merge(page, url)
    _, old, _, future = identities
    incoming = incoming_copy(record(page, middle[0]))
    payload = payload_for(page, [incoming])
    before = stored(page)
    open_merge(page, payload, action)
    submit_merge(page)
    current = get_task_records(page)
    by_id = {task['id']: task for task in current}
    assert all(by_id[task['id']] == task for task in before['tasks']), \
        'Keep/Skip changed or reconnected an existing occurrence'
    added = [task for task in current if task['id'] not in {item['id'] for item in before['tasks']}]
    assert len(added) == (1 if action == 'keep' else 0)
    if added:
        assert_incoming_fields(added[0], incoming)
        assert all(added[0][field] is None for field in REFERENCES)
    assert_roundtrip_and_recomplete(page, old, future)


def distinct_import(page, url):
    identities, middle = prepare_merge(page, url)
    _, old, _, future = identities
    incoming = {**incoming_copy(record(page, middle[0])), 'id': 999, 'name': 'Distinct incoming occurrence'}
    payload = payload_for(page, [incoming])
    before = stored(page)
    open_merge(page, payload)
    expect(page.locator('.import-conflict-select')).to_have_count(0)
    submit_merge(page)
    current = {task['id']: task for task in get_task_records(page)}
    assert len(current) == len(before['tasks']) + 1
    assert all(current[task['id']] == task for task in before['tasks'])
    assert_incoming_fields(current[999], incoming)
    assert_roundtrip_and_recomplete(page, old, future)


def aborted_merge(page, url, phase):
    identities, middle = prepare_merge(page, url)
    _, old, _, future = identities
    incoming = incoming_copy(record(page, middle[0]))
    payload = payload_for(page, [incoming])
    before = stored(page)
    open_merge(page, payload)
    page.evaluate("""({phase, old, future, name, description}) => {
        const original = IDBObjectStore.prototype.put;
        window.repeatMergeAbortInjected = false;
        IDBObjectStore.prototype.put = function(value, ...rest) {
            const trigger = phase === 'checkpoint' ? this.name === 'config' && value?.key === 'recoveryHistory'
                : this.name === 'tasks' && (phase === 'repair'
                    ? value?.id === old && value?.nextRepeatTaskId === future
                    : value?.name === name && value?.description === description);
            if (!trigger) return original.call(this, value, ...rest);
            IDBObjectStore.prototype.put = original;
            const request = original.call(this, value, ...rest);
            window.repeatMergeAbortInjected = true;
            this.transaction.abort();
            return request;
        };
    }""", {'phase': phase, 'old': old, 'future': future,
            'name': incoming['name'], 'description': incoming['description']})
    page.locator('#submitBtn').click()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_enabled()
    assert page.evaluate('window.repeatMergeAbortInjected === true'), 'The requested real transaction abort was not reached'
    assert stored(page) == before, 'Aborted merge changed tasks, recurrence metadata, revision, history or configuration'
    page.locator('#cancelBtn').click()
    page.reload()
    wait_for_app_ready(page)
    assert stored(page) == before, 'Aborted merge changed persisted state after reload'
    open_merge(page, payload)
    submit_merge(page)
    assert_existing_records(page, before, middle, old, future)


def stale_merge(page, url):
    identities, middle = prepare_merge(page, url)
    _, old, _, future = identities
    incoming = incoming_copy(record(page, middle[0]))
    payload = payload_for(page, [incoming])
    open_merge(page, payload)
    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        select_filter(other, 'all')
        click_task_action(row(other, future), 'edit')
        other.locator('#taskDesc').fill('Newer future edit in another real window')
        other.locator('#submitBtn').click()
        expect(other.locator('#taskModal')).to_be_hidden()
        before = stored(other)
        page.locator('#submitBtn').click()
        expect(page.locator('#notification')).to_have_class(re.compile(r'\bwarning\b'))
        assert stored(page) == before, 'A stale merge approval deleted or overwrote newer data'
        if page.locator('#taskModal').is_visible():
            page.locator('#cancelBtn').click()
        open_merge(page, payload)
        submit_merge(page)
        assert_existing_records(page, before, middle, old, future)
        assert record(page, future)['description'] == 'Newer future edit in another real window'
    finally:
        other.close()


def conservative_merge(page, url, cycle=False):
    identities, middle = prepare_merge(page, url)
    root, old, replaced, future = identities
    fixture = get_task_records(page)
    if cycle:
        fixture = [{**task, 'nextRepeatTaskId': old} if task['id'] == replaced else task for task in fixture]
    else:
        descendant = record(page, future)
        fixture.extend([
            {**deepcopy(descendant), 'id': 999, 'name': 'Another explicit future branch'},
            {**deepcopy(descendant), 'id': 998, 'name': 'Shared source with no directed evidence', 'repeatCreatedFrom': None},
        ])
    import_payload_replace(page, fixture)
    incoming = incoming_copy(record(page, replaced))
    payload = payload_for(page, [incoming])
    before = stored(page)
    open_merge(page, payload)
    submit_merge(page)
    current = {task['id']: task for task in get_task_records(page)}
    for task in before['tasks']:
        if task['id'] == replaced:
            assert replaced not in current
            continue
        expected = {**task}
        if not cycle and task['id'] in (future, 999):
            expected['repeatCreatedFrom'] = old
        assert current[task['id']] == expected, 'Merge guessed an ambiguous/cyclic endpoint or changed a source-only task'
    assert current[old]['nextRepeatTaskId'] == replaced
    assert current[future]['repeatSourceId'] == root
    assert_checkpoint(before, stored(page))
    page.locator('#undoBtn').click()
    expect(row(page, replaced)).to_have_count(1)
    assert get_task_records(page) == before['tasks']


CASES = {
    'replace-roundtrip': replace_and_roundtrip,
    'consecutive': consecutive_replace,
    'keep': lambda page, url: keep_or_skip(page, url, 'keep'),
    'skip': lambda page, url: keep_or_skip(page, url, 'skip'),
    'distinct': distinct_import,
    **{f'abort-{phase}': lambda page, url, phase=phase: aborted_merge(page, url, phase)
       for phase in ('repair', 'incoming', 'checkpoint')},
    'stale': stale_merge,
    'ambiguity': conservative_merge,
    'cycle': lambda page, url: conservative_merge(page, url, cycle=True),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', *CASES), default='all')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    selected = CASES if args.case == 'all' else {args.case: CASES[args.case]}
    report = {'browser': args.browser, 'browser_version': None, 'planned_cases': list(selected),
              'cases': [], 'started_at': timestamp(), 'finished_at': None, 'status': 'running',
              'passed': False, 'source': None, 'source_final': None, 'error': None}
    publish = lambda: atomic_report(args.output, report) if args.output else None
    publish()
    try:
        report['source'] = source_identity()
        publish()
        with local_server() as url, sync_playwright() as playwright:
            options = browser_launch_options() if args.browser == 'chromium' else {'headless': True}
            browser = getattr(playwright, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                for name, operation in selected.items():
                    started = time.perf_counter()
                    context = browser.new_context(timezone_id='UTC', reduced_motion='reduce', accept_downloads=True)
                    try:
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        operation(page, url)
                        assert not errors, errors
                        report['cases'].append({'name': name, 'passed': True,
                                                'duration_seconds': round(time.perf_counter() - started, 3)})
                        publish()
                        print(f'Repeat merge {args.browser}: {name} passed', flush=True)
                    except BaseException as error:
                        report['cases'].append({'name': name, 'passed': False,
                                                'duration_seconds': round(time.perf_counter() - started, 3),
                                                'error': f'{type(error).__name__}: {error}'})
                        raise
                    finally:
                        context.close()
            finally:
                browser.close()
        report['source_final'] = source_identity()
        assert report['source'] == report['source_final'], 'Runtime inputs changed during recurrence merge checks'
        report['status'] = 'passed'
        report['passed'] = True
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        report['finished_at'] = timestamp()
        if report['source_final'] is None:
            try:
                report['source_final'] = source_identity()
            except BaseException as error:
                report['status'] = 'failed'
                report['passed'] = False
                report['source_final_error'] = f'{type(error).__name__}: {error}'
        publish()
        print(json.dumps({'browser': report['browser'], 'browser_version': report['browser_version'],
                          'cases': len(report['cases']), 'status': report['status'], 'passed': report['passed']}), flush=True)


if __name__ == '__main__':
    main()
