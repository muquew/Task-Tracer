#!/usr/bin/env python3
"""Exercise a realistic synthetic workspace through backup, import and recovery."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

from playwright.sync_api import expect, sync_playwright
from check import source_identity
from recovery_playwright import open_recovery
from smoke_playwright import (
    add_task, assert_backup_payload_integrity, browser_launch_options,
    clear_app_data, exercise_export_backup, get_task_records, local_server,
    select_filter, select_project, select_view, task_locator, wait_for_app_ready,
)
from validate_static import app_version

ROOT = Path(__file__).resolve().parents[1]


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def tool_identity():
    names = ['tools/workspace_roundtrip_playwright.py', 'tools/check.py',
             'tools/smoke_playwright.py', 'tools/recovery_playwright.py',
             'tools/validate_static.py']
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    encoded = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return {'files': files, 'sha256': hashlib.sha256(encoded).hexdigest()}


def write_report(output, report, exclusive=False):
    if not output:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output.parent,
                                         prefix=f'.{output.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def fingerprint(tasks):
    return hashlib.sha256(json.dumps(tasks, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def measure(action, operation, metrics):
    started = time.perf_counter()
    metrics['current_operation'] = action
    try:
        result = operation()
    finally:
        metrics[action + '_ms'] = round((time.perf_counter() - started) * 1000, 1)
        print(f'{action}: {metrics[action + "_ms"]} ms', flush=True)
    metrics['current_operation'] = None
    return result


def database_summary(page, include_history=False):
    return page.evaluate("""async includeHistory => {
        const data = await new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
                const tasks = tx.objectStore('tasks').getAll();
            const revision = tx.objectStore('config').get('taskRevision');
                const history = includeHistory ? tx.objectStore('config').get('recoveryHistory') : null;
            tx.oncomplete = () => {db.close(); resolve({tasks:tasks.result, revision:revision.result?.value || 0,
                history:history?.result?.value || []});};
                tx.onabort = () => reject(tx.error);
            };
        });
        const digest = async records => {
            const canonical = JSON.stringify(records, (key, value) => {
                if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
                return Object.fromEntries(Object.keys(value).sort().map(key => [key, value[key]]));
            });
            const result = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical));
            return Array.from(new Uint8Array(result), byte => byte.toString(16).padStart(2,'0')).join('');
        };
        const history = [];
        for (const point of data.history) history.push({id:point.id, count:point.tasks.length, signature:await digest(point.tasks)});
        return {count:data.tasks.length, signature:await digest(data.tasks), history, revision:data.revision,
            subtaskCount:data.tasks.reduce((total, task) => total+task.subtasks.length,0)};
    }""", include_history)


def replace_from_backup(page, payload, expected_signature):
    with tempfile.TemporaryDirectory(prefix='task-tracer-workspace-') as folder:
        source = Path(folder) / 'workspace-backup.json'
        source.write_text(json.dumps(payload, ensure_ascii=False))
        page.locator('#openMenuBtn').click()
        with page.expect_file_chooser() as chooser:
            page.locator('#importBtn').click()
        chooser.value.set_files(source)
        expect(page.locator('#mergeImportMode')).to_be_visible()
        expect(page.locator('.import-conflict-select')).to_have_count(0)
        with page.expect_download() as snapshot_info:
            page.locator('#submitBtn').click()
        snapshot = json.loads(snapshot_info.value.path().read_text())
        assert_backup_payload_integrity(snapshot, 'pre-import-backup')
        assert fingerprint(snapshot['tasks']) == expected_signature, 'Pre-import backup changed current task fields'
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        select_filter(page, 'all')


def seed_workspace(page, size, subtask_count):
    add_task(page, 'Workspace seed', no_deadline=True)
    page.evaluate("""({size, subtaskCount}) => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const store = tx.objectStore('tasks');
            const seed = store.getAll();
            seed.onsuccess = () => {
                const template = seed.result[0];
                store.clear();
                for (let i = 0; i < size; i++) {
                    const date = new Date();
                    date.setDate(date.getDate() + i % 28);
                    date.setHours(12, 30, 0, 0);
                    const localDate = [date.getFullYear(), String(date.getMonth()+1).padStart(2,'0'), String(date.getDate()).padStart(2,'0')].join('-');
                    const chainLength = Math.min(size, 4);
                    const identity = i === 0 ? 0 : 100000 + i;
                    const chain = i < chainLength;
                    const dated = chain || i % 4 !== 0;
                    const due = dated ? date.toISOString() : null;
                    store.put({...template, id: identity,
                        name: `Workspace task ${String(i).padStart(5, '0')} 中文`,
                        description: `Synthetic report entry ${i}: commas, "quotes"\nSecond line 中文 🚀.`,
                        project: `Project ${i % 10}`, tags: ['workspace', `tag${i % 20}`],
                        dueDate: due, dueAt: due,
                        dueLocalDate: dated ? localDate : null,
                        dueLocalTime: dated ? '12:30' : null,
                        dueTimeZone: dated ? Intl.DateTimeFormat().resolvedOptions().timeZone : null,
                        reminderOffset: -1, reminderRepeat: -1,
                        repeatType: chain ? 'daily' : 'none', repeatInterval: 1,
                        repeatSourceId: chain && i > 0 ? 0 : null,
                        repeatCreatedFrom: chain && i > 0 ? (i === 1 ? 0 : 100000 + i - 1) : null,
                        nextRepeatTaskId: chain && i + 1 < chainLength ? 100000 + i + 1 : null,
                        completed: chain && i + 1 < chainLength,
                        completedAt: chain && i + 1 < chainLength ? due : null,
                        order: i * 1000,
                        subtasks: Array.from({length: subtaskCount}, (_, index) => ({
                            id: (100000+i)*100 + index,
                            text: `Synthetic subtask ${index} / 中文`, completed: index % 3 === 0
                        }))});
                }
                tx.objectStore('config').put({key:'recoveryHistory', value:[]});
            };
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", {'size': size, 'subtaskCount': subtask_count})


