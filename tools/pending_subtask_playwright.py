#!/usr/bin/env python3
"""Save a pending subtask once without consuming a failed or composing draft.

Uses fresh browser contexts and the real deployment CSP. Composition checks
exercise DOM events; they do not claim to test a native operating-system IME.
Each invocation keeps a unique evidence directory, including the first failure.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import threading
import traceback
import uuid

from playwright.sync_api import Page, expect, sync_playwright

from recovery_management_playwright import config, stored
from security_playwright import ProductionHeaderHandler
from smoke_playwright import (
    ThreadingHTTPServer, add_task, browser_launch_options, click_task_action,
    get_task_records, open_task_editor, reveal_task_field, task_locator,
    wait_for_app_ready,
)
from task_draft_playwright import downloaded_drafts, unload_is_guarded
from workspace_failure_playwright import inject, injection_seen


@contextmanager
def deployment_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def by_id(records):
    return {record['id']: record for record in records}


def check_subtasks(task, expected_texts) -> None:
    children = task['subtasks']
    assert [child['text'] for child in children] == expected_texts, children
    identifiers = [child['id'] for child in children]
    assert all(identifier is not None for identifier in identifiers), children
    assert len(set(identifiers)) == len(identifiers), 'Subtask identifiers collided'


def only_added(page: Page, before, name, expected_texts):
    after = get_task_records(page)
    original = by_id(before)
    assert {item['id']: item for item in after if item['id'] in original} == original, 'Creating a task changed an existing record'
    added = [item for item in after if item['id'] not in original]
    assert len(after) == len(before) + 1 and len(added) == 1, 'One submission created zero or duplicate tasks'
    task = added[0]
    assert task['name'] == name, task
    check_subtasks(task, expected_texts)
    assert all(child['completed'] is False for child in task['subtasks']), task
    return task


def only_appended(page: Page, before, identifier, pending_text):
    after = get_task_records(page)
    old, new = by_id(before), by_id(after)
    assert old.keys() == new.keys(), 'Editing created or removed a task'
    assert {key: value for key, value in old.items() if key != identifier} == {
        key: value for key, value in new.items() if key != identifier
    }, 'Editing changed a different task'
    original, updated = old[identifier], new[identifier]
    assert {key: value for key, value in updated.items() if key != 'subtasks'} == {
        key: value for key, value in original.items() if key != 'subtasks'
    }, 'Appending a subtask changed another field of the task'
    assert updated['subtasks'][:-1] == original['subtasks'], 'Existing subtask IDs, text, order or completion changed'
    check_subtasks(updated, [child['text'] for child in original['subtasks']] + [pending_text])
    assert updated['subtasks'][-1]['completed'] is False, updated
    return updated


def persisted_after_reload(page: Page) -> None:
    expected = get_task_records(page)
    page.reload()
    wait_for_app_ready(page)
    assert get_task_records(page) == expected, 'Reload changed the committed task data'


def keep_editing(page: Page) -> None:
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
    expect(page.locator('#taskModal')).to_be_visible()


def fill_pending_form(page: Page, name: str) -> None:
    open_task_editor(page)
    page.locator('#taskName').fill(name)
    page.locator('#taskDesc').fill('保留原文与换行。\n不能因加入最后一条子任务改动其它字段。')
    page.locator('#taskProject').fill('评审项目')
    page.locator('#noDeadline').check()
    reveal_task_field(page, '#taskTags').fill('review, "quoted, tag"')


def create_pending(page: Page, evidence: Path) -> None:
    before = get_task_records(page)
    name = '新建长任务：整理资料、确认负责人并准备下一轮评审'
    fill_pending_form(page, name)
    raw = '  未点加号的最后一条子任务  '
    page.locator('#subtaskInput').fill(raw)
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    task = only_added(page, before, name, [raw.strip()])
    assert task['description'] == '保留原文与换行。\n不能因加入最后一条子任务改动其它字段。', task
    assert task['project'] == '评审项目' and task['tags'] == ['review', 'quoted, tag'], task
    assert task['dueAt'] is None and task['repeatType'] == 'none', task
    assert not unload_is_guarded(page)
    task_locator(page, name).locator('.subtask-summary-bar').click()
    expect(task_locator(page, name).locator('.subtask-text')).to_have_text(raw.strip())
    page.screenshot(path=str(evidence / 'verification.png'), full_page=True)
    persisted_after_reload(page)


def explicit_and_whitespace(page: Page, evidence: Path) -> None:
    before = get_task_records(page)
    open_task_editor(page)
    page.locator('#taskName').fill('显式添加与空白输入不重复')
    page.locator('#noDeadline').check()
    page.locator('#subtaskInput').fill('通过加号加入')
    page.locator('#addSubtaskBtn').click()
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(1)
    expect(page.locator('#subtaskInput')).to_have_value('')
    page.locator('#subtaskInput').fill('通过Enter加入')
    page.locator('#subtaskInput').press('Enter')
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(2)
    expect(page.locator('#subtaskInput')).to_have_value('')
    page.locator('#subtaskInput').fill('   \t  ')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    only_added(page, before, '显式添加与空白输入不重复', ['通过加号加入', '通过Enter加入'])
    before = get_task_records(page)
    open_task_editor(page)
    page.locator('#taskName').fill('只有空白子任务')
    page.locator('#noDeadline').check()
    page.locator('#subtaskInput').fill('   ')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    only_added(page, before, '只有空白子任务', [])


def editable_completed_subtask(page: Page):
    name = '保留已完成子任务和全部任务字段'
    add_task(page, name, description='原始描述。\n第二行不应变化。',
             project='原项目', tags=['original', 'keep'], due_date='2032-05-06',
             due_time='16:35', reminder_offset='60', repeat_type='weekly-days',
             repeat_weekdays=['2', '4'], repeat_paused=True,
             subtasks=['已经完成的第一条', '仍未完成的第二条'])
    task = task_locator(page, name)
    task.locator('.subtask-summary-bar').click()
    task.locator('.subtask-checkbox').first.check()
    expect(task.locator('.subtask-checkbox').first).to_be_checked()
    page.wait_for_function("""name => new Promise(resolve => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('tasks');
            const all = tx.objectStore('tasks').getAll();
            all.onsuccess = () => resolve(all.result.find(task => task.name === name)?.subtasks[0]?.completed === true);
            tx.oncomplete = () => db.close();
        };
    })""", arg=name)
    before = get_task_records(page)
    original = next(item for item in before if item['name'] == name)
    assert original['subtasks'][0]['completed'] is True
    assert original['subtasks'][1]['completed'] is False
    click_task_action(task, 'edit')
    expect(page.locator('#taskModal')).to_be_visible()
    return before, original


def edit_pending(page: Page, evidence: Path) -> None:
    before, original = editable_completed_subtask(page)
    page.locator('#subtaskInput').fill('  编辑时补充的最后一条  ')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    only_appended(page, before, original['id'], '编辑时补充的最后一条')
    task = task_locator(page, original['name'])
    if not task.locator('.subtask-checkbox').first.is_visible():
        task.locator('.subtask-summary-bar').click()
    expect(task.locator('.subtask-checkbox')).to_have_count(3)
    expect(task.locator('.subtask-checkbox').first).to_be_checked()
    expect(task.locator('.subtask-checkbox').nth(1)).not_to_be_checked()
    expect(task.locator('.subtask-checkbox').nth(2)).not_to_be_checked()
    page.screenshot(path=str(evidence / 'verification.png'), full_page=True)
    persisted_after_reload(page)


def validation_retry(page: Page, evidence: Path) -> None:
    before = stored(page)
    open_task_editor(page)
    raw = '  名称校验失败后仍保留的子任务  '
    page.locator('#subtaskInput').fill(raw)
    page.locator('#submitBtn').click()
    assert page.locator('#taskName').evaluate('input => input.validity.valueMissing'), 'Missing task name bypassed native validation'
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#subtaskInput')).to_have_value(raw)
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
    assert stored(page) == before
    # Whitespace reaches application validation, after payload construction.
    page.locator('#taskName').fill('   ')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskName')).to_be_focused()
    expect(page.locator('#subtaskInput')).to_have_value(raw)
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
    assert stored(page) == before, 'Failed name validation committed task or config data'
    page.locator('#taskName').fill('校验与取消后再保存一次')
    keep_editing(page)
    expect(page.locator('#subtaskInput')).to_have_value(raw)
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
    assert unload_is_guarded(page)
    assert stored(page) == before, 'Cancelling a discard wrote task data'
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    only_added(page, before['tasks'], '校验与取消后再保存一次', [raw.strip()])


def failed_save_retry(page: Page, evidence: Path, *, quota: bool) -> None:
    if quota:
        fill_pending_form(page, '配额失败后恢复并保存一次')
        page.locator('#subtaskInput').fill('已经通过加号加入')
        page.locator('#addSubtaskBtn').click()
        original = None
    else:
        _, original = editable_completed_subtask(page)
    raw = '  失败后不能丢失或重复的子任务  '
    page.locator('#subtaskInput').fill(raw)
    before = stored(page)
    form_before = page.locator('#taskForm').aria_snapshot()
    save_json(evidence / 'before.json', before)
    page.evaluate('window.pendingSubtaskOriginalDocument = true')
    inject(page, 'add' if quota else 'put', 'tasks', quota=quota, queued=True)
    page.locator('#submitBtn').click()
    if not quota:
        # An explicit tx.abort() has no DOMException in tx.error. The app's
        # ordinary save-error path keeps this same form available for retry.
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#submitBtn')).to_be_enabled()
        expect(page.locator('#taskDraftSavingStatus')).to_have_count(0)
        expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
        expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
        injection_seen(page, queued=True)
        assert stored(page) == before, 'An aborted edit partially changed committed task/config data'
        expect(page.locator('#subtaskInput')).to_have_value(raw)
        assert page.locator('#taskForm').aria_snapshot() == form_before, 'An aborted edit changed its draft fields or existing subtasks'
        assert unload_is_guarded(page)
        keep_editing(page)
        expect(page.locator('#subtaskInput')).to_have_value(raw)
        assert stored(page) == before, 'Cancelling discard after an aborted save wrote task data'
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        only_appended(page, before['tasks'], original['id'], raw.strip())
        after = stored(page)
        assert config(after)['taskRevision'] == config(before)['taskRevision'] + 1, 'Retry committed the edited task more than once'
        assert not unload_is_guarded(page)
        save_json(evidence / 'after.json', after)
        persisted_after_reload(page)
        return
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    injection_seen(page, queued=True)
    assert stored(page) == before, 'An aborted task save partially changed committed task/config data'
    drafts = downloaded_drafts(page)
    save_json(evidence / 'recovered-drafts.json', drafts)
    assert len(drafts) == 1, drafts
    draft = drafts[0]
    assert draft['editingTaskId'] == (None if original is None else original['id'])
    assert draft['form']['values']['subtask'] == raw, 'Failure consumed the pending subtask text'
    expected_existing = original['subtasks'] if original else None
    if expected_existing is not None:
        assert draft['form']['subtasks'] == expected_existing, 'Failure changed existing completed subtask data'
    else:
        assert [child['text'] for child in draft['form']['subtasks']] == ['已经通过加号加入']
    assert unload_is_guarded(page)
    # Cancelling recovery-draft deletion must keep the same draft and content.
    page.locator('#taskDraftRecoveryDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    assert downloaded_drafts(page) == drafts, 'Cancelling draft deletion changed the recoverable draft'
    assert stored(page) == before
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_enabled()
    assert page.evaluate('window.pendingSubtaskOriginalDocument === true'), 'Retry reloaded away the in-memory draft'
    assert stored(page) == before, 'Storage Retry committed a task before explicit form submission'
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#subtaskInput')).to_have_value(raw)
    assert page.locator('#taskForm').aria_snapshot() == form_before, 'Restoring the failed form changed its fields or existing subtasks'
    keep_editing(page)
    expect(page.locator('#subtaskInput')).to_have_value(raw)
    assert stored(page) == before
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
    if original:
        only_appended(page, before['tasks'], original['id'], raw.strip())
    else:
        only_added(page, before['tasks'], '配额失败后恢复并保存一次', ['已经通过加号加入', raw.strip()])
    after = stored(page)
    assert config(after)['taskRevision'] == config(before)['taskRevision'] + 1, 'Recovery committed the task more than once'
    assert not unload_is_guarded(page)
    save_json(evidence / 'after.json', after)
    persisted_after_reload(page)


def quota_retry(page: Page, evidence: Path) -> None:
    failed_save_retry(page, evidence, quota=True)


def abort_retry(page: Page, evidence: Path) -> None:
    failed_save_retry(page, evidence, quota=False)


def composition(page: Page, evidence: Path) -> None:
    before = stored(page)
    open_task_editor(page)
    page.locator('#taskName').fill('组合输入结束后再保存')
    page.locator('#noDeadline').check()
    field = page.locator('#subtaskInput')
    field.fill('仍在中文组词的子任务')
    for selector in ('#subtaskInput', '#taskName'):
        active = page.locator(selector)
        active.focus()
        active.dispatch_event('compositionstart', {'data': '中文'})
        # requestSubmit preserves the composing input as document.activeElement;
        # a pointer click first moves focus to the button and ends that premise.
        expect(active).to_be_focused()
        page.locator('#taskForm').evaluate('form => form.requestSubmit()')
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#submitBtn')).to_be_enabled()
        expect(field).to_have_value('仍在中文组词的子任务')
        expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
        assert stored(page) == before, f'An active composition in {selector} saved or consumed the draft'
        active.dispatch_event('compositionend', {'data': '中文'})
    for mode in ('flag', 'legacy'):
        result = field.evaluate("""(input, mode) => {
            const event = new KeyboardEvent('keypress', {key:'Enter', bubbles:true,
                cancelable:true, isComposing:mode === 'flag', keyCode:mode === 'legacy' ? 229 : 0});
            input.dispatchEvent(event);
            return {composing:event.isComposing, code:event.keyCode, prevented:event.defaultPrevented};
        }""", mode)
        assert result['composing'] if mode == 'flag' else result['code'] == 229, result
        assert not result['prevented'], result
        expect(field).to_have_value('仍在中文组词的子任务')
        expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
        assert stored(page) == before
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    only_added(page, before['tasks'], '组合输入结束后再保存', ['仍在中文组词的子任务'])


CASES = {
    'create': create_pending, 'explicit': explicit_and_whitespace,
    'edit': edit_pending, 'validation': validation_retry,
    'quota': quota_retry, 'abort': abort_retry, 'composition': composition,
}


def run(engine: str, selected: str, widths: list[int], report_root: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report = report_root / f'{stamp}-{engine}-{uuid.uuid4().hex[:8]}'
    report.mkdir(parents=True, exist_ok=False)
    results = []
    print(f'Pending subtask evidence: {report}', flush=True)
    with deployment_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(playwright, engine).launch(timeout=30000, **options)
        root = Path(__file__).resolve().parents[1]
        source_files = ['index.html', 'vercel.json', 'sw.js', 'resources/en.json',
                        'resources/zh-CN.json', 'tools/pending_subtask_playwright.py']
        metadata = {'browser': engine, 'version': browser.version, 'production_csp': True,
                    'widths': widths, 'fresh_context_per_case': True, 'results': results,
                    'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                      for name in source_files if (root / name).is_file()}}
        for name in metadata['source_sha256']:
            destination = report / 'source-snapshot' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, destination)
        save_json(report / 'results.json', metadata)
        try:
            for width in widths:
                for name, check in CASES.items():
                    if selected != 'all' and selected != name:
                        continue
                    evidence = report / f'{width}-{name}'
                    evidence.mkdir()
                    context = browser.new_context(locale='zh-CN', timezone_id='UTC',
                                                  viewport={'width': width, 'height': 900 if width > 600 else 844},
                                                  reduced_motion='reduce', accept_downloads=True)
                    context.tracing.start(screenshots=True, snapshots=True, sources=True)
                    page = context.new_page()
                    errors = []
                    console = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: console.append({'type': message.type, 'text': message.text}))
                    result = {'width': width, 'case': name, 'status': 'running'}
                    results.append(result)
                    try:
                        response = page.goto(url)
                        assert response and response.headers.get('content-security-policy'), 'Deployment CSP was not served'
                        wait_for_app_ready(page)
                        assert get_task_records(page) == [], 'Fresh context unexpectedly contains task data'
                        add_task(page, '回归哨兵：不能改动已有记录', description='独立合成数据', no_deadline=True,
                                 subtasks=['保留哨兵子任务'])
                        save_json(evidence / 'initial.json', stored(page))
                        check(page, evidence)
                        assert not errors, errors
                        save_json(evidence / 'final.json', stored(page))
                        result['status'] = 'passed'
                        print(f'Pending subtask passed: {width}px {name}', flush=True)
                    except Exception:
                        result['status'] = 'failed'
                        result['error'] = traceback.format_exc()
                        (evidence / 'failure.txt').write_text(result['error'], encoding='utf-8')
                        page.screenshot(path=str(evidence / 'failure.png'), full_page=True)
                        (evidence / 'failure-dom.txt').write_text(page.locator('body').aria_snapshot(), encoding='utf-8')
                        save_json(evidence / 'failure-records.json', stored(page))
                        raise
                    finally:
                        save_json(evidence / 'browser-events.json', {'pageerrors': errors, 'console': console})
                        context.tracing.stop(path=str(evidence / 'trace.zip'))
                        context.close()
                        save_json(report / 'results.json', metadata)
        finally:
            browser.close()
    print(f'Pending subtask passed: {len(results)} cases; evidence {report}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--widths', type=int, nargs='+', default=[1280, 390])
    parser.add_argument('--report-dir', type=Path, default=Path('/tmp/task-tracer-4.13.2-pending'))
    args = parser.parse_args()
    run(args.browser, args.case, args.widths, args.report_dir)
