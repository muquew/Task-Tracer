#!/usr/bin/env python3
"""Measure repeatable full-workspace UI operations with explicit CPU conditions."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import tempfile
import time
import uuid

from playwright.sync_api import expect, sync_playwright

from check import atomic_report, identity, source_identity
from recovery_playwright import open_recovery
from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task, assert_backup_payload_integrity, browser_launch_options, clear_app_data,
    delete_task, local_server, select_filter, select_view, task_locator,
    wait_for_app_ready,
)

ROOT = Path(__file__).resolve().parents[1]
CLOCK = datetime(2039, 1, 1, 12, tzinfo=timezone.utc)
TOOLS = ['tools/workspace_performance_playwright.py', 'tools/check.py',
         'tools/smoke_playwright.py', 'tools/recovery_playwright.py',
         'tools/build_release.py', 'tools/validate_static.py']
BUDGETS = {'reload_list': 15000, 'list_tail_search': 5000}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def fingerprint(tasks):
    encoded = json.dumps(tasks, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def seed(page, size, subtasks, template, history_points):
    """Test setup only: install one fixed fixture before measured UI actions."""
    page.evaluate("""({size, subtasks, template, historyPoints}) => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const store = tx.objectStore('tasks');
            const config = tx.objectStore('config');
            store.clear(); config.clear();
            const fixtures = [];
            for (let i = 0; i < size; i++) {
                const id = i === 0 ? 0 : 100000 + i;
                const linked = i < 3 && size >= 3;
                const dated = linked || i % 4 !== 0;
                const day = linked ? i + 2 : i % 27 + 2;
                const key = dated ? `2039-01-${String(day).padStart(2, '0')}` : null;
                const instant = key ? `${key}T12:30:00.000Z` : null;
                const task = {...template, id,
                    name: `Controlled task ${String(i).padStart(5, '0')} 中文`,
                    description: `Synthetic record ${i}: commas, "quotes", 🧭.\\r\\n  Retain indentation.`,
                    project: `Project ${i % 10}`, tags: ['controlled', `tag${i % 20}`],
                    createdAt: '2038-12-01T00:00:00.000Z', order: i * 1000,
                    archived: false, archivedAt: null, focusDate: null,
                    completed: linked && i < 2,
                    completedAt: linked && i < 2 ? '2038-12-31T12:00:00.000Z' : null,
                    dueDate: instant, dueAt: instant, dueLocalDate: key,
                    dueLocalTime: dated ? '12:30' : null, dueTimeZone: dated ? 'UTC' : null,
                    reminderOffset: -1, reminderRepeat: -1,
                    repeatType: linked ? 'daily' : 'none', repeatInterval: 1,
                    repeatPaused: false, repeatSourceId: linked ? 0 : null,
                    repeatCreatedFrom: linked && i > 0 ? (i === 1 ? 0 : 100001) : null,
                    nextRepeatTaskId: linked && i < 2 ? 100001 + i : null,
                    subtasks: Array.from({length: subtasks}, (_, n) => ({
                        id: (100000 + i) * 100 + n,
                        text: `Checklist ${i}/${n} 中文`, completed: n % 3 === 0
                    }))};
                fixtures.push(task); store.put(task);
            }
            const history = Array.from({length: historyPoints}, (_, n) => ({
                id: `controlled-history-${n}`,
                createdAt: new Date(Date.UTC(2039, 0, 1, 12) - n * 60000).toISOString(),
                tasks: fixtures.map(task => structuredClone(task))
            }));
            for (const entry of [
                {key: 'sampleTasksAdded', value: true}, {key: 'language', value: 'en'},
                {key: 'notifications_enabled', value: false},
                {key: 'taskRevision', value: 2}, {key: 'recoveryHistory', value: history}
            ]) config.put(entry);
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", {'size': size, 'subtasks': subtasks, 'template': template,
             'historyPoints': history_points})