def assert_records(page, expected, message):
    actual = get_task_records(page)
    assert actual == expected, message


def undo_exact(page, expected, previous_revision):
    expect(page.locator('#undoBtn')).to_be_enabled()
    page.locator('#undoBtn').click()
    page.wait_for_function("""() => /Undone|已撤销/.test(document.querySelector('#notificationText').textContent)""")
    expect(page.locator('#undoBtn')).to_be_disabled()
    restored = database_summary(page)
    assert restored['signature'] == fingerprint(expected), 'Undo did not restore exact task fields'
    assert restored['revision'] == previous_revision + 1, 'Undo did not commit exactly one task revision'


def probe_unfiltered_batch(page, size, metrics):
    before = database_summary(page)
    def enter():
        page.locator('#batchModeBtn').click()
        expect(page.locator('.task-item')).to_have_count(min(size, 100))
        expect(page.locator('#batchSelectVisibleBtn')).to_be_enabled()
    measure('batch_unfiltered_entry', enter, metrics)
    metrics['batch_unfiltered_task_nodes'] = page.locator('.task-item').count()
    metrics['batch_unfiltered_dom_nodes'] = page.locator('*').count()
    metrics['batch_unfiltered_total_matches'] = size
    if size > 100:
        expect(page.locator('#taskPagination')).to_be_visible()
        expect(page.locator('#taskPagination p')).to_contain_text(str(size))
    page.locator('#batchSelectVisibleBtn').click()
    assert_selection(page, size, min(size, 100))
    metrics['batch_unfiltered_selected_tasks'] = size
    if size > 100:
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.task-item')).to_have_count(min(size, 200))
        assert_selection(page, size, min(size, 200))
        metrics['batch_unfiltered_loaded_task_nodes'] = page.locator('.task-item').count()
    page.locator('#exitBatchModeBtn').click()
    expect(page.locator('.task-item')).to_have_count(min(size, 100))
    after = database_summary(page)
    assert after == before, 'Entering or leaving batch mode changed task data or its revision'


def assert_selection(page, total, rendered):
    expect(page.locator('#batchSelectionSummary')).to_have_text(re.compile(rf'(^|\D){total}(\D|$)'))
    expect(page.locator('.task-select-checkbox:checked')).to_have_count(rendered)


