#!/usr/bin/env python3
"""Check full-workspace rollback and explicit recovery after injected write failures."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

from playwright.sync_api import expect, sync_playwright

from check import atomic_report, source_identity
from recovery_management_playwright import config, stored
from recovery_playwright import open_recovery
from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, local_server,
    task_locator, wait_for_app_ready,
)
from task_draft_playwright import downloaded_drafts, unload_is_guarded


ROOT = Path(__file__).resolve().parents[1]
FIRST = 'Failure workspace 00000 中文'
DRAFT_NAME = 'Recovered full-workspace form draft'
RAW_QUICK = 'Recovered full-workspace quick draft #retained /Recovery'


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def assert_equal(actual, expected, message):
    assert actual == expected, f'{message}; expected={digest(expected)}, actual={digest(actual)}'


def prepare(page, url, size, subtasks):
    clear_app_data(page, url)
    add_task(page, 'Failure workspace seed', no_deadline=True)
    page.evaluate("""({size, subtasks}) => new Promise((resolve, reject) => {
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
                const examples = [];
                for (let i = 0; i < size; i++) {
                    const dated = i % 3 !== 0;
                    const day = String(1 + i % 28).padStart(2, '0');
                    const due = dated ? `2032-05-${day}T12:30:00.000Z` : null;
                    const task = {...template, id: 100000 + i,
                        name: `Failure workspace ${String(i).padStart(5, '0')} 中文`,
                        description: `Synthetic entry ${i}: comma, \"quote\"\\n第二行`,
                        project: `Project ${i % 10}`, tags: ['workspace', `tag${i % 20}`],
                        dueDate: due, dueAt: due,
                        dueLocalDate: dated ? `2032-05-${day}` : null,
                        dueLocalTime: dated ? '12:30' : null, dueTimeZone: dated ? 'UTC' : null,
                        reminderOffset: -1, reminderRepeat: -1,
                        repeatType: 'none', repeatInterval: 1, repeatWeekdays: [],
                        repeatSourceId: null, nextRepeatTaskId: null, repeatCreatedFrom: null,
                        order: i * 1000,
                        subtasks: Array.from({length:subtasks}, (_, index) => ({
                            id:(100000+i)*100+index, text:`Subtask ${index} 中文`, completed:index % 3 === 0
                        }))};
                    store.put(task);
                    if (i < 3) examples.push(task);
                }
                const settings = tx.objectStore('config');
                settings.put({key:'recoveryHistory',value:[{
                    id:'workspace-failure-old',createdAt:'2001-01-01T00:00:00.000Z',tasks:examples
                }]});
                settings.put({key:'workspaceFailurePreference',value:{keep:'untouched sentinel 中文'}});
                const revision = settings.get('taskRevision');
                revision.onsuccess = () => {
                    const date = new Date().toISOString();
                    settings.put({key:'lastBackupAt',value:date});
                    settings.put({key:'lastTaskBackup',value:{date,taskRevision:revision.result.value}});
                };
            };
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => {db.close(); reject(tx.error);};
        };
    })""", {'size': size, 'subtasks': subtasks})
    page.reload()
    wait_for_app_ready(page)
    expect(page.locator('.task-item')).to_have_count(min(size, 100))
    baseline = stored(page)
    assert len(baseline['tasks']) == size
    assert sum(len(task['subtasks']) for task in baseline['tasks']) == size * subtasks
    page.evaluate('window.workspaceFailureOriginalDocument = true')
    return baseline


def inject(page, method, store_name, key=None, occurrence=1, quota=False, queued=True):
    page.evaluate("""options => {
        const original = IDBObjectStore.prototype[options.method];
        window.workspaceFailureInjection = {matched:0, fired:false, queued:false};
        IDBObjectStore.prototype[options.method] = function(value, ...rest) {
            const matches = this.name === options.store
                && (options.key === null || value?.key === options.key);
            if (!matches) return original.call(this, value, ...rest);
            const observation = window.workspaceFailureInjection;
            observation.matched++;
            if (observation.matched !== options.occurrence) return original.call(this, value, ...rest);
            IDBObjectStore.prototype[options.method] = original;
            observation.fired = true;
            let request;
            if (options.queued) {
                request = original.call(this, value, ...rest);
                observation.queued = true;
            }
            if (options.quota) throw new DOMException('Injected synthetic quota failure', 'QuotaExceededError');
            this.transaction.abort();
            return request;
        };
    }""", {'method': method, 'store': store_name, 'key': key, 'occurrence': occurrence,
             'quota': quota, 'queued': queued})


def injection_seen(page, queued):
    observation = page.evaluate('window.workspaceFailureInjection')
    assert observation['fired'] and observation['queued'] == queued, observation
    return observation


def close_dirty_form(page):
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def verify_rollback(page, before, reopen=True):
    assert_equal(stored(page), before, 'Failed write changed tasks, config, revision or recovery history')
    if reopen:
        page.reload()
        wait_for_app_ready(page)
        assert_equal(stored(page), before, 'Failed write changed persisted records after reload')


def edit_abort(page, before, history=False):
    page.locator('#searchInput').fill(FIRST)
    click_task_action(task_locator(page, FIRST), 'edit')
    page.locator('#taskDesc').fill('A changed field that must remain unsaved after abort')
    inject(page, 'put', 'config' if history else 'tasks', 'recoveryHistory' if history else None)
    page.locator('#submitBtn').click()
    expect(page.locator('#submitBtn')).to_be_enabled()
    expect(page.locator('#taskDesc')).to_have_value('A changed field that must remain unsaved after abort')
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    seen = injection_seen(page, True)
    verify_rollback(page, before, False)
    close_dirty_form(page)
    verify_rollback(page, before)
    return {'injection': seen, 'rollback_after_reload': True}


def select_batch(page, size):
    page.locator('#searchInput').fill('Failure workspace 0000')
    expect(page.locator('.task-item')).to_have_count(min(size, 10))
    page.locator('#batchModeBtn').click()
    for index in range(3):
        task_locator(page, f'Failure workspace {index:05d} 中文').locator('.task-select-checkbox').check()


def batch_abort(page, before, delete=False):
    select_batch(page, len(before['tasks']))
    if delete:
        page.locator('#batchDeleteBtn').click()
        expect(page.locator('#taskModal')).to_be_visible()
        inject(page, 'put', 'config', 'taskRevision')
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
    else:
        inject(page, 'put', 'tasks', occurrence=2)
        page.locator('#batchCompleteBtn').click()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    seen = injection_seen(page, True)
    verify_rollback(page, before)
    return {'injection': seen, 'queued_prior_mutations': 'delete + checkpoint' if delete else 'first task put + checkpoint',
            'rollback_after_reload': True}


def restore_abort(page, before):
    open_recovery(page)
    page.locator('#recoverySelect').select_option('workspace-failure-old', force=True)
    page.locator('#recoveryConfirm').check()
    inject(page, 'put', 'tasks')
    page.locator('#submitBtn').click()
    expect(page.locator('#submitBtn')).to_be_enabled()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    seen = injection_seen(page, True)
    verify_rollback(page, before, False)
    if page.locator('#taskModal').is_visible():
        page.locator('#cancelBtn').click()
    verify_rollback(page, before)
    return {'injection': seen, 'queued_prior_mutations': 'tasks.clear + checkpoint', 'rollback_after_reload': True}


def assert_successful_add(before, after, name):
    old = {task['id']: task for task in before['tasks']}
    added = [task for task in after['tasks'] if task['id'] not in old]
    assert len(added) == 1 and added[0]['name'] == name, 'Explicit recovered submit did not commit exactly once'
    assert len(after['tasks']) == len(before['tasks']) + 1
    for task in after['tasks']:
        if task['id'] in old:
            assert_equal(task, old[task['id']], 'Recovered submit changed an unrelated saved task')
    original, current = config(before), config(after)
    assert current['taskRevision'] == original['taskRevision'] + 1
    assert_equal(current['recoveryHistory'][0]['tasks'], before['tasks'], 'Recovery checkpoint was not exact')
    assert_equal(current['recoveryHistory'][1:], original['recoveryHistory'], 'Recovery removed older history')
    for key, value in original.items():
        if key not in ('taskRevision', 'recoveryHistory'):
            assert_equal(current.get(key), value, f'Recovered submit changed unrelated config {key}')
    return added[0]


def retry(page, before):
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    assert page.evaluate('window.workspaceFailureOriginalDocument === true'), 'Retry reloaded away the retained draft'
    assert_equal(stored(page), before, 'Storage retry changed committed workspace without an explicit submit')


def quota_form(page, before):
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill(DRAFT_NAME)
    page.locator('#taskDesc').fill('Retain this exact draft after a failed checkpoint')
    page.locator('#taskProject').fill('Recovery')
    page.locator('#taskTags').fill('retained, workspace')
    page.locator('#noDeadline').check()
    page.locator('#subtaskInput').fill('Saved draft child 中文')
    page.locator('#addSubtaskBtn').click()
    page.locator('#subtaskInput').fill('Unsubmitted draft child 中文')
    inject(page, 'put', 'config', 'recoveryHistory', quota=True, queued=False)
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    seen = injection_seen(page, False)
    verify_rollback(page, before, False)
    drafts = downloaded_drafts(page)
    assert len(drafts) == 1 and drafts[0]['form']['values']['name'] == DRAFT_NAME
    assert drafts[0]['form']['values']['subtask'] == 'Unsubmitted draft child 中文'
    assert drafts[0]['form']['subtasks'][0]['text'] == 'Saved draft child 中文'
    assert unload_is_guarded(page)
    retry(page, before)
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskName')).to_have_value(DRAFT_NAME)
    expect(page.locator('#subtaskInput')).to_have_value('Unsubmitted draft child 中文')
    page.locator('#addSubtaskBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = stored(page)
    added = assert_successful_add(before, after, DRAFT_NAME)
    assert [child['text'] for child in added['subtasks']] == ['Saved draft child 中文', 'Unsubmitted draft child 中文']
    assert not unload_is_guarded(page)
    page.reload()
    wait_for_app_ready(page)
    assert_equal(stored(page), after, 'Recovered task/checkpoint changed after reload')
    return {'injection': seen, 'draft_download': True, 'same_document_retry': True,
            'explicit_single_submit': True, 'after_sha256': digest(after)}


def quota_quick(page, before):
    page.locator('#quickAddInput').fill(RAW_QUICK)
    inject(page, 'add', 'tasks', quota=True, queued=True)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#quickAddInput')).to_have_value(RAW_QUICK)
    expect(page.locator('#quickAddInput')).to_have_attribute('readonly', '')
    seen = injection_seen(page, True)
    verify_rollback(page, before, False)
    assert unload_is_guarded(page)
    retry(page, before)
    expect(page.locator('#quickAddInput')).to_have_value(RAW_QUICK)
    expect(page.locator('#quickAddInput')).not_to_have_attribute('readonly', '')
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    after = stored(page)
    added = assert_successful_add(before, after, 'Recovered full-workspace quick draft')
    assert added['project'] == 'Recovery' and added['tags'] == ['retained']
    assert not unload_is_guarded(page)
    page.reload()
    wait_for_app_ready(page)
    assert_equal(stored(page), after, 'Recovered quick-add/checkpoint changed after reload')
    return {'injection': seen, 'same_document_retry': True, 'explicit_single_submit': True,
            'after_sha256': digest(after)}


def stale_edit(page, before, url):
    page.locator('#searchInput').fill(FIRST)
    click_task_action(task_locator(page, FIRST), 'edit')
    page.locator('#taskDesc').fill('Unsaved stale first-window draft')
    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        expect(other.locator('.task-item')).to_have_count(min(len(before['tasks']), 100))
        other.locator('#searchInput').fill(FIRST)
        click_task_action(task_locator(other, FIRST), 'edit')
        other.locator('#taskDesc').fill('A newer second-window committed edit')
        other.locator('#submitBtn').click()
        expect(other.locator('#taskModal')).to_be_hidden()
        remote = stored(other)
        old_by_id = {task['id']: task for task in before['tasks']}
        for task in remote['tasks']:
            expected = {**old_by_id[task['id']]}
            if task['name'] == FIRST:
                expected['description'] = 'A newer second-window committed edit'
            assert_equal(task, expected, 'Remote field edit changed unrelated task fields')
        assert config(remote)['taskRevision'] == config(before)['taskRevision'] + 1
        page.locator('#submitBtn').click()
        expect(page.locator('#submitBtn')).to_be_enabled()
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskDesc')).to_have_value('Unsaved stale first-window draft')
        assert_equal(stored(page), remote, 'Stale form overwrote newer tasks, history, revision or settings')
        assert unload_is_guarded(page)
        close_dirty_form(page)
        page.reload()
        wait_for_app_ready(page)
        assert_equal(stored(page), remote, 'Rejected stale edit changed persisted workspace')
        return {'two_actual_pages': True, 'stale_draft_retained': True, 'remote_sha256': digest(remote)}
    finally:
        other.close()


def asynchronous_request_error(page, before, url):
    page.evaluate("""identity => {
        window.workspaceAsyncFailure = {trace:[], caught:null, abortObserved:false, queued:false};
        const transaction = IDBDatabase.prototype.transaction;
        IDBDatabase.prototype.transaction = function(...args) {
            const tx = transaction.apply(this, args);
            if (tx.mode === 'readwrite' && Array.from(tx.objectStoreNames).includes('tasks')) {
                tx.addEventListener('error', event => window.workspaceAsyncFailure.trace.push({
                    stage:'transaction.error', transactionError:tx.error?.name || null,
                    targetError:event.target?.error?.name || null
                }));
                tx.addEventListener('abort', () => {
                    window.workspaceAsyncFailure.abortObserved = true;
                    window.workspaceAsyncFailure.trace.push({stage:'transaction.abort', transactionError:tx.error?.name || null});
                });
            }
            return tx;
        };
        const add = IDBObjectStore.prototype.add;
        IDBObjectStore.prototype.add = function(value, ...rest) {
            if (this.name !== 'tasks') return add.call(this, value, ...rest);
            IDBObjectStore.prototype.add = add;
            const request = add.call(this, {...value, id:identity}, ...rest);
            window.workspaceAsyncFailure.queued = true;
            request.addEventListener('error', () => window.workspaceAsyncFailure.trace.push({
                stage:'request.error', requestError:request.error?.name || null,
                transactionError:this.transaction.error?.name || null
            }));
            return request;
        };
        const error = console.error;
        console.error = function(...args) {
            if (args[0] === '快速添加任务失败:') window.workspaceAsyncFailure.caught = {
                errorName:args[1]?.name || null, abortObserved:window.workspaceAsyncFailure.abortObserved
            };
            return error.apply(this, args);
        };
    }""", before['tasks'][0]['id'])
    raw = 'Recovered real asynchronous request failure'
    page.locator('#quickAddInput').fill(raw)
    page.locator('#quickAddInput').press('Enter')
    page.wait_for_function('window.workspaceAsyncFailure.caught !== null && window.workspaceAsyncFailure.abortObserved')
    observed = page.evaluate('window.workspaceAsyncFailure')
    print('Real asynchronous request failure observations: ' + json.dumps(observed), flush=True)
    assert observed['queued'], 'Duplicate add was not queued as a genuine IndexedDB request'
    request_error = next(event for event in observed['trace'] if event['stage'] == 'request.error')
    assert request_error['requestError'] == 'ConstraintError', observed
    assert observed['caught']['errorName'] == 'ConstraintError', \
        'Application discarded the native asynchronous request error: ' + json.dumps(observed)
    assert observed['caught']['abortObserved'], \
        'Application rejected before transaction rollback completed: ' + json.dumps(observed)
    verify_rollback(page, before, False)
    expect(page.locator('#quickAddInput')).to_have_value(raw)
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    expect(page.locator('#quickAddForm button[type="submit"]')).to_be_enabled()
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    after = stored(page)
    assert_successful_add(before, after, raw)
    page.reload()
    wait_for_app_ready(page)
    assert_equal(stored(page), after, 'Explicit retry after native request error changed committed records on reload')
    return {'native_error': 'ConstraintError', 'fault': 'One real duplicate-key add, not quota injection',
            'events': observed, 'explicit_single_submit': True, 'after_sha256': digest(after)}


CASES = {
    'edit-task-abort': lambda page, before, url: edit_abort(page, before),
    'edit-history-abort': lambda page, before, url: edit_abort(page, before, True),
    'batch-write-abort': lambda page, before, url: batch_abort(page, before),
    'batch-delete-revision-abort': lambda page, before, url: batch_abort(page, before, True),
    'restore-write-abort': lambda page, before, url: restore_abort(page, before),
    'form-checkpoint-quota': lambda page, before, url: quota_form(page, before),
    'quick-add-queued-quota': lambda page, before, url: quota_quick(page, before),
    'stale-edit': stale_edit,
    'asynchronous-request-error': asynchronous_request_error,
}


def run(engine, size, subtasks, selected, output):
    source = None
    tool_hash = None
    report = {'schema_version': 1, 'run_id': str(uuid.uuid4()), 'started_at': timestamp(),
              'finished_at': None, 'status': 'initializing', 'completed': False, 'passed': False,
              'browser_engine': engine, 'tasks': size, 'subtasks_per_task': subtasks,
              'source': None, 'source_final': None, 'source_unchanged': False,
              'tool_sha256': None, 'tool_unchanged': False, 'integrity_errors': [], 'error': None, 'cases': [],
              'scope': 'Controlled queued-transaction abort, quota-failure injection and a real asynchronous duplicate-key ConstraintError; not actual quota exhaustion or browser eviction',
              'performance_scope': 'Correctness only; timings include setup and may share cloud resources'}
    if output:
        atomic_report(output, report)
    failure = None
    expect.set_options(timeout=45000)
    try:
        source = source_identity()
        tool_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report['source'] = source
        report['tool_sha256'] = tool_hash
        report['status'] = 'running'
        if output:
            atomic_report(output, report)
        with local_server() as url, sync_playwright() as p:
            options = browser_launch_options() if engine == 'chromium' else {'headless': True}
            browser = getattr(p, engine).launch(**options)
            report['browser_version'] = browser.version
            try:
                for name in selected:
                    started = time.perf_counter()
                    result = {'case': name, 'passed': False, 'started_at': timestamp()}
                    context = browser.new_context(accept_downloads=True, reduced_motion='reduce', timezone_id='UTC')
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    try:
                        before = prepare(page, url, size, subtasks)
                        result['before_sha256'] = digest(before)
                        result['assertions'] = CASES[name](page, before, url)
                        assert not errors, errors
                        result['passed'] = True
                        print(f'Workspace failure passed: {name}; {size} tasks × {subtasks} subtasks; browser={engine}', flush=True)
                    except BaseException as error:
                        result['error'] = f'{type(error).__name__}: {error}'
                        result['page_errors'] = errors
                        failure = error
                        print(f'Workspace failure FAILED: {name}; {result["error"]}', flush=True)
                    finally:
                        result['duration_seconds'] = round(time.perf_counter() - started, 3)
                        report['cases'].append(result)
                        context.close()
                        if output:
                            atomic_report(output, report)
                    if failure:
                        break
            finally:
                browser.close()
    except BaseException as error:
        failure = error
        report['error'] = f'{type(error).__name__}: {error}'
    finally:
        try:
            report['source_final'] = source_identity()
            report['source_unchanged'] = source is not None and report['source_final'] == source
            if source is not None and not report['source_unchanged']:
                report['integrity_errors'].append('Runtime input snapshot changed during checks')
        except BaseException as error:
            report['integrity_errors'].append(f'Final runtime capture failed: {type(error).__name__}: {error}')
            if failure is None:
                failure = error
                report['error'] = f'{type(error).__name__}: {error}'
        try:
            final_tool_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            report['tool_unchanged'] = tool_hash is not None and final_tool_hash == tool_hash
            if tool_hash is not None and not report['tool_unchanged']:
                report['integrity_errors'].append('Workspace failure tool changed during checks')
        except BaseException as error:
            report['integrity_errors'].append(f'Final tool capture failed: {type(error).__name__}: {error}')
            if failure is None:
                failure = error
                report['error'] = f'{type(error).__name__}: {error}'
        report['completed'] = len(report['cases']) == len(selected)
        report['passed'] = not failure and report['completed'] and report['source_unchanged'] and report['tool_unchanged'] and not report['integrity_errors']
        report['status'] = 'passed' if report['passed'] else 'failed'
        report['finished_at'] = timestamp()
        if output:
            atomic_report(output, report)
        print(json.dumps({key: report[key] for key in ('status', 'browser_engine', 'tasks', 'subtasks_per_task', 'source_unchanged')}, ensure_ascii=False), flush=True)
    if failure:
        raise failure
    assert report['passed'], 'Input drift or incomplete checks prevented a pass'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--size', type=int, default=200)
    parser.add_argument('--subtasks', type=int, default=6)
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 3 <= args.size <= 10000 or not 0 <= args.subtasks <= 20:
        parser.error('Use 3..10000 tasks and 0..20 subtasks per task')
    run(args.browser, args.size, args.subtasks, list(CASES) if args.case == 'all' else [args.case], args.output)