def summary(page, focus_value=None, edit=None):
    return page.evaluate("""async ({focusValue, edit}) => {
        const data = await new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(['tasks', 'config']);
                const tasks = tx.objectStore('tasks').getAll();
                const history = tx.objectStore('config').get('recoveryHistory');
                const revision = tx.objectStore('config').get('taskRevision');
                tx.oncomplete = () => {db.close(); resolve({tasks: tasks.result,
                    history: history.result?.value || [], revision: revision.result?.value});};
                tx.onabort = () => reject(tx.error);
            };
        });
        const digest = async rows => {
            const canonical = JSON.stringify(rows, (key, value) => {
                if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
                return Object.fromEntries(Object.keys(value).sort().map(key => [key, value[key]]));
            });
            const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical));
            return Array.from(new Uint8Array(buffer), x => x.toString(16).padStart(2, '0')).join('');
        };
        const points = [];
        for (const point of data.history) points.push({id: point.id, count: point.tasks.length,
            signature: await digest(point.tasks)});
        const ids = new Set(data.tasks.map(task => task.id));
        return {count: data.tasks.length, signature: await digest(data.tasks),
            normalized_focus_signature: focusValue === null ? null :
                await digest(data.tasks.map(task => ({...task, focusDate: focusValue}))),
            edited_signature: edit === null ? null : await digest(data.tasks.map(task =>
                task.id === edit.id ? {...task, description: edit.description} : task)),
            revision: data.revision, history: points,
            subtasks: data.tasks.reduce((sum, task) => sum + task.subtasks.length, 0),
            focused: data.tasks.filter(task => task.focusDate === '2039-01-01').length,
            valid_repeat_references: data.tasks.every(task =>
                [task.repeatSourceId, task.repeatCreatedFrom, task.nextRepeatTaskId]
                .every(id => id === null || id === undefined || ids.has(id)))};
    }""", {'focusValue': focus_value, 'edit': edit})


def observation(page, session):
    metrics = {entry['name']: entry['value']
               for entry in session.send('Performance.getMetrics')['metrics']}
    counters = session.send('Memory.getDOMCounters')
    return {
        'js_heap_used_bytes': metrics.get('JSHeapUsedSize'),
        'js_heap_total_bytes': metrics.get('JSHeapTotalSize'),
        'browser_dom_counters': counters,
        'connected_dom': page.evaluate("""() => ({
            elements: document.querySelectorAll('*').length,
            task_cards: document.querySelectorAll('.task-item').length,
            calendar_preview_buttons: document.querySelectorAll('.calendar-task').length,
            calendar_detail_items: document.querySelectorAll('.calendar-detail-task').length,
            selected_checkboxes: document.querySelectorAll('.task-select-checkbox:checked').length
        })"""),
    }


def export_download(page):
    page.locator('#openMenuBtn').click()
    with page.expect_download() as pending:
        page.locator('#backupBtn').click()
    download = pending.value
    path = download.path()
    assert path, 'No completed backup download'
    return Path(path)


def replace_from_file(page, path):
    page.locator('#openMenuBtn').click()
    with page.expect_file_chooser() as pending:
        page.locator('#importBtn').click()
    pending.value.set_files(path)
    expect(page.locator('#mergeImportMode')).to_be_visible()
    expect(page.locator('.import-conflict-select')).to_have_count(0)
    with page.expect_download() as pending:
        page.locator('#submitBtn').click()
    snapshot = pending.value.path()
    assert snapshot, 'Replacement did not produce a completed safety snapshot'
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    return Path(snapshot)