def exercise_batch_roundtrip(page, baseline, metrics):
    signature = fingerprint(baseline)
    project = baseline[-1]['project']
    selected_ids = {task['id'] for task in baseline if task['project'] == project}
    select_project(page, project)
    page.locator('#batchModeBtn').click()
    expect(page.locator('.task-item')).to_have_count(min(len(selected_ids), 100))
    page.locator('#batchSelectVisibleBtn').click()
    assert_selection(page, len(selected_ids), min(len(selected_ids), 100))
    before = database_summary(page)

    def focus():
        page.locator('#batchFocusBtn').click()
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(0)
        expect(page.locator('#undoBtn')).to_be_enabled()
    measure('batch_focus', focus, metrics)
    focused = get_task_records(page)
    changed = set()
    for expected, actual in zip(baseline, focused, strict=True):
        assert actual['id'] == expected['id']
        if expected['id'] in selected_ids:
            assert actual['focusDate'], 'Selected batch task was not placed in Today Plan'
            assert actual == {**expected, 'focusDate': actual['focusDate']}, 'Batch focus changed another task field'
            if actual != expected:
                changed.add(actual['id'])
        else:
            assert actual == expected, 'Batch focus changed an unselected task'
    assert changed == selected_ids, 'Batch focus did not change exactly the reviewed selection'
    focused_summary = database_summary(page)
    assert focused_summary['revision'] == before['revision'] + 1
    metrics['batch_focus_selected_tasks'] = len(selected_ids)
    measure('batch_focus_undo', lambda: undo_exact(page, baseline, focused_summary['revision']), metrics)

    # Small fixtures with only repeat members delete the whole chain, avoiding
    # an expectation that intentionally ignores valid metadata reconnection.
    delete_project = project if baseline[-1]['repeatType'] == 'none' else 'all'
    select_project(page, delete_project)
    deleted_ids = {task['id'] for task in baseline
                   if delete_project == 'all' or task['project'] == delete_project}
    survivors = [task for task in baseline if task['id'] not in deleted_ids]
    metrics['batch_delete_selected_tasks'] = len(deleted_ids)

    def remove():
        before_delete = database_summary(page)
        page.locator('#batchSelectVisibleBtn').click()
        assert_selection(page, len(deleted_ids), min(len(deleted_ids), 100))
        page.locator('#batchDeleteBtn').click()
        expect(page.locator('#taskModal')).to_be_visible()
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        current = database_summary(page, include_history=True)
        assert current['signature'] == fingerprint(survivors), 'Batch deletion changed surviving fields or removed other tasks'
        assert current['count'] == len(survivors)
        assert current['revision'] == before_delete['revision'] + 1
        assert current['history'][0]['signature'] == signature, 'Batch delete checkpoint lost original fields or repeat relationships'
        return current

    first_delete = measure('batch_delete', remove, metrics)
    measure('batch_delete_undo', lambda: undo_exact(page, baseline, first_delete['revision']), metrics)
    deleted = measure('checkpoint_delete', remove, metrics)
    checkpoint_id = deleted['history'][0]['id']
    def restore():
        open_recovery(page)
        page.locator('#recoverySelect').select_option(checkpoint_id, force=True)
        page.locator('#recoveryConfirm').check()
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
    measure('checkpoint_restore', restore, metrics)
    restored = database_summary(page, include_history=True)
    assert restored['signature'] == signature, 'Recovery changed task fields or repeat relationships'
    assert restored['revision'] == deleted['revision'] + 1
    assert any(point['signature'] == fingerprint(survivors) for point in restored['history']), 'Recovery lost the replaced state'
    assert_records(page, baseline, 'Batch/Undo/checkpoint sequence did not restore the complete workspace')
    page.locator('#exitBatchModeBtn').click()
    select_project(page, 'all')
    expect(page.locator('.task-item')).to_have_count(min(len(baseline), 100))


def exercise_paged_view(page, view, baseline, metrics):
    size = len(baseline)
    target = baseline[-1]
    measure(view, lambda: select_view(page, view), metrics)
    expect(page.locator('.task-item')).to_have_count(min(size, 100))
    metrics[view + '_task_nodes'] = page.locator('.task-item').count()
    if size > 100:
        page.locator('#loadMoreTasksBtn').click()
        expect(page.locator('.task-item')).to_have_count(min(size, 200))
        metrics[view + '_loaded_task_nodes'] = page.locator('.task-item').count()
    page.locator('#searchInput').fill(target['name'])
    expect(task_locator(page, target['name'])).to_have_count(1)
    expect(task_locator(page, target['name'])).to_have_attribute('data-task-id', str(target['id']))
    page.locator('#searchInput').fill('')
    expect(page.locator('.task-item')).to_have_count(min(size, 100))
    metrics[view + '_tail_search_id'] = target['id']


