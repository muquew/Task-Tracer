#!/usr/bin/env python3
"""Keep composition keys in text input; verify normal keys still work afterward.

These are browser DOM composition/event regressions, not a native OS IME test.
"""
from __future__ import annotations

from smoke_playwright import ensure_capture, open_task_editor

import argparse

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import browser_launch_options, get_task_records, local_server, wait_for_app_ready


def key(locator, value, mode, event_type='keydown'):
    result = locator.evaluate("""(input, options) => {
        const event = new KeyboardEvent(options.type, {
            key: options.key, bubbles: true, cancelable: true,
            isComposing: options.mode === 'flag',
            keyCode: options.mode === 'legacy' ? 229 : 0
        });
        input.dispatchEvent(event);
        return {prevented: event.defaultPrevented, composing: event.isComposing, keyCode: event.keyCode};
    }""", {'key': value, 'mode': mode, 'type': event_type})
    if mode == 'flag':
        assert result['composing']
    if mode == 'legacy':
        assert result['keyCode'] == 229
    assert not result['prevented'], f'Application consumed composition key {value}: {result}'


def compose(locator, active):
    locator.dispatch_event('compositionstart' if active else 'compositionend', {'data': '中文'})


def palette(page, mode):
    page.keyboard.press('Control+p')
    field = page.locator('#commandPaletteInput')
    expect(field).to_be_focused()
    initial = field.get_attribute('aria-activedescendant')
    if mode == 'tracked':
        compose(field, True)
    for value in ('ArrowDown', 'End', 'Home', 'Enter', 'Escape'):
        key(field, value, mode)
        expect(page.locator('#commandPalette')).to_be_visible()
        expect(page.locator('#taskModal')).to_be_hidden()
        assert field.get_attribute('aria-activedescendant') == initial
    if mode == 'tracked':
        compose(field, False)
    page.keyboard.press('ArrowDown')
    assert field.get_attribute('aria-activedescendant') != initial
    page.keyboard.press('Home')
    expect(field).to_have_attribute('aria-activedescendant', initial)
    page.keyboard.press('Enter')
    expect(page.locator('#commandPalette')).to_be_hidden()
    expect(page.locator('#taskName')).to_be_visible()
    assert get_task_records(page) == []


def subtasks(page, mode):
    open_task_editor(page)
    page.locator('#taskName').fill('Composition task 中文')
    page.locator('#noDeadline').check()
    field = page.locator('#subtaskInput')
    field.fill('第一项中文组词')
    if mode == 'tracked':
        compose(field, True)
    key(field, 'Enter', mode, 'keypress')
    expect(field).to_have_value('第一项中文组词')
    expect(page.locator('.subtask-preview-item')).to_have_count(0)
    if mode == 'tracked':
        compose(field, False)
    field.press('Enter')
    expect(page.locator('.subtask-preview-item')).to_have_count(1)
    expect(field).to_have_value('')
    page.locator('.subtask-preview-text').click()
    inline = page.locator('.subtask-edit-input')
    expect(inline).to_be_focused()
    inline.fill('最终子任务中文')
    if mode == 'tracked':
        compose(inline, True)
    key(inline, 'Enter', mode)
    expect(inline).to_be_focused()
    expect(inline).to_have_value('最终子任务中文')
    if mode == 'tracked':
        compose(inline, False)
    inline.press('Enter')
    expect(page.locator('.subtask-edit-input')).to_have_count(0)
    expect(page.locator('.subtask-preview-text')).to_have_text('最终子任务中文')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    tasks = get_task_records(page)
    assert len(tasks) == 1 and tasks[0]['subtasks'][0]['text'] == '最终子任务中文'


def escape(page, mode):
    open_task_editor(page)
    field = page.locator('#taskName')
    field.fill('继续输入中文')
    if mode == 'tracked':
        compose(field, True)
    key(field, 'Escape', mode)
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
    expect(field).to_have_value('继续输入中文')
    if mode == 'tracked':
        compose(field, False)
    field.press('Escape')
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').click()
    expect(field).to_have_value('继续输入中文')
    assert get_task_records(page) == []


def search(page, mode):
    if page.locator('#searchInput').is_hidden():
        page.locator('#toolsDrawerToggleBtn').click()
    field = page.locator('#searchInput')
    field.fill('搜索中文')
    if mode == 'tracked':
        compose(field, True)
    key(field, 'Escape', mode)
    expect(field).to_have_value('搜索中文')
    expect(field).to_be_focused()
    if mode == 'tracked':
        compose(field, False)
    field.press('Escape')
    expect(field).to_have_value('')
    assert get_task_records(page) == []


def forms(page, mode):
    for task_form in (False, True):
        if task_form:
            open_task_editor(page)
            field = page.locator('#taskName')
            field.fill('完整表单中文')
            page.locator('#noDeadline').check()
            field.focus()
            form = page.locator('#taskForm')
        else:
            field = ensure_capture(page)
            field.fill('快速添加中文')
            form = page.locator('#quickAddForm')
        before = get_task_records(page)
        compose(field, True)
        form.evaluate('(form) => form.requestSubmit()')
        assert get_task_records(page) == before, 'A form saved an unfinished composition'
        expect(field).to_have_value('完整表单中文' if task_form else '快速添加中文')
        compose(field, False)
        field.press('Enter')
        page.wait_for_function("""expected => new Promise(resolve => {
            const open = indexedDB.open('TaskTrackerDB', 2);
            open.onsuccess = () => {
                const db = open.result;
                const tx = db.transaction('tasks');
                const request = tx.objectStore('tasks').count();
                request.onsuccess = () => resolve(request.result === expected);
                tx.oncomplete = () => db.close();
            };
        })""", arg=len(before) + 1)
        if task_form:
            expect(page.locator('#taskModal')).to_be_hidden()
        else:
            expect(field).to_have_value('')


CASES = {'palette': palette, 'subtasks': subtasks, 'escape': escape, 'search': search, 'forms': forms}


def run(engine, selected):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'Composition {engine}: {browser.version}', flush=True)
        for name, check in CASES.items():
            if selected != 'all' and name != selected:
                continue
            for mode in (('tracked',) if name == 'forms' else ('flag', 'legacy', 'tracked')):
                context = browser.new_context(locale='en-US')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url)
                wait_for_app_ready(page)
                check(page, mode)
                assert not errors, errors
                context.close()
            print(f'Composition passed: {name}; composition keys stay in text and ordinary keys still work', flush=True)
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
