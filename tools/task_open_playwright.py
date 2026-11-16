#!/usr/bin/env python3
"""Exercise direct task opening, keyboard activation and focus after rerendering."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, click_task_action, get_task_records,
    local_server, select_filter, select_view, task_locator, wait_for_app_ready,
)


def exercise(page, output):
    name = '直接打开产品评审'
    add_task(page, name, description='检查标题打开、保存和焦点返回。',
             due_date='2035-06-14', project='应用完善', tags=['评审'], subtasks=['核对入口'])
    add_task(page, '归档参考记录', no_deadline=True)
    before = get_task_records(page)
    title = task_locator(page, name).locator('[data-task-open]')
    expect(title).to_have_role('button')
    expect(title).to_have_attribute('type', 'button')
    expect(task_locator(page, name).locator('[data-action="edit"]')).to_have_count(1)
    title.click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value(name)
    expect(page.locator('#taskName')).to_be_focused()
    page.locator('#cancelBtn').click()
    expect(title).to_be_focused()
    assert get_task_records(page) == before

    title.press('Enter')
    expect(page.locator('#taskModal')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(title).to_be_focused()
    title.press('Space')
    expect(page.locator('#taskModal')).to_be_visible()
    updated_name = name + ' · 已完善'
    page.locator('#taskName').fill(updated_name)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    updated_title = task_locator(page, updated_name).locator('[data-task-open]')
    expect(updated_title).to_be_focused()
    expect(updated_title).to_have_text(updated_name)
    page.locator('#undoBtn').click()
    expect(task_locator(page, name)).to_have_count(1)
    assert get_task_records(page) == before, 'Undo did not restore the exact pre-edit task records'
    page.screenshot(path=str(output / '01-desktop-direct-task.png'), animations='disabled')

    page.set_viewport_size({'width': 390, 'height': 844})
    title.click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.screenshot(path=str(output / '02-mobile-direct-editor.png'), animations='disabled')
    page.locator('#taskName').fill('尚未保存的修改')
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(title).to_be_focused()
    assert get_task_records(page) == before, 'Discarding direct edit changed task records'
    select_view(page, 'timeline')
    title.click()
    expect(page.locator('#taskName')).to_have_value(name)
    page.locator('#cancelBtn').click()
    expect(title).to_be_focused()
    select_view(page, 'list')

    archive = task_locator(page, '归档参考记录')
    click_task_action(archive, 'toggle')
    select_filter(page, 'completed')
    click_task_action(archive, 'archive')
    expect(archive).to_have_count(0)
    select_filter(page, 'archived')
    archived_title = archive.locator('[data-task-open]')
    expect(archived_title).to_be_disabled()
    bounds = archived_title.bounding_box()
    assert bounds
    page.mouse.click(bounds['x'] + bounds['width'] / 2, bounds['y'] + bounds['height'] / 2)
    expect(page.locator('#taskModal')).to_be_hidden()
    page.screenshot(path=str(output / '03-archived-title.png'), animations='disabled')
    click_task_action(archive, 'archive')
    select_filter(page, 'completed')
    expect(archive.locator('[data-task-open]')).to_be_enabled()
    archive.locator('[data-task-open]').click()
    expect(page.locator('#taskName')).to_have_value('归档参考记录')
    page.locator('#cancelBtn').click()
    expect(archive.locator('[data-task-open]')).to_be_focused()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    return ['click and native Enter/Space open task', 'menu edit remains a separate action',
            'Cancel/Escape/discard return to title', 'save rerender resolves title focus by task id',
            'undo restores exact pre-edit records', '390px and timeline direct opening',
            'archived title is inert; restoring enables it']


def main(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'passed': False, 'browser': args.browser, 'page_errors': []}
    try:
        with local_server() as url, sync_playwright() as p:
            options = browser_launch_options(args.browser)
            browser = getattr(p, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                context = browser.new_context(viewport={'width': 1280, 'height': 900},
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
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-task-open'))
    main(parser.parse_args())