def exercise_calendar(page, baseline, metrics, full_views):
    measure('calendar', lambda: select_view(page, 'calendar'), metrics)
    metrics['calendar_task_nodes'] = page.locator('.calendar-task').count()
    if not full_views:
        return
    dated = [task for task in baseline if task['dueAt']]
    undated = [task for task in baseline if not task['dueAt']]
    for kind, tasks in [('dated', dated), ('undated', undated)]:
        if not tasks:
            continue
        target = tasks[-1]
        page.locator('#searchInput').fill(target['name'])
        selector = (f'[data-calendar-task-id="{target["id"]}"]' if kind == 'dated'
                    else f'.date-view-undated .task-item[data-task-id="{target["id"]}"]')
        expect(page.locator(selector)).to_have_count(1)
        metrics[f'calendar_{kind}_tail_search_id'] = target['id']
        page.locator('#searchInput').fill('')
    if len(undated) > 100:
        expect(page.locator('.date-view-undated .task-item')).to_have_count(100)
        page.locator('[data-calendar-action="undated-more"]').click()
        expect(page.locator('.date-view-undated .task-item')).to_have_count(min(200, len(undated)))
        metrics['calendar_loaded_undated_nodes'] = page.locator('.date-view-undated .task-item').count()
    groups = Counter(task['dueLocalDate'] for task in dated)
    for key in sorted(groups):
        button = page.locator(f'[data-calendar-detail-date="{key}"]')
        if button.count():
            button.click()
            expect(page.locator('.calendar-detail-task')).to_have_count(min(100, groups[key]))
            metrics['calendar_detail_task_nodes'] = page.locator('.calendar-detail-task').count()
            metrics['calendar_detail_total_tasks'] = groups[key]
            if groups[key] > 100:
                page.locator('[data-calendar-action="detail-more"]').click()
                expect(page.locator('.calendar-detail-task')).to_have_count(min(200, groups[key]))
                metrics['calendar_loaded_detail_nodes'] = page.locator('.calendar-detail-task').count()
            page.locator('.calendar-detail-close').click()
            break
    measure('list_from_calendar', lambda: select_view(page, 'list'), metrics)


