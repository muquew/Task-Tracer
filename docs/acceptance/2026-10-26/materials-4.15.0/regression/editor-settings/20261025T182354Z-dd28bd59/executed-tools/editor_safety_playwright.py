#!/usr/bin/env python3
"""Protect editor schedules, explicit weekday choices and inline subtask drafts.

Targeted real-UI regressions at desktop and mobile widths. Each run retains its
own source snapshot, native IndexedDB records, DOM, screenshots and traces.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import traceback
import uuid

from playwright.sync_api import Page, expect, sync_playwright

from pending_subtask_playwright import deployment_server, save_json, by_id, only_added, persisted_after_reload
from recovery_management_playwright import config, stored
from smoke_playwright import (
    add_task, browser_launch_options, click_task_action, get_task_records,
    open_task_editor, reveal_task_field, select_visible_option, task_locator,
    wait_for_app_ready,
)


FORM_FIELDS = ('taskName', 'taskDesc', 'taskProject', 'taskTags', 'noDeadline',
               'dueDate', 'dueTime', 'reminderOffset', 'reminderRepeat',
               'repeatType', 'repeatInterval', 'repeatPaused', 'subtaskInput')


def raw_form(page: Page):
    return page.evaluate("""ids => {
        const values = Object.fromEntries(ids.map(id => {
            const input = document.getElementById(id);
            return [id, input.type === 'checkbox' ? input.checked : input.value];
        }));
        values.weekdays = Array.from(document.querySelectorAll('.repeat-weekday-input'),
            input => ({value:input.value, checked:input.checked}));
        return values;
    }""", FORM_FIELDS)


def choose(page: Page, selector: str, value: str) -> None:
    reveal_task_field(page, selector)
    select_visible_option(page, selector, value)


def fill_schedule(page: Page, name: str, repeat_type: str) -> None:
    open_task_editor(page)
    page.locator('#taskName').fill(name)
    page.locator('#taskDesc').fill('第一行原始描述。\n第二行保留。')
    page.locator('#taskProject').fill('编辑安全审查')
    page.locator('#noDeadline').uncheck()
    page.locator('#dueDate').fill('2032-05-06')
    page.locator('#dueTime').fill('16:35')
    reveal_task_field(page, '#taskTags').fill('review, "tag, with comma"')
    choose(page, '#reminderOffset', '60')
    choose(page, '#reminderRepeat', '15')
    choose(page, '#repeatType', repeat_type)
    if repeat_type == 'weekly-days':
        for day in ('0', '1', '2', '3', '4', '5', '6'):
            page.locator(f'#repeatWeekday{day}').uncheck()
        for day in ('2', '4'):
            page.locator(f'#repeatWeekday{day}').check()
    else:
        reveal_task_field(page, '#repeatInterval').fill('9')
    reveal_task_field(page, '#repeatPaused').check()
    page.locator('#subtaskInput').fill('已经加入的子任务')
    page.locator('#addSubtaskBtn').click()
    page.locator('#subtaskInput').fill('  仍在输入框中的子任务  ')


def assert_same_except_no_deadline(actual, expected) -> None:
    assert {key: value for key, value in actual.items() if key != 'noDeadline'} == {
        key: value for key, value in expected.items() if key != 'noDeadline'
    }, 'Toggling No deadline changed another raw form value'


VALIDATION_VISIBILITY = """() => {
    const error = document.getElementById('repeatWeekdaysError');
    const form = document.getElementById('taskForm');
    const footer = form.querySelector('.form-actions');
    const header = document.querySelector('#taskModal .modal-header');
    const rect = node => {
        const r = node.getBoundingClientRect();
        return {top:r.top, bottom:r.bottom, left:r.left, right:r.right,
            width:r.width, height:r.height};
    };
    const e = rect(error), f = rect(form), a = rect(footer), h = rect(header);
    const clip = {top:Math.max(0, f.top, h.bottom), bottom:Math.min(innerHeight, f.bottom, a.top),
        left:Math.max(0, f.left), right:Math.min(innerWidth, f.right)};
    const hit = document.elementFromPoint((e.left + e.right) / 2, (e.top + e.bottom) / 2);
    return {error:e, form:f, footer:a, header:h, clip,
        fullyVisible:!error.hidden && e.height > 0 && e.width > 0
            && e.top >= clip.top - 1 && e.bottom <= clip.bottom + 1
            && e.left >= clip.left - 1 && e.right <= clip.right + 1,
        hitInside:Boolean(hit && (hit === error || error.contains(hit))),
        hit:hit ? {tag:hit.tagName, id:hit.id, className:hit.className} : null};
}"""


def assert_weekday_error_readable(page: Page, evidence: Path) -> None:
    expect(page.locator('#repeatWeekdaysError')).to_be_visible()
    try:
        page.wait_for_function(
            f'() => {{ const state = ({VALIDATION_VISIBILITY})(); return state.fullyVisible && state.hitInside; }}',
            timeout=5000,
        )
    finally:
        save_json(evidence / 'validation-visibility.json', page.evaluate(VALIDATION_VISIBILITY))


def date_roundtrip(page: Page, evidence: Path) -> None:
    for repeat_type in ('weekly-days', 'custom'):
        name = f'无日期往返保留安排 {repeat_type}'
        fill_schedule(page, name, repeat_type)
        before = stored(page)
        original = raw_form(page)
        save_json(evidence / f'{repeat_type}-raw-before.json', original)
        for _ in range(2):
            page.locator('#noDeadline').check()
            expect(page.locator('#dueDate')).to_be_disabled()
            assert_same_except_no_deadline(raw_form(page), original)
            assert stored(page) == before, 'Disabling a schedule committed data'
            page.locator('#noDeadline').uncheck()
            expect(page.locator('#dueDate')).to_be_enabled()
            assert raw_form(page) == original, 'The original schedule did not return after a second toggle'
            assert stored(page) == before
        if repeat_type == 'weekly-days':
            page.locator('#repeatGroup').scroll_into_view_if_needed()
            page.screenshot(path=str(evidence / 'roundtrip-restored.png'), full_page=True)
        else:
            # Preserve raw values while disabled; normalize only the submitted record.
            page.locator('#noDeadline').check()
            assert_same_except_no_deadline(raw_form(page), original)
        save_json(evidence / f'{repeat_type}-raw-before-save.json', raw_form(page))
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        task = only_added(page, before['tasks'], name, ['已经加入的子任务', '仍在输入框中的子任务'])
        assert task['description'] == '第一行原始描述。\n第二行保留。'
        assert task['project'] == '编辑安全审查' and task['tags'] == ['review', 'tag, with comma']
        if repeat_type == 'weekly-days':
            assert task['dueLocalDate'] == '2032-05-06' and task['dueLocalTime'] == '16:35', task
            assert task['reminderOffset'] == 60 and task['reminderRepeat'] == 15, task
            assert task['repeatType'] == 'weekly-days' and task['repeatWeekdays'] == [2, 4], task
            assert task['repeatPaused'] is True, task
        else:
            assert task['dueAt'] is None and task['dueDate'] is None, task
            assert task['reminderOffset'] == -1 and task['reminderRepeat'] == -1, task
            assert task['repeatType'] == 'none' and task['repeatInterval'] == 1, task
            assert task['repeatWeekdays'] == [] and task['repeatPaused'] is False, task
        after = stored(page)
        assert config(after)['taskRevision'] == config(before)['taskRevision'] + 1
        save_json(evidence / f'{repeat_type}-saved.json', after)
        persisted_after_reload(page)


def empty_weekdays(page: Page, evidence: Path) -> None:
    fill_schedule(page, '必须明确选择重复星期', 'weekly-days')
    for day in ('2', '4'):
        page.locator(f'#repeatWeekday{day}').uncheck()
    expect(page.locator('#repeatWeekdaysRow input:checked')).to_have_count(0)
    before = stored(page)
    values = raw_form(page)
    row = page.locator('#repeatWeekdaysRow')
    prior_visible_text = row.inner_text().strip()
    save_json(evidence / 'invalid-raw-before.json', values)
    save_json(evidence / 'invalid-db-before.json', before)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_enabled()
    expect(page.locator('#taskDraftSavingStatus')).to_have_count(0)
    expect(page.locator('#repeatWeekdaysRow input:checked')).to_have_count(0)
    assert raw_form(page) == values, 'Weekday validation changed the unfinished form'
    assert stored(page) == before, 'Invalid weekdays wrote task, revision or recovery data'
    # Check rendered feedback near the group without tying the test to translated copy.
    visible_text = row.inner_text().strip()
    assert visible_text != prior_visible_text and len(visible_text) > len(prior_visible_text), 'Empty weekdays have no visible inline validation message'
    assert page.evaluate("Boolean(document.activeElement.closest('#repeatWeekdaysRow'))"), 'Weekday validation did not move focus into the invalid group'
    assert_weekday_error_readable(page, evidence)
    page.screenshot(path=str(evidence / 'invalid-weekdays-feedback.png'), full_page=True)
    (evidence / 'invalid-dom.txt').write_text(page.locator('#taskModal').aria_snapshot(), encoding='utf-8')
    # A repeated invalid submit must remain read-only and retain the pending subtask.
    page.locator('#submitBtn').click()
    assert raw_form(page) == values
    assert stored(page) == before
    page.locator('#repeatWeekday4').check()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    task = only_added(page, before['tasks'], '必须明确选择重复星期', ['已经加入的子任务', '仍在输入框中的子任务'])
    assert task['repeatType'] == 'weekly-days' and task['repeatWeekdays'] == [4], task
    assert task['dueLocalDate'] == '2032-05-06' and task['dueLocalTime'] == '16:35', task
    assert task['reminderOffset'] == 60 and task['reminderRepeat'] == 15, task
    assert task['repeatPaused'] is True, task
    assert config(stored(page))['taskRevision'] == config(before)['taskRevision'] + 1
    persisted_after_reload(page)


def subtask_delete(page: Page, evidence: Path) -> None:
    name = '删除前行保留后行未完成编辑'
    add_task(page, name, description='不能改动此任务其它原始字段。\n保留换行。',
             due_date='2032-05-06', due_time='16:35', project='子任务安全',
             tags=['keep', 'original'], reminder_offset='60', repeat_type='weekly-days',
             repeat_weekdays=['2', '4'], repeat_paused=True,
             subtasks=['联系负责人A', '校对数据B', '检查附件C'])
    task = task_locator(page, name)
    task.locator('.subtask-summary-bar').click()
    task.locator('.subtask-checkbox').nth(2).check()
    expect(task.locator('.subtask-checkbox').nth(2)).to_be_checked()
    page.wait_for_function("""name => new Promise(resolve => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('tasks');
            const all = tx.objectStore('tasks').getAll();
            all.onsuccess = () => resolve(all.result.find(task => task.name === name)?.subtasks[2]?.completed === true);
            tx.oncomplete = () => db.close();
        };
    })""", arg=name)
    before = stored(page)
    original = next(record for record in before['tasks'] if record['name'] == name)
    assert original['subtasks'][2]['completed'] is True
    click_task_action(task, 'edit')
    preview = page.locator('#subtaskListPreview')
    preview.get_by_role('button', name='编辑子任务：检查附件C', exact=True).click()
    editor = preview.get_by_role('textbox', name='编辑子任务文本', exact=True)
    changed = '检查附件C：已补充关键修改'
    editor.fill(changed)
    editor.evaluate("input => { input.setSelectionRange(2, 6); window.editorSafetyOldInput = input; }")
    expect(editor).to_be_focused()
    save_json(evidence / 'before-delete-db.json', before)
    (evidence / 'before-delete-dom.txt').write_text(page.locator('#taskModal').aria_snapshot(), encoding='utf-8')
    # This real pointer path caused the original mousedown/focusout ordering bug.
    preview.get_by_role('button', name='删除子任务：联系负责人A', exact=True).click()
    expect(preview.locator('.subtask-preview-item')).to_have_count(2)
    expect(editor).to_have_value(changed)
    expect(editor).to_be_focused()
    assert editor.evaluate('input => [input.selectionStart, input.selectionEnd]') == [2, 6], 'Deleting another row reset the current edit selection'
    assert stored(page) == before, 'Deleting a temporary subtask committed data before Save'
    # A detached editor's delayed focusout must not touch the current editor or another item.
    page.evaluate("window.editorSafetyOldInput.dispatchEvent(new FocusEvent('focusout', {bubbles:true}))")
    expect(editor).to_have_value(changed)
    expect(editor).to_be_focused()
    assert stored(page) == before
    page.screenshot(path=str(evidence / 'editing-preserved-after-delete.png'), full_page=True)
    (evidence / 'after-delete-dom.txt').write_text(page.locator('#taskModal').aria_snapshot(), encoding='utf-8')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = stored(page)
    old, new = by_id(before['tasks']), by_id(after['tasks'])
    assert old.keys() == new.keys(), 'Editing created or removed a task record'
    assert {key: record for key, record in old.items() if key != original['id']} == {
        key: record for key, record in new.items() if key != original['id']
    }, 'Deleting a draft child changed another task'
    expected = {**original, 'subtasks': [original['subtasks'][1], {**original['subtasks'][2], 'text': changed}]}
    assert new[original['id']] == expected, 'Deletion lost the inline edit, stable IDs, completion state, or another task field'
    assert config(after)['taskRevision'] == config(before)['taskRevision'] + 1
    save_json(evidence / 'after-save-db.json', after)
    persisted_after_reload(page)


CASES = {'date-roundtrip': date_roundtrip, 'empty-weekdays': empty_weekdays, 'subtask-delete': subtask_delete}


def run(engine: str, selected: str, widths: list[int], report_root: Path, expected_sha: str | None) -> None:
    root = Path(__file__).resolve().parents[1]
    initial_sha = hashlib.sha256((root / 'index.html').read_bytes()).hexdigest()
    if expected_sha:
        assert initial_sha == expected_sha, f'Expected source {expected_sha}; actual {initial_sha}'
    report = report_root / f'{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}-{engine}-{uuid.uuid4().hex[:8]}'
    report.mkdir(parents=True, exist_ok=False)
    source_names = ['index.html', 'vercel.json', 'sw.js', 'resources/en.json', 'resources/zh-CN.json',
                    'tools/editor_safety_playwright.py', 'tools/pending_subtask_playwright.py']
    sources = {}
    for name in source_names:
        if not (root / name).is_file():
            continue
        sources[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        destination = report / 'source-snapshot' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, destination)
    results = []
    metadata = {'source_sha256': sources, 'widths': widths, 'normal_motion': True,
                'production_csp': True, 'results': results}
    print(f'Editor safety evidence: {report}', flush=True)
    with deployment_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(playwright, engine).launch(timeout=30000, **options)
        metadata.update({'browser': engine, 'native_browser_version': browser.version})
        try:
            for width in widths:
                for name, check in CASES.items():
                    if selected != 'all' and selected != name:
                        continue
                    evidence = report / f'{width}-{name}'
                    evidence.mkdir()
                    context = browser.new_context(locale='zh-CN', timezone_id='UTC',
                                                  viewport={'width': width, 'height': 1000 if width > 600 else 844})
                    context.tracing.start(screenshots=True, snapshots=True, sources=True)
                    page = context.new_page()
                    errors, console = [], []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: console.append({'type': message.type, 'text': message.text}))
                    result = {'width': width, 'case': name, 'status': 'running'}
                    results.append(result)
                    try:
                        response = page.goto(url)
                        assert response and response.headers.get('content-security-policy'), 'Normal deployment CSP was not served'
                        wait_for_app_ready(page)
                        assert get_task_records(page) == [], 'A fresh synthetic profile contained task data'
                        add_task(page, '安全回归哨兵', description='所有其它记录必须保持', no_deadline=True, subtasks=['保留此ID与内容'])
                        save_json(evidence / 'initial.json', stored(page))
                        check(page, evidence)
                        assert not errors, errors
                        save_json(evidence / 'final.json', stored(page))
                        result['status'] = 'passed'
                        print(f'Editor safety passed: {width}px {name}', flush=True)
                    except Exception:
                        result.update({'status': 'failed', 'error': traceback.format_exc()})
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
    assert hashlib.sha256((root / 'index.html').read_bytes()).hexdigest() == initial_sha, 'Application source changed during the regression run'
    print(f'Editor safety passed: {len(results)} cases; evidence {report}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--widths', type=int, nargs='+', default=[1280, 390])
    parser.add_argument('--report-dir', type=Path, default=Path('/tmp/task-tracer-editor-safety/regression'))
    parser.add_argument('--expected-index-sha')
    args = parser.parse_args()
    run(args.browser, args.case, args.widths, args.report_dir, args.expected_index_sha)
