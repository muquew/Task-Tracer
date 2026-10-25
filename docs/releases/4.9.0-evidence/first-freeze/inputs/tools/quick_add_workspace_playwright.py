#!/usr/bin/env python3
"""Verify 10,000-task / 60,000-subtask quick-add recovery and record the actual source."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / 'tools'))

from playwright.sync_api import expect, sync_playwright
from quick_add_recovery_playwright import RAW_NAME, RAW_TEXT, assert_retained_readonly, assert_same_document, mark_document
from smoke_playwright import add_task, browser_launch_options, clear_app_data, exercise_export_backup, local_server, task_locator, wait_for_app_ready
from task_draft_playwright import inject_quota_failure, unload_is_guarded
from validate_static import app_version, resource_version
from workspace_roundtrip_playwright import fingerprint


SUMMARY = """async saveBaseline => {
    const data = await new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => { db.close(); resolve({tasks: tasks.result, config: config.result}); };
            tx.onabort = () => reject(tx.error);
        };
    });
    const canonical = value => JSON.stringify(value, (key, item) => {
        if (!item || typeof item !== 'object' || Array.isArray(item)) return item;
        return Object.fromEntries(Object.keys(item).sort().map(name => [name, item[name]]));
    });
    const digest = async value => {
        const raw = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(value)));
        return Array.from(new Uint8Array(raw), byte => byte.toString(16).padStart(2, '0')).join('');
    };
    if (saveBaseline) window.largeQuickAddBaseline = data;
    const baseline = window.largeQuickAddBaseline;
    const originalIds = new Set(baseline.tasks.map(task => task.id));
    const originals = data.tasks.filter(task => originalIds.has(task.id));
    const latestById = new Map(data.tasks.map(task => [task.id, task]));
    const changedIds = baseline.tasks.filter(task => canonical(latestById.get(task.id)) !== canonical(task)).map(task => task.id);
    const getConfig = (records, key) => records.find(item => item.key === key)?.value;
    const history = getConfig(data.config, 'recoveryHistory') || [];
    const oldHistory = getConfig(baseline.config, 'recoveryHistory') || [];
    const historyById = new Map(history.map(point => [point.id, point]));
    return {
        tasks: data.tasks.length,
        subtasks: data.tasks.reduce((sum, task) => sum + task.subtasks.length, 0),
        tasks_sha256: await digest(data.tasks),
        config_sha256: await digest(data.config),
        history_sha256: await digest(history),
        history_points: history.length,
        history_task_counts: history.map(point => point.tasks.length),
        revision: getConfig(data.config, 'taskRevision'),
        unchanged_original_records: baseline.tasks.length - changedIds.length,
        changed_original_ids: changedIds,
        original_tasks_sha256: await digest(originals),
        non_task_mutation_config_sha256: await digest(data.config.filter(item => !['taskRevision', 'recoveryHistory'].includes(item.key))),
        prior_history_records_preserved: oldHistory.every(point => canonical(historyById.get(point.id)) === canonical(point)),
        added: data.tasks.filter(task => !originalIds.has(task.id))
    };
}"""


def seed_expression():
    source = (REPOSITORY / 'tools/workspace_roundtrip_playwright.py').read_text()
    run = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'run')
    matches = [node.args[0].value for node in ast.walk(run)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr == 'evaluate' and node.args
               and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
               and 'subtaskCount' in node.args[0].value and 'store.put' in node.args[0].value]
    assert len(matches) == 1, 'Existing workload seed expression was not located exactly once'
    return matches[0]


def assert_identical(before, after, phase):
    for key in ('tasks', 'subtasks', 'tasks_sha256', 'config_sha256', 'history_sha256', 'revision'):
        assert after[key] == before[key], f'{phase} changed {key}: {before[key]} -> {after[key]}'
    assert after['changed_original_ids'] == [], f'{phase} changed original task records'
    assert after['added'] == [], f'{phase} unexpectedly created task records'


def run(output: Path, expected_app: str | None = None, expected_resource: str | None = None):
    started = time.perf_counter()
    index = (REPOSITORY / 'index.html').read_text()
    app = app_version(index)
    resource = resource_version(index)
    if expected_app is not None:
        assert app == expected_app, f'Expected app {expected_app}, found {app}'
    if expected_resource is not None:
        assert resource == expected_resource, f'Expected resources {expected_resource}, found {resource}'
    report = {
        'app_version': app,
        'resource_version': resource,
        'index_sha256': hashlib.sha256(index.encode()).hexdigest(),
        'database_version': 2,
        'task_file_version': '2.4',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'concurrency': 'Other final checks may have run concurrently. Single synthetic cloud-browser exercise; no comparative, memory, speed, or device guarantee.',
        'requested_tasks': 10000,
        'subtasks_per_original_task': 6,
        'scope_passed': []
    }
    expect.set_options(timeout=45000)
    with local_server() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
        page = context.new_page()
        page.set_default_timeout(45000)
        page_errors = []
        downloads = []
        page.on('pageerror', lambda error: page_errors.append(str(error)))
        page.on('download', lambda download: downloads.append(download))
        report['browser'] = browser.version
        try:
            clear_app_data(page, url)
            add_task(page, 'Workspace seed', no_deadline=True)
            page.evaluate(seed_expression(), {'size': 10000, 'subtaskCount': 6})
            page.reload()
            wait_for_app_ready(page)
            expect(page.locator('.task-item')).to_have_count(100)
            page.locator('#searchInput').fill('Workspace task 00000 中文')
            first = task_locator(page, 'Workspace task 00000 中文')
            first.locator('[data-action="toggle"]').click()
            expect(first).to_have_count(0)
            page.locator('#searchInput').fill('')
            expect(page.locator('.task-item')).to_have_count(100)
            mark_document(page)
            baseline = page.evaluate(SUMMARY, True)
            assert baseline['tasks'] == 10000 and baseline['subtasks'] == 60000
            assert 10000 in baseline['history_task_counts'], 'Baseline has no actual populated 10k recovery point'
            assert baseline['revision'] >= 2
            report['baseline'] = baseline
            report['scope_passed'].append('existing workload seed: 10,000 tasks / 60,000 subtasks; actual committed mutation creates a nonempty 10k recovery point')
            print(f'Prepared {app} with 10,000 tasks, 60,000 subtasks and a populated recovery history', flush=True)

            page.evaluate("""() => {
                const original = IDBDatabase.prototype.transaction;
                window.largeQuickAddTaskWriteAborts = 0;
                window.largeQuickAddTaskWriteCommits = 0;
                IDBDatabase.prototype.transaction = function(...args) {
                    const tx = original.apply(this, args);
                    if (tx.mode === 'readwrite' && Array.from(tx.objectStoreNames).includes('tasks')) {
                        tx.addEventListener('abort', () => { window.largeQuickAddTaskWriteAborts += 1; });
                        tx.addEventListener('complete', () => { window.largeQuickAddTaskWriteCommits += 1; });
                    }
                    return tx;
                };
            }""")
            page.locator('#quickAddInput').fill(RAW_TEXT)
            inject_quota_failure(page)
            page.locator('#quickAddInput').press('Enter')
            expect(page.locator('#storageUnavailableBanner')).to_be_visible()
            assert_retained_readonly(page)
            page.wait_for_function('window.largeQuickAddTaskWriteAborts === 1')
            aborted = page.evaluate(SUMMARY, False)
            assert_identical(baseline, aborted, 'Quota abort')
            assert page.evaluate('window.largeQuickAddTaskWriteCommits') == 0
            report['after_quota_abort'] = aborted
            report['scope_passed'].append('one genuine tasks.add QuotaExceededError transaction abort; raw quick-add text remains enabled, selectable and readonly; all original task fields plus entire config/revision/populated history unchanged')

            page.locator('#retryStorageBtn').click()
            expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
            wait_for_app_ready(page)
            assert_same_document(page)
            field = page.locator('#quickAddInput')
            expect(field).to_have_value(RAW_TEXT)
            expect(field).not_to_have_attribute('readonly', '')
            expect(page.locator('#quickAddForm button[type="submit"]')).to_be_enabled()
            assert unload_is_guarded(page)
            retried = page.evaluate(SUMMARY, False)
            assert_identical(baseline, retried, 'Same-document Retry')
            assert page.evaluate('window.largeQuickAddTaskWriteCommits') == 0
            report['after_same_document_retry'] = retried
            report['scope_passed'].append('same-document Retry retains exact raw text, restores editability, performs zero task writes and leaves complete config/revision/history unchanged')
            print('Quota abort and same-document Retry preserved complete task and config/history signatures', flush=True)

            field.press('Enter')
            expect(field).to_have_value('')
            expect(page.locator('#quickAddForm button[type="submit"]')).to_be_enabled()
            after = page.evaluate(SUMMARY, False)
            assert after['tasks'] == 10001 and len(after['added']) == 1
            assert after['unchanged_original_records'] == 10000 and after['changed_original_ids'] == []
            assert after['original_tasks_sha256'] == baseline['tasks_sha256']
            assert after['revision'] == baseline['revision'] + 1
            assert after['non_task_mutation_config_sha256'] == baseline['non_task_mutation_config_sha256']
            assert after['prior_history_records_preserved']
            added = after['added'][0]
            assert added['name'] == RAW_NAME and added['description'] == ''
            assert added['project'] == '个人' and added['tags'] == ['待办']
            assert added['dueLocalTime'] == '20:00'
            assert page.evaluate('window.largeQuickAddTaskWriteAborts') == 1
            assert page.evaluate('window.largeQuickAddTaskWriteCommits') == 1
            assert not unload_is_guarded(page)
            report['after_explicit_resubmit'] = after
            report['scope_passed'].append('one explicit resubmit adds exactly one parsed task, advances revision once, preserves every field of all 10,000 originals and every prior recovery point')

            backup = exercise_export_backup(page)
            export_signature = fingerprint(backup['tasks'])
            assert len(backup['tasks']) == 10001 and export_signature == after['tasks_sha256']
            originals = [task for task in backup['tasks'] if 100000 <= task['id'] < 110000]
            assert len(originals) == 10000 and fingerprint(originals) == baseline['tasks_sha256']
            assert next(task for task in backup['tasks'] if task['id'] == added['id']) == added
            exported_db = page.evaluate(SUMMARY, False)
            assert exported_db['tasks_sha256'] == after['tasks_sha256']
            assert exported_db['changed_original_ids'] == []
            report['export'] = {'tasks': len(backup['tasks']), 'file_bytes': downloads[-1].path().stat().st_size, 'tasks_sha256': export_signature, 'all_original_records_unchanged': True, 'added_task_exact_match': True}
            report['scope_passed'].append('actual downloaded JSON backup passes existing metadata/checksum assertions and full-field SHA checks for all 10,001 tasks, including exact new task and every original record')
            assert not page_errors, page_errors
            assert hashlib.sha256((REPOSITORY / 'index.html').read_bytes()).hexdigest() == report['index_sha256'], 'Application source changed during the workload'
            report['page_errors'] = page_errors
            report['passed'] = True
            report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
            report['completed_at'] = datetime.now(timezone.utc).isoformat()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps(report, ensure_ascii=False), flush=True)
        except Exception as error:
            print(f'FAILED: {type(error).__name__}: {error}', flush=True)
            print('Page errors:', page_errors, flush=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-quick-add-10000.json'))
    parser.add_argument('--expect-app-version', help='Refuse a workload against a different application version')
    parser.add_argument('--expect-resource-version', help='Refuse a workload against a different translation version')
    args = parser.parse_args()
    run(args.output, args.expect_app_version, args.expect_resource_version)
