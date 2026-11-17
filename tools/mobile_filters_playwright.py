#!/usr/bin/env python3
"""Exercise real mobile filter controls without duplicating their state or nodes.

Fresh synthetic tasks only. The filter sheet is inspected through normal clicks,
keyboard interaction, resizing, reloading and theme/language controls.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import (
    add_task, browser_launch_options, get_task_records, local_server,
    navigate_workbench, select_filter, select_language, select_theme_preference,
    task_locator, wait_for_app_ready,
)


def open_sheet(page):
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    page.locator('#toolsDrawerToggleBtn').click()
    expect(page.locator('#mobileFiltersDialog')).to_be_visible()
    expect(page.locator('#toolsDrawerToggleBtn')).to_have_attribute('aria-expanded', 'true')
    expect(page.locator('#mobileFiltersTitle')).to_be_focused()
    expect(page.locator('#mobileFiltersBody #toolsDrawerContent')).to_have_count(1)


def capture(page, output, name):
    notice = page.locator('#workspaceNotificationClose')
    if notice.is_visible() and not page.locator('#mobileFiltersDialog').is_visible():
        notice.click()
    page.screenshot(path=str(output / (name + '.png')), animations='disabled')


def expect_popup_inside_viewport(page, selector):
    page.wait_for_function('''selector => {
        const menu = document.querySelector(selector), box = menu.getBoundingClientRect();
        return menu.style.left && box.left >= 0 && box.right <= innerWidth
            && box.top >= 0 && box.bottom <= innerHeight;
    }''', arg=selector)


def check_controls(page, output):
    add_task(page, '整理本周研究笔记', description='整理阅读记录并补充引用。',
             no_deadline=True, project='研究')
    add_task(page, '完成评审材料', description='检查任务流程与手机体验。',
             no_deadline=True, project='工作')
    task_locator(page, '完成评审材料').locator('[data-action="toggle"]').click()
    select_filter(page, 'all')
    before = get_task_records(page)
    expect(page.locator('#taskList .task-item')).to_have_count(2)
    node = page.locator('#toolsDrawerContent').evaluate_handle('node => node')
    assert page.locator('#toolsDrawerContent').evaluate(
        'node => !node.closest("dialog")'), 'Closed sheet left task controls in a dialog'
    capture(page, output, '01-mobile-task-list')

    open_sheet(page)
    scroll_before = page.evaluate('scrollY')
    page.mouse.move(8, 100)
    page.mouse.wheel(0, 300)
    assert page.evaluate('scrollY') == scroll_before, 'Backdrop allowed task page to scroll'
    for _ in range(10):
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement === document.body || Boolean(document.activeElement.closest("#mobileFiltersDialog"))'), \
            'Native modal allowed keyboard focus into the task page'
    page.locator('#filterBtn').click()
    expect(page.locator('#filterMenu')).to_be_visible()
    expect_popup_inside_viewport(page, '#filterMenu')
    capture(page, output, '02-mobile-filter-options')
    page.locator('#filterMenu [data-filter="completed"]').click()
    expect(page.locator('#filterBtn')).to_be_focused()
    expect(page.locator('#filterMenu [data-filter="completed"]')).to_have_attribute('aria-selected', 'true')
    expect(page.locator('#mobileFiltersDialog')).to_be_visible()
    expect(page.locator('#taskList .task-item')).to_have_count(1)
    capture(page, output, '03-mobile-filters-applied')
    page.locator('#mobileFiltersDoneBtn').click()
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    expect(page.locator('#toolsDrawerToggleBtn')).to_be_focused()
    expect(task_locator(page, '完成评审材料')).to_be_visible()
    assert node.evaluate('node => node === document.getElementById("toolsDrawerContent")')
    assert get_task_records(page) == before, 'Filtering changed task data'

    open_sheet(page)
    page.locator('#filterBtn').click()
    page.keyboard.press('Escape')
    expect(page.locator('#filterMenu')).to_be_hidden()
    expect(page.locator('#mobileFiltersDialog')).to_be_visible()
    expect(page.locator('#filterBtn')).to_be_focused()
    page.keyboard.press('Escape')
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    expect(page.locator('#toolsDrawerToggleBtn')).to_be_focused()

    open_sheet(page)
    page.set_viewport_size({'width': 1280, 'height': 900})
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    assert page.locator('#toolsDrawerContent').evaluate(
        'node => node.parentElement.classList.contains("controls-bar")')
    if not page.locator('#toolsDrawerContent').is_visible():
        page.locator('#toolsDrawerToggleBtn').click()
    expect(page.locator('#filterMenu [data-filter="completed"]')).to_have_attribute('aria-selected', 'true')
    capture(page, output, '04-desktop-inline-filters')
    page.locator('#filterBtn').focus()
    page.set_viewport_size({'width': 320, 'height': 568})
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    expect(page.locator('#toolsDrawerContent')).to_be_hidden()
    expect(page.locator('#toolsDrawerToggleBtn')).to_be_focused()
    open_sheet(page)
    assert node.evaluate('node => node === document.getElementById("toolsDrawerContent")')
    expect(page.locator('#toolsDrawerContent')).to_have_count(1)
    expect(page.locator('#filterMenu [data-filter="completed"]')).to_have_attribute('aria-selected', 'true')
    expect(page.locator('#mobileFiltersCloseBtn')).to_be_in_viewport()
    expect(page.locator('#mobileFiltersDoneBtn')).to_be_in_viewport()
    capture(page, output, '05-compact-mobile-sheet')
    page.locator('#mobileFiltersDoneBtn').click()

    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    navigate_workbench(page, 'tasks')
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    assert get_task_records(page) == before, 'Reload changed task records'
    open_sheet(page)
    page.locator('#mobileFiltersCloseBtn').click()
    expect(page.locator('#toolsDrawerToggleBtn')).to_be_focused()
    select_language(page, 'en')
    navigate_workbench(page, 'tasks')
    select_theme_preference(page, 'dark')
    navigate_workbench(page, 'tasks')
    open_sheet(page)
    expect(page.locator('#mobileFiltersTitle')).to_have_text('Filters & sorting')
    page.locator('#sortBtn').click()
    expect(page.locator('#sortMenu')).to_be_visible()
    expect_popup_inside_viewport(page, '#sortMenu')
    capture(page, output, '06-english-dark-sort')
    page.locator('#sortMenu [data-sort="alpha-asc"]').click()
    page.locator('#mobileFiltersDoneBtn').click()
    page.keyboard.press('Control+i')
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#mobileFiltersDialog')).to_be_hidden()
    page.locator('#cancelBtn').click()
    if page.locator('#draftDiscardPrompt').is_visible():
        page.locator('#draftDiscardBtn').click()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    assert get_task_records(page) == before
    return ['single shared control node', 'immediate filtering without data writes',
            'native focus containment', 'dropdown Escape before sheet Escape',
            'Done and close restore focus', 'resize retains selected filter',
            'reload closes sheet and preserves tasks', '320px, English and dark states',
            'task editor opens after returning from filters']


def main(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    result = {'passed': False, 'browser': args.browser, 'page_errors': [],
              'scope': 'Isolated synthetic tasks; localhost only; actual UI events'}
    try:
        with local_server() as url, sync_playwright() as p:
            engine = getattr(p, args.browser)
            options = browser_launch_options(args.browser)
            browser = engine.launch(**options)
            result['browser_version'] = browser.version
            try:
                context = browser.new_context(viewport={'width': 390, 'height': 844},
                                              locale='zh-CN', reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: result['page_errors'].append(str(error)))
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    wait_for_app_ready(page)
                    result['checks'] = check_controls(page, output)
                    assert not result['page_errors'], result['page_errors']
                    result['passed'] = True
                except Exception:
                    page.screenshot(path=str(output / 'failure.png'), animations='disabled')
                    raise
                finally:
                    context.close()
            finally:
                browser.close()
    except Exception:
        result['error'] = traceback.format_exc()
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({'passed': result['passed'], 'report': str(output / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-mobile-filters'))
    main(parser.parse_args())