def run_once(browser, url, args, report, publish, number):
    context = browser.new_context(accept_downloads=True, locale='en-US', timezone_id='UTC',
                                  viewport={'width': args.width, 'height': args.height},
                                  reduced_motion='reduce')
    record = {'run': number, 'status': 'running', 'measurements': []}
    report['runs'].append(record)
    page = context.new_page()
    page.set_default_timeout(args.timeout_ms)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.clock.set_fixed_time(CLOCK)
    session = context.new_cdp_session(page)
    session.send('Performance.enable')
    try:
        clear_app_data(page, url)
        add_task(page, 'Controlled fixture seed', no_deadline=True)
        template = page.evaluate("""() => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('tasks');
                const all = tx.objectStore('tasks').getAll();
                tx.oncomplete = () => {db.close(); resolve(all.result[0]);};
                tx.onabort = () => reject(tx.error);
            };
        })""")

        def reset():
            session.send('Emulation.setCPUThrottlingRate', {'rate': 1})
            seed(page, args.size, args.subtasks, template, args.history_points)
            session.send('Emulation.setCPUThrottlingRate', {'rate': args.cpu_rate})
            page.reload()
            wait_for_app_ready(page)
            expect(page.locator('.task-item')).to_have_count(min(args.size - 2, 100))
            select_filter(page, 'all')
            expect(page.locator('.task-item')).to_have_count(min(args.size, 100))
            current = summary(page)
            assert current['count'] == args.size and current['subtasks'] == args.size * args.subtasks
            assert current['valid_repeat_references'], 'Invalid recurrence relationship in fixture'
            if 'fixture' not in record:
                record['fixture'] = current
            else:
                assert current['signature'] == record['fixture']['signature'], 'Fixture changed between measured operations'
            return current

        def measure(name, operation):
            item = {'operation': name, 'status': 'running',
                    'budget_ms': BUDGETS.get(name),
                    'budget_scope': 'existing regression ceiling' if name in BUDGETS else 'baseline_only'}
            record['measurements'].append(item)
            report['current_operation'] = {'run': number, 'operation': name}
            publish()
            started = time.perf_counter()
            try:
                result = operation()
                elapsed = round((time.perf_counter() - started) * 1000, 1)
                item.update({'duration_ms': elapsed, 'status': 'passed',
                             'observation_after': observation(page, session)})
                if name in BUDGETS:
                    item['budget_passed'] = elapsed <= BUDGETS[name]
                    assert item['budget_passed'], f'{name} exceeded existing {BUDGETS[name]} ms regression budget: {elapsed} ms'
                print(f'run {number} {name}: {elapsed} ms', flush=True)
                publish()
                return result
            except BaseException as error:
                item.setdefault('duration_ms', round((time.perf_counter() - started) * 1000, 1))
                item.update({'status': 'failed', 'error': f'{type(error).__name__}: {error}'})
                publish()
                raise

        baseline = reset()
        target = f'Controlled task {args.size - 1:05d} 中文'

        edited_description = 'Explicit controlled description edit; every other field stays intact.'
        expected_edit_signature = summary(page, edit={
            'id': 100000 + args.size - 1, 'description': edited_description})['edited_signature']
        page.locator('#searchInput').fill(target)
        expect(task_locator(page, target)).to_have_count(1)
        click_task_action(task_locator(page, target), 'edit')
        page.locator('#taskDesc').fill(edited_description)
        def save_single_edit():
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            expect(task_locator(page, target).locator('.task-desc')).to_contain_text('Explicit controlled description edit')
        measure('single_edit_save', save_single_edit)
        edited = summary(page)
        assert edited['count'] == baseline['count'] and edited['revision'] == baseline['revision'] + 1
        assert edited['signature'] == expected_edit_signature, 'Single edit changed an unrelated task field'
        assert edited['valid_repeat_references']
        if args.history_points:
            assert edited['history'] == baseline['history'], 'An ordinary write changed recent recovery snapshots'
        else:
            assert edited['history'][0]['signature'] == baseline['signature'], 'First write did not checkpoint the full original workspace'
        if args.history_edit_only:
            assert not errors, errors
            record.update({'status': 'passed', 'page_errors': errors})
            publish()
            return
        reset()

        def reload_list():
            page.reload()
            wait_for_app_ready(page)
            expect(page.locator('.task-item')).to_have_count(min(args.size - 2, 100))
        measure('reload_list', reload_list)
        select_filter(page, 'all')
        expect(page.locator('.task-item')).to_have_count(min(args.size, 100))

        def search():
            page.locator('#searchInput').fill(target)
            expect(task_locator(page, target)).to_have_count(1)
            expect(page.locator('.task-item')).to_have_count(1)
        measure('list_tail_search', search)
        page.locator('#searchInput').fill('')
        expect(page.locator('.task-item')).to_have_count(min(args.size, 100))

        def timeline():
            select_view(page, 'timeline')
            expect(page.locator('.timeline-view .task-item')).to_have_count(min(args.size, 100))
        measure('timeline', timeline)
        def calendar():
            select_view(page, 'calendar')
            expect(page.locator('.calendar-title')).to_contain_text('2039')
            expect(page.locator('.calendar-title')).to_contain_text('January')
            days = {}
            for index in range(args.size):
                if index < 3 or index % 4:
                    day = index + 2 if index < 3 else index % 27 + 2
                    days[day] = days.get(day, 0) + 1
            expect(page.locator('.calendar-task')).to_have_count(sum(min(3, count) for count in days.values()))
            expect(page.locator('.date-view-undated .task-item')).to_have_count(min(100, (args.size + 3) // 4 - 1))
        measure('calendar', calendar)
        assert summary(page)['signature'] == baseline['signature'], 'Read-only views changed task fields'

        reset()
        expected_focus_signature = summary(page, focus_value='2039-01-01')['normalized_focus_signature']
        def enter_batch():
            page.locator('#batchModeBtn').click()
            expect(page.locator('#batchModeBtn')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('.task-item')).to_have_count(min(100, args.size))
        measure('batch_enter_bounded_workspace', enter_batch)
        def select_all():
            page.locator('#batchSelectVisibleBtn').click()
            expect(page.locator('.task-select-checkbox:checked')).to_have_count(min(100, args.size))
            expect(page.locator('#batchSelectionSummary')).to_contain_text(str(args.size))
        measure('batch_select_all_matching', select_all)
        if args.size > 100:
            def batch_more():
                page.locator('#loadMoreTasksBtn').click()
                expect(page.locator('.task-item')).to_have_count(min(200, args.size))
                expect(page.locator('.task-select-checkbox:checked')).to_have_count(min(200, args.size))
                expect(page.locator('#batchSelectionSummary')).to_contain_text(str(args.size))
            measure('batch_load_more_selected', batch_more)
        def focus_batch():
            page.locator('#batchFocusBtn').click()
            expect(page.locator('#undoBtn')).to_be_enabled()
            expect(page.locator('.task-select-checkbox:checked')).to_have_count(0)
        measure('batch_focus_full_workspace', focus_batch)
        changed = summary(page, focus_value=None)
        assert changed['focused'] == args.size, 'Batch focus did not update the complete workspace'
        assert changed['signature'] == expected_focus_signature, 'Batch focus changed an unrelated task field'
        assert changed['revision'] == baseline['revision'] + 1
        def undo_batch():
            page.locator('#undoBtn').click()
            expect(page.locator('#undoBtn')).to_be_disabled()
            expect(page.locator('#notificationText')).to_contain_text('Undone')
        measure('batch_undo', undo_batch)
        assert summary(page)['signature'] == baseline['signature'], 'Undo did not restore every original field'

        reset()
        backup_path = measure('json_export_download', lambda: export_download(page))
        backup = json.loads(backup_path.read_text())
        assert_backup_payload_integrity(backup, 'backup')
        assert fingerprint(backup['tasks']) == baseline['signature'], 'Downloaded JSON changed full task fields'
        record['export_file_bytes'] = backup_path.stat().st_size
        with tempfile.TemporaryDirectory(prefix='task-tracer-controlled-import-') as folder:
            source = Path(folder) / 'backup.json'
            source.write_bytes(backup_path.read_bytes())
            reset()
            snapshot_path = measure('json_replace_import', lambda: replace_from_file(page, source))
            snapshot = json.loads(snapshot_path.read_text())
            assert_backup_payload_integrity(snapshot, 'pre-import-backup')
            assert fingerprint(snapshot['tasks']) == baseline['signature']
        assert summary(page)['signature'] == baseline['signature'], 'Replacement import changed full task fields'

        reset()
        page.locator('#searchInput').fill(target)
        expect(task_locator(page, target)).to_have_count(1)
        measure('checkpoint_delete', lambda: delete_task(page, target))
        deleted = summary(page)
        assert deleted['count'] == args.size - 1
        point = next(item for item in deleted['history'] if item['signature'] == baseline['signature'])
        def restore():
            open_recovery(page)
            page.locator('#recoverySelect').select_option(str(point['id']), force=True)
            page.locator('#recoveryConfirm').check()
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            expect(task_locator(page, target)).to_have_count(1)
        measure('checkpoint_restore', restore)
        assert summary(page)['signature'] == baseline['signature'], 'Checkpoint restore changed full task fields'
        assert not errors, errors
        record.update({'status': 'passed', 'page_errors': errors})
        publish()
    except BaseException:
        record.update({'status': 'failed', 'page_errors': errors})
        raise
    finally:
        context.close()


def run(args):
    expect.set_options(timeout=args.timeout_ms)
    report = {
        'schema_version': 1, 'run_id': str(uuid.uuid4()), 'started_at': timestamp(),
        'status': 'initializing', 'completed': False, 'passed': False,
        'current_operation': None, 'runs': [], 'source': None,
        'measurement_tools': None, 'integrity_errors': [],
        'conditions': {
            'tasks': args.size, 'subtasks_per_task': args.subtasks,
            'viewport': {'width': args.width, 'height': args.height},
            'cpu_throttle_rate': args.cpu_rate, 'runs_requested': args.runs,
            'history_points': args.history_points,
            'newest_history_created_at': CLOCK.isoformat() if args.history_points else None,
            'history_edit_policy': 'Populated history has a current newest point; ordinary edit should not create another checkpoint inside its interval.',
            'coverage': 'single edit only' if args.history_edit_only else 'views, full-workspace batch, download/import and checkpoint recovery',
            'timezone': 'UTC', 'locale': 'en-US', 'fixed_clock': CLOCK.isoformat(),
            'fixture_seed_cpu_throttle_rate': 1,
            'reload_readiness_scope': 'Default active filter excludes the two completed recurrence ancestors; remaining phases explicitly select all tasks.',
            'calendar_scope': 'Clock fixed to January 2039; transition includes visible month, exact dated preview count and bounded undated-card readiness, without month-navigation setup.',
            'measurement_type': 'smoke' if args.smoke else 'controlled synthetic cloud run',
            'host_platform': platform.platform(),
            'budgets': {'reference': 'tools/performance_playwright.py; docs/performance.md',
                        'ceilings_ms': BUDGETS,
                        'scope': 'Existing generous list load/search ceilings applied unchanged to this heavier controlled workload. Other operations are baseline-only.'},
            'limitations': [
                'CPU throttling and narrow viewports do not reproduce real mobile hardware.',
                'Elapsed operation times include browser-driver/UI work; fixture setup and full-field signature verification are outside timings.',
                'Heap and DOM samples are observations after operations, not peak memory, process RSS or a memory budget.',
                'Fixture injection and integrity checks allocate JavaScript data outside measured intervals; their transient allocations may affect heap observations and collection.',
                'Each repetition uses a fresh browser context; repeated operations within it are warm-cache observations.',
                'Batch mode renders bounded pages; Select all matching acts on the complete match set including unloaded tasks.',
            ],
        },
    }
    def publish():
        if args.output:
            atomic_report(args.output, report)
    def capture_final():
        for kind, capture in [('source', source_identity), ('measurement_tools', lambda: identity(TOOLS))]:
            try:
                report[kind + '_final'] = capture()
                report[kind + '_unchanged'] = report[kind] is not None and report[kind] == report[kind + '_final']
                if not report[kind + '_unchanged']:
                    message = f'{kind} inputs changed or were not captured at initialization'
                    if message not in report['integrity_errors']:
                        report['integrity_errors'].append(message)
            except Exception as error:
                report[kind + '_final'] = None
                report[kind + '_unchanged'] = False
                message = f'{kind} final capture failed: {type(error).__name__}: {error}'
                if message not in report['integrity_errors']:
                    report['integrity_errors'].append(message)
    publish()
    try:
        report['source'] = source_identity()
        report['measurement_tools'] = identity(TOOLS)
        report['status'] = 'running'
        publish()
        with local_server() as url, sync_playwright() as p:
            browser = p.chromium.launch(**browser_launch_options())
            report['browser_engine'] = 'chromium'
            report['browser_version'] = browser.version
            try:
                for number in range(1, args.runs + 1):
                    run_once(browser, url, args, report, publish, number)
            finally:
                browser.close()
        capture_final()
        assert report['source_unchanged'] and report['measurement_tools_unchanged'], 'Measurement inputs changed during the run'
        signatures = {item['fixture']['signature'] for item in report['runs']}
        assert len(signatures) == 1, 'Independent runs did not use exactly the same fixture'
        operations = [item['operation'] for item in report['runs'][0]['measurements']]
        report['aggregate'] = {}
        for operation in operations:
            values = [next(item['duration_ms'] for item in run['measurements'] if item['operation'] == operation)
                      for run in report['runs']]
            report['aggregate'][operation] = {'samples_ms': values,
                'min_ms': min(values), 'median_ms': statistics.median(values), 'max_ms': max(values),
                'budget_ms': BUDGETS.get(operation),
                'interpretation': 'existing regression ceiling passed' if operation in BUDGETS else 'baseline_only'}
        report.update({'status': 'passed', 'completed': True, 'passed': True,
                       'current_operation': None, 'finished_at': timestamp()})
        publish()
        print(json.dumps({'passed': True, 'runs': len(report['runs']), 'tasks': args.size,
                          'cpu_rate': args.cpu_rate, 'viewport_width': args.width,
                          'source_sha256': report['source']['sha256']}, ensure_ascii=False), flush=True)
    except BaseException as error:
        report.update({'status': 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                       'completed': False, 'passed': False, 'finished_at': timestamp(),
                       'error': f'{type(error).__name__}: {error}'})
        capture_final()
        publish()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=10000)
    parser.add_argument('--subtasks', type=int, default=6)
    parser.add_argument('--cpu-rate', type=float, default=4)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--timeout-ms', type=int, default=120000)
    parser.add_argument('--history-points', type=int, default=0)
    parser.add_argument('--history-edit-only', action='store_true', help='Measure only one task save against the specified populated recovery history')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true', help='Allow fewer than three runs; explicitly marks report as smoke evidence')
    args = parser.parse_args()
    if not 4 <= args.size <= 10000 or not 0 <= args.subtasks <= 20:
        parser.error('Use 4..10000 tasks and 0..20 subtasks')
    if not 1 <= args.cpu_rate <= 16 or args.runs < (1 if args.smoke else 3):
        parser.error('Use CPU rate 1..16 and at least three runs (or --smoke for development)')
    if args.width < 320 or args.height < 320 or args.timeout_ms < 15000:
        parser.error('Viewport must be at least 320×320; timeout must be at least 15000ms')
    if not 0 <= args.history_points <= 10:
        parser.error('History points must be within the actual 0..10 retention limit')
    if args.output.exists():
        parser.error('Output already exists; use a new path to preserve earlier evidence')
    run(args)
