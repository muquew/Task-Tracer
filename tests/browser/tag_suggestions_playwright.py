#!/usr/bin/env python3
"""Use existing tags through real editor input, pointer and keyboard actions.

Composition checks cover browser DOM events; they do not emulate an OS keyboard.
"""
from __future__ import annotations
from tests.support.browser import reveal_task_field

import argparse
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright
from tests.support.ime_input import key as composition_key
from tests.support.browser import (
    add_task,
    browser_launch_options,
    get_task_records,
    import_payload_replace,
    open_task_editor,
    return_to_task_workspace,
    task_locator,
    wait_for_app_ready,
)
from tests.support.http import local_server


def exercise(page, output):
    known = ['设计评审', '重点, 复盘', '引用"标签', '深度 工作', '本周重点']
    add_task(page, '已有标签资料', no_deadline=True)
    task_locator(page, '已有标签资料').locator('[data-task-open]').click()
    field = reveal_task_field(page, '#taskTags')
    field.fill('设计评审, "重点, 复盘", "引用""标签", 深度 工作, 本周重点')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    before = get_task_records(page)
    assert before[0]['tags'] == known

    open_task_editor(page)
    reveal_task_field(page, '#taskTags')
    expect(field).to_have_attribute('aria-expanded', 'false')
    field.focus()
    options = page.locator('#taskTagSuggestions [role="option"]')
    expect(options).to_have_count(5)
    expect(field).to_be_focused()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert get_task_records(page) == before, 'Focusing tag candidates wrote a task or tag'

    open_task_editor(page)
    reveal_task_field(page, '#taskTags')
    page.locator('#taskName').fill('复用标签验收')
    reveal_task_field(page, '#noDeadline').check()
    reveal_task_field(page, '#taskTags')
    field.fill('自由输入, 设计')
    expect(options).to_have_count(1)
    field.press('ArrowDown')
    expect(field).to_have_attribute('aria-activedescendant', 'task-tag-suggestion-0')
    expect(options.first).to_have_attribute('aria-selected', 'true')
    page.screenshot(path=str(output / '01-desktop-keyboard-candidate.png'), animations='disabled')
    field.press('Enter')
    expect(field).to_have_value('自由输入, 设计评审, ')
    expect(field).to_be_focused()
    expect(page.locator('#taskModal')).to_be_visible()
    assert get_task_records(page) == before, 'Selecting a suggestion prematurely saved the task'

    raw = '"重点, 复盘", 深度 工, "引用""标签"'
    field.fill(raw)
    field.press('Home')
    for _ in range(raw.index('深度 工') + len('深度 工')):
        field.press('ArrowRight')
    expect(options).to_have_count(1)
    field.press('ArrowUp')
    field.press('Enter')
    expect(field).to_have_value('"重点, 复盘", 深度 工作, "引用""标签"')

    field.fill('设计评审, "重点, 复')
    expect(options).to_have_text(['重点, 复盘'])
    field.press('ArrowUp')
    field.press('Enter')
    expect(field).to_have_value('设计评审, "重点, 复盘", ')
    field.fill('设计评审, 设')
    expect(page.locator('#taskTagSuggestions')).to_be_hidden()
    field.fill('一个全新标签')
    expect(page.locator('#taskTagSuggestions')).to_be_hidden()

    field.fill('引用')
    expect(options).to_have_text(['引用"标签'])
    options.first.click()
    expect(field).to_have_value('"引用""标签", ')
    expect(field).to_be_focused()
    field.fill('设计')
    field.press('Escape')
    expect(page.locator('#taskTagSuggestions')).to_be_hidden()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#draftDiscardPrompt')).to_be_hidden()
    field.press('Escape')
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').click()
    expect(field).to_be_focused()
    field.fill('深度')
    expect(page.locator('#taskTagSuggestions')).to_be_visible()
    field.press('Tab')
    expect(page.locator('#taskTagSuggestions')).to_be_hidden()
    expect(field).not_to_be_focused()
    expect(page.locator('#taskModal')).to_be_visible()

    for width, height, screenshot in ((320, 568, '02-compact-candidate-bounds'), (390, 420, '03-reduced-height-candidates')):
        page.set_viewport_size({'width': width, 'height': height})
        field.fill('')
        expect(options).to_have_count(5)
        page.wait_for_function('''() => {
            const input = document.querySelector('#taskTags').getBoundingClientRect();
            const menu = document.querySelector('#taskTagSuggestions').getBoundingClientRect();
            const actions = document.querySelector('#taskForm .dialog-actions').getBoundingClientRect();
            const form = document.querySelector('#taskForm').getBoundingClientRect();
            return input.bottom <= actions.top && menu.top >= form.top
                && menu.bottom <= actions.top && menu.right <= innerWidth;
        }''')
        field.press('ArrowUp')
        expect(options.last).to_have_attribute('aria-selected', 'true')
        last = options.last.text_content()
        page.screenshot(path=str(output / (screenshot + '.png')), animations='disabled')
        field.press('Enter')
        assert last in field.input_value()
        expect(field).to_be_focused()

    page.set_viewport_size({'width': 390, 'height': 844})
    field.fill('设计')
    field.dispatch_event('compositionstart', {'data': '设'})
    for value in ('ArrowDown', 'Enter', 'Escape'):
        composition_key(field, value, 'tracked')
    expect(field).to_have_value('设计')
    expect(page.locator('#taskTagSuggestions')).to_be_hidden()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#draftDiscardPrompt')).to_be_hidden()
    assert get_task_records(page) == before
    field.dispatch_event('compositionend', {'data': '设计'})
    expect(options).to_have_text(['设计评审'])
    page.screenshot(path=str(output / '04-mobile-composition-ended.png'), animations='disabled')
    options.first.tap()
    expect(field).to_have_value('设计评审, ')
    expect(field).to_be_focused()
    field.fill('设计评审, "重点, 复盘", 引用')
    expect(options).to_have_text(['引用"标签'])
    options.first.tap()
    expect(field).to_have_value('设计评审, "重点, 复盘", "引用""标签", ')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    saved = next(task for task in get_task_records(page) if task['name'] == '复用标签验收')
    assert saved['tags'] == ['设计评审', '重点, 复盘', '引用"标签']
    task_locator(page, '复用标签验收').locator('[data-task-open]').click()
    expect(field).to_have_value('设计评审, "重点, 复盘", "引用""标签"')
    page.locator('#cancelBtn').click()

    open_task_editor(page)
    reveal_task_field(page, '#taskTags')
    page.locator('#taskName').fill('未选任何候选')
    reveal_task_field(page, '#noDeadline').check()
    field.focus()
    expect(options).to_have_count(5)
    field.press('Enter')
    expect(page.locator('#taskModal')).to_be_hidden()
    empty = next(task for task in get_task_records(page) if task['name'] == '未选任何候选')
    assert empty['tags'] == [], 'Submitting an untouched tags field accepted a suggestion'

    import_payload_replace(page, [{'id': 31, 'name': '导入后标签资料', 'tags': ['导入的新标签']}])
    return_to_task_workspace(page)
    open_task_editor(page)
    reveal_task_field(page, '#taskTags')
    field.fill('设计')
    expect(page.locator('#taskTagSuggestions')).to_be_hidden()
    field.fill('导入')
    expect(options).to_have_text(['导入的新标签'])
    page.locator('#cancelBtn').click()
    page.locator('#draftDiscardBtn').click()
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    return_to_task_workspace(page)
    open_task_editor(page)
    reveal_task_field(page, '#taskTags')
    field.fill('导入')
    expect(options).to_have_text(['导入的新标签'])
    page.screenshot(path=str(output / '05-imported-candidate-after-reload.png'), animations='disabled')
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    return ['existing tags only, no implicit selection', 'ArrowDown/Up and Enter keep input focus',
            'middle-token replacement preserves quoted neighbours', 'comma and quote roundtrip',
            'existing tags excluded, free text accepted', 'Escape before editor dismissal; natural Tab',
            'DOM composition does not select or submit', 'mouse and mobile touch selection',
            '320x568 and reduced 390x420 height keep candidates and input above footer',
            'import invalidates names; reload restores candidates']


def main(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'passed': False, 'browser': args.browser, 'page_errors': [],
              'limits': 'Synthetic viewports and DOM composition events, not an OS IME or mobile keyboard.'}
    try:
        with local_server() as url, sync_playwright() as p:
            options = browser_launch_options(args.browser)
            browser = getattr(p, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                context = browser.new_context(viewport={'width': 1280, 'height': 900}, has_touch=True,
                                              locale='zh-CN', reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    wait_for_app_ready(page)
                    report['checks'] = exercise(page, output)
                    assert not report['page_errors'], report['page_errors']
                    report['passed'] = True
                except Exception:
                    page.screenshot(path=str(output / 'failure.png'), animations='disabled')
                    raise
                finally:
                    context.close()
            finally:
                browser.close()
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'passed': report['passed'], 'report': str(output / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-tag-suggestions'))
    main(parser.parse_args())