def run(size, subtask_count, include_full_views, output):
    expect.set_options(timeout=45000)
    report = {
        'schema_version': 2, 'run_id': str(uuid.uuid4()), 'started_at': timestamp(),
        'finished_at': None, 'status': 'running', 'completed': False, 'passed': False,
        'assertions_passed': False, 'app_version': None,
        'tasks': size, 'subtasks_per_task': subtask_count, 'browser_engine': 'chromium',
        'source': None, 'tool_inputs': None,
        'source_final': None, 'tool_inputs_final': None,
        'source_unchanged': None, 'tool_inputs_unchanged': None,
        'integrity_errors': [], 'error': None, 'checks': [], 'page_errors': [], 'current_operation': None,
        'scope': {'full_views': include_full_views, 'synthetic_data': True,
                  'real_device': False, 'controlled_performance_benchmark': False,
                  'notes': 'Elapsed values describe this correctness run; CPU/load are not controlled.'},
    }
    write_report(output, report, exclusive=True)
    page = None
    caught = None
    try:
        report['app_version'] = app_version((ROOT / 'index.html').read_text())
        report['source'] = source_identity()
        report['tool_inputs'] = tool_identity()
        write_report(output, report)
        with local_server() as url, sync_playwright() as p:
            browser = p.chromium.launch(**browser_launch_options())
            context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
            try:
                report['browser'] = browser.version
                page = context.new_page()
                page.set_default_timeout(45000)
                downloads = []
                page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
                page.on('download', lambda download: downloads.append(download))
                clear_app_data(page, url)
                seed_workspace(page, size, subtask_count)

                def reload():
                    page.reload()
                    wait_for_app_ready(page)
                    initial_active = size - max(0, min(size, 4) - 1)
                    expect(page.locator('.task-item')).to_have_count(min(initial_active, 100))
                    select_filter(page, 'all')
                    expect(page.locator('.task-item')).to_have_count(min(size, 100))
                measure('reload', reload, report)
                expected = database_summary(page)
                signature = expected['signature']
                assert expected['count'] == size
                assert expected['subtaskCount'] == size * subtask_count
                report['baseline_signature'] = signature
                report['checks'].append('seed-reload-all-task-and-subtask-counts')

                if include_full_views:
                    probe_unfiltered_batch(page, size, report)
                    report['checks'].append('unfiltered-batch-entry-no-task-writes')
                else:
                    report['scope']['unfiltered_batch'] = 'Not requested; pass --full-views for the unfiltered workspace probe.'

                backup = measure('json_export', lambda: exercise_export_backup(page), report)
                baseline = backup['tasks']
                assert fingerprint(baseline) == signature, 'JSON export changed task fields'
                assert_records(page, baseline, 'Real downloaded backup differs from the complete database')
                report['export_file_bytes'] = downloads[-1].path().stat().st_size
                report['compact_export_bytes'] = len(json.dumps(backup, ensure_ascii=False).encode())
                identities = {task['id'] for task in baseline}
                links = [(task['id'], field, task[field]) for task in baseline
                         for field in ('repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId')
                         if task[field] is not None]
                assert all(target in identities for _, _, target in links), 'Fixture has invalid repeat references'
                assert any(target == 0 for _, _, target in links) == (size > 1), 'Fixture lost its valid root-ID-zero relationship'
                report['fixture_repeat_members'] = min(size, 4)
                report['fixture_repeat_links'] = len(links)
                report['checks'].append('real-json-download-checksum-all-fields-and-valid-repeat-links')
                measure('json_replace_import', lambda: replace_from_backup(page, backup, signature), report)
                assert_records(page, baseline, 'JSON replacement round-trip changed complete task fields')
                assert database_summary(page)['signature'] == signature
                report['checks'].append('actual-json-replacement-and-safety-snapshot-all-fields')

                exercise_batch_roundtrip(page, baseline, report)
                report['checks'].append('scoped-batch-focus-delete-exact-undo-and-checkpoint-restore')

                before_views = database_summary(page)
                if include_full_views:
                    exercise_paged_view(page, 'list', baseline, report)
                    exercise_paged_view(page, 'timeline', baseline, report)
                    report['checks'].append('list-and-timeline-pagination-reset-and-tail-search')
                else:
                    report['timeline_skipped'] = 'Pass --full-views for timeline/list paging and full-dataset search.'
                exercise_calendar(page, baseline, report, include_full_views)
                if not include_full_views:
                    measure('list_from_calendar', lambda: select_view(page, 'list'), report)
                report['checks'].append('calendar-bounded-rendering' + ('-tail-search-and-section-paging' if include_full_views else ''))
                after_views = database_summary(page)
                assert after_views == before_views, 'Read-only view/search/pagination changed tasks, revision or subtasks'
                report['checks'].append('view-navigation-and-search-task-data-read-only')
                final_backup = measure('final_json_export', lambda: exercise_export_backup(page), report)
                assert final_backup['tasks'] == baseline, 'Final real JSON backup lost task fields or repeat links'
                assert not report['page_errors'], report['page_errors']
                report['checks'].append('final-real-json-download-checksum-and-exact-task-fields')
                report['assertions_passed'] = True
                report['status'] = 'passed'
                report['completed'] = True
                report['passed'] = True
            finally:
                context.close()
                browser.close()
    except BaseException as error:
        caught = error
        report['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['completed'] = False
        report['passed'] = False
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        print(f'Workspace operation failed: {type(error).__name__}: {error}', flush=True)
        raise
    finally:
        report['finished_at'] = timestamp()
        for key, capture in [('source', source_identity), ('tool_inputs', tool_identity)]:
            try:
                report[key + '_final'] = capture()
            except Exception as identity_error:
                report['integrity_errors'].append(f'Final {key} identity failed: {type(identity_error).__name__}: {identity_error}')
            report[key + '_unchanged'] = report[key] is not None and report[key] == report[key + '_final']
            if report[key] is None:
                report['integrity_errors'].append(f'Initial {key} identity was unavailable.')
            elif not report[key + '_unchanged']:
                report['integrity_errors'].append(f'{key} inputs changed during this run.')
        if report['integrity_errors']:
            report['passed'] = False
            if report['status'] == 'passed':
                report['status'] = 'failed'
        write_report(output, report)
        print(json.dumps({key: value for key, value in report.items()
                          if key not in ('source', 'source_final', 'tool_inputs', 'tool_inputs_final')},
                         ensure_ascii=False), flush=True)
        if report['integrity_errors'] and caught is None:
            raise AssertionError('; '.join(report['integrity_errors']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=1000)
    parser.add_argument('--subtasks', type=int, default=6)
    parser.add_argument('--full-views', action='store_true', help='Also probe unfiltered batch mode and list/timeline/calendar paging and full-dataset search')
    parser.add_argument('--output', type=Path, help='New JSON result path; existing evidence is never overwritten')
    args = parser.parse_args()
    if not 1 <= args.size <= 10000 or not 0 <= args.subtasks <= 20:
        parser.error('Use 1..10000 tasks and 0..20 subtasks per task')
    run(args.size, args.subtasks, args.full_views, args.output)
