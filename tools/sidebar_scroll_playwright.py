#!/usr/bin/env python3
"""Exercise a crowded sidebar through real capture, pointer and keyboard paths.

The workload is created by submitting forty quick captures and four saved views.
Only the normal empty-profile helper clears storage; no project, task or saved-view
records are injected, and no application limits or CSP settings are changed.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import traceback

from playwright.sync_api import expect, sync_playwright

from saved_views_playwright import save_view, stored_views
from smoke_playwright import (
    REPO_ROOT, browser_launch_options, clear_app_data, close_workspace_navigation,
    ensure_capture, get_task_records, local_server, return_to_task_workspace,
    task_locator, visible_task_names,
)


VIEWPORTS = ((1280, 720), (1280, 500), (390, 844), (320, 640))
LONG_PROJECT = 'Sidebar-40-' + '超长项目名称需要正常换行并保持所有操作始终可达' * 3
PROJECTS = [f'Sidebar-{index:02d}' for index in range(1, 40)] + [LONG_PROJECT]
TASKS = [f'Sidebar reachability task number_{index:02d}' for index in range(1, 41)]
SAVED_NAMES = [f'Sidebar saved view {index}' for index in range(1, 5)]


def settle(page):
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def project_control(page, project):
    return page.locator('#workspaceProjects [data-workspace-project]').filter(
        has=page.locator('.workspace-project-name', has_text=re.compile('^' + re.escape(project) + '$'))
    )


def open_navigation(page):
    toggle = page.locator('#workspaceNavToggle')
    if page.viewport_size['width'] < 780:
        expect(toggle).to_be_visible()
        if toggle.get_attribute('aria-expanded') != 'true':
            toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        expect(page.locator('#workspaceSidebar')).to_have_attribute('aria-hidden', 'false')
        settle(page)
    expect(page.locator('#workspaceSidebar')).to_be_visible()


def snapshot_geometry(page):
    return page.evaluate("""() => {
        const box = selector => {
            const node = document.querySelector(selector), r = node.getBoundingClientRect();
            return {top:r.top, bottom:r.bottom, left:r.left, right:r.right,
                width:r.width, height:r.height, scrollTop:node.scrollTop,
                scrollHeight:node.scrollHeight, clientHeight:node.clientHeight,
                scrollWidth:node.scrollWidth, clientWidth:node.clientWidth};
        };
        return {windowY:scrollY, windowX:scrollX, width:innerWidth, height:innerHeight,
            documentWidth:document.documentElement.scrollWidth,
            sidebar:box('#workspaceSidebar'), pane:box('#workspaceSidebarScroll'),
            settings:box('#workspaceSettingsBtn'), footer:box('.workspace-sidebar-footer'),
            brand:box('.workspace-brand'), viewHost:box('#workspaceViewNavHost')};
    }""")


def assert_fixed(before, after, *, mobile):
    for name in ('settings', 'footer', 'brand') + (() if mobile else ('viewHost',)):
        for edge in ('top', 'bottom', 'left', 'right'):
            assert abs(before[name][edge] - after[name][edge]) <= 1, \
                f'{name} moved while the sidebar content scrolled: {before[name]} -> {after[name]}'
    assert after['windowY'] == before['windowY'], 'Sidebar scrolling also moved the main page'
    assert after['windowX'] == before['windowX'], 'Sidebar scrolling moved the page horizontally'
    assert after['sidebar']['scrollTop'] == 0, 'The entire sidebar scrolled instead of its middle pane'


def assert_footer(page, geometry):
    sidebar, footer, settings, pane = [geometry[key] for key in ('sidebar', 'footer', 'settings', 'pane')]
    assert footer['bottom'] <= sidebar['bottom'] + 1
    assert sidebar['bottom'] - footer['bottom'] <= 36, f'Footer is not anchored near the sidebar bottom: {geometry}'
    assert settings['top'] >= pane['bottom'] - 1, 'Settings overlaps the scrollable project area'
    assert settings['bottom'] <= sidebar['bottom'] + 1
    assert sidebar['bottom'] - settings['bottom'] <= 110, f'Settings is far from the sidebar bottom: {geometry}'
    expect(page.locator('#workspaceSettingsBtn')).to_be_in_viewport(ratio=1)


def assert_reachable(page, control):
    geometry = control.evaluate("""node => {
        const r = node.getBoundingClientRect(), p = node.closest('#workspaceSidebarScroll').getBoundingClientRect();
        return {center:(r.top+r.bottom)/2, top:p.top, bottom:p.bottom,
            x:(p.left+p.right)/2, y:(p.top+p.bottom)/2};
    }""")
    if not geometry['top'] + 8 <= geometry['center'] <= geometry['bottom'] - 8:
        page.mouse.move(geometry['x'], geometry['y'])
        page.mouse.wheel(0, geometry['center'] - geometry['y'])
        page.wait_for_function("""node => {
            const r = node.getBoundingClientRect(), p = node.closest('#workspaceSidebarScroll').getBoundingClientRect();
            return (r.top+r.bottom)/2 >= p.top && (r.top+r.bottom)/2 <= p.bottom;
        }""", arg=control.element_handle())
    settle(page)
    expect(control).to_be_in_viewport()
    result = control.evaluate("""node => {
        const r = node.getBoundingClientRect(), pane = node.closest('#workspaceSidebarScroll');
        const p = pane.getBoundingClientRect();
        const left = Math.max(r.left, p.left), right = Math.min(r.right, p.right);
        const top = Math.max(r.top, p.top), bottom = Math.min(r.bottom, p.bottom);
        const x = (left + right) / 2, y = (top + bottom) / 2;
        const target = document.elementFromPoint(x, y);
        return {visibleHeight:bottom-top, visibleWidth:right-left,
            hit:target === node || node.contains(target),
            width:r.width, paneWidth:p.width, text:node.textContent};
    }""")
    assert result['visibleHeight'] >= 16 and result['visibleWidth'] > 0 and result['hit'], \
        f'Sidebar item cannot be reached through its scroll pane: {result}'


def assert_focus_visible(page):
    result = page.evaluate("""() => {
        const node = document.activeElement, r = node.getBoundingClientRect();
        const pane = node.closest('#workspaceSidebarScroll');
        const clip = pane ? pane.getBoundingClientRect() : {top:0,bottom:innerHeight,left:0,right:innerWidth};
        const top = Math.max(r.top, clip.top, 0), bottom = Math.min(r.bottom, clip.bottom, innerHeight);
        const left = Math.max(r.left, clip.left, 0), right = Math.min(r.right, clip.right, innerWidth);
        const target = document.elementFromPoint((left+right)/2, (top+bottom)/2);
        return {id:node.id, project:node.dataset.workspaceProject || '', tag:node.tagName,
            text:node.textContent, top:r.top, bottom:r.bottom, visibleHeight:bottom-top,
            hit:node === target || node.contains(target), inSidebar:Boolean(node.closest('#workspaceSidebar'))};
    }""")
    assert result['inSidebar'] and result['visibleHeight'] >= 16 and result['hit'], \
        f'Keyboard focus is hidden or outside the navigation: {result}'
    return result


def build_workload(page):
    started = time.perf_counter()
    field = ensure_capture(page)
    for index, (project, task) in enumerate(zip(PROJECTS, TASKS), start=1):
        field.fill(f'{task} /{project}')
        field.press('Enter')
        expect(field).to_have_value('')
        expect(task_locator(page, task)).to_have_count(1)
        if index % 10 == 0:
            print(f'Sidebar workload: {index}/40 projects created through quick capture', flush=True)
    if page.locator('#captureShelf').is_visible():
        page.locator('#captureCloseBtn').click()
    for index, name in enumerate(SAVED_NAMES, start=1):
        save_view(page, name, f'number_{index:02d}')
    page.locator('#searchInput').fill('')
    expect(page.locator('.task-item .task-name')).to_have_count(40)
    settle(page)
    expect(page.locator('#workspaceProjects [data-workspace-project]')).to_have_count(40)
    assert len(stored_views(page)) == 4
    records = get_task_records(page)
    assert len(records) == 40 and {task['project'] for task in records} == set(PROJECTS)
    assert {task['name'] for task in records} == set(TASKS)
    return {'projects':40, 'tasks':40, 'saved_views':4,
            'created_through':'40 quick-capture submissions and 4 saved-view forms',
            'seconds':round(time.perf_counter() - started, 2)}, records


def check_scroll_and_reachability(page, entry):
    mobile = page.viewport_size['width'] < 780
    open_navigation(page)
    pane = page.locator('#workspaceSidebarScroll')
    expect(pane).to_have_count(1)
    assert page.locator('#workspaceSettingsBtn').evaluate("node => Boolean(node.closest('.workspace-sidebar-footer'))")
    assert not page.locator('#workspaceSettingsBtn').evaluate("node => Boolean(node.closest('#workspaceSidebarScroll'))")
    assert pane.locator('#workspaceAllTasks').count() == 1 and pane.locator('#focusModeToggleBtn').count() == 1
    assert pane.locator('#workspaceProjects').count() == 1 and pane.locator('#savedViewsList').count() == 1
    expect(pane.locator('#workspaceProjects [data-workspace-project]')).to_have_count(40)
    before = snapshot_geometry(page)
    entry['geometry'] = {'before':before}
    assert before['pane']['scrollHeight'] > before['pane']['clientHeight'] + 500, 'Crowded sidebar did not overflow its middle pane'
    assert before['pane']['clientHeight'] >= 60, f'Scrollable navigation has too little usable height: {before}'
    assert_footer(page, before)

    rect = pane.bounding_box()
    page.mouse.move(rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2)
    page.mouse.wheel(0, 8000)
    page.wait_for_function("() => { const node = document.querySelector('#workspaceSidebarScroll'); return node.scrollTop >= node.scrollHeight - node.clientHeight - 2; }")
    settle(page)
    bottom = snapshot_geometry(page)
    entry['geometry']['at_bottom'] = bottom
    assert_fixed(before, bottom, mobile=mobile)
    assert_footer(page, bottom)
    page.mouse.wheel(0, 2000)
    settle(page)
    assert_fixed(bottom, snapshot_geometry(page), mobile=mobile)
    for name in SAVED_NAMES:
        control = page.locator('#savedViewsList .saved-view-chip').filter(
            has=page.locator('.saved-view-name', has_text=name)).locator('.saved-view-apply')
        assert_reachable(page, control)
    for project in PROJECTS:
        assert_reachable(page, project_control(page, project))
    final = snapshot_geometry(page)
    assert_fixed(before, final, mobile=mobile)
    assert_footer(page, final)
    assert final['documentWidth'] <= final['width'], 'Sidebar workload causes horizontal page overflow'
    assert final['pane']['scrollWidth'] <= final['pane']['clientWidth'] + 1, 'Sidebar content overflows horizontally'
    long_name = project_control(page, LONG_PROJECT).locator('.workspace-project-name')
    text = long_name.evaluate("""node => {
        const style = getComputedStyle(node), r = node.getBoundingClientRect();
        return {height:r.height, lineHeight:parseFloat(style.lineHeight),
            scrollWidth:node.scrollWidth, clientWidth:node.clientWidth, text:node.textContent};
    }""")
    assert text['height'] > text['lineHeight'] * 1.5, f'Long project name did not wrap: {text}'
    assert text['scrollWidth'] <= text['clientWidth'] + 1, f'Long project name overflows horizontally: {text}'
    entry['geometry'] = {'before':before, 'at_bottom':bottom, 'after_reaching_all':final, 'long_name':text}


def check_filter_targets(page):
    reached = []
    for index in (0, 19, 39):
        open_navigation(page)
        button = project_control(page, PROJECTS[index])
        assert_reachable(page, button)
        button.click()
        expect(project_control(page, PROJECTS[index])).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('.task-item .task-name')).to_have_count(1)
        assert visible_task_names(page) == [TASKS[index]], 'Sidebar project opened the wrong task scope'
        reached.append(PROJECTS[index])
        if page.viewport_size['width'] < 780:
            expect(page.locator('#workspaceNavToggle')).to_have_attribute('aria-expanded', 'false')
            expect(page.locator('#workspaceNavToggle')).to_be_focused()
    return reached


def check_keyboard(page):
    open_navigation(page)
    page.locator('#workspaceAllTasks').focus()
    focused = [assert_focus_visible(page)]
    reached_projects = set()
    for _ in range(70):
        page.keyboard.press('Tab')
        settle(page)
        current = assert_focus_visible(page)
        focused.append(current)
        if current['project']:
            reached_projects.add(json.loads(current['project'])['name'])
        if current['id'] == 'workspaceSettingsBtn':
            break
    assert focused[-1]['id'] == 'workspaceSettingsBtn', 'Keyboard did not reach the fixed Settings entry'
    assert reached_projects == set(PROJECTS), 'Keyboard skipped project controls in the scrollable sidebar'
    page.keyboard.press('Enter')
    expect(page.locator('#settingsWorkspace')).to_be_visible()
    return_to_task_workspace(page)
    return {'focus_stops':len(focused), 'project_controls_reached':len(reached_projects), 'settings_enter_activated':True}


def check_views_and_settings(page):
    mobile = page.viewport_size['width'] < 780
    close_workspace_navigation(page)
    for view in ('calendar', 'timeline', 'stats', 'list'):
        button = page.locator(f'#viewTab-{view}')
        expect(button).to_be_in_viewport(ratio=1)
        button.click()
        expect(button).to_have_attribute('aria-current', 'page')
    open_navigation(page)
    settings = page.locator('#workspaceSettingsBtn')
    settings.click()
    expect(page.locator('#settingsWorkspace')).to_be_visible()
    if mobile:
        expect(page.locator('#workspaceNavToggle')).to_have_attribute('aria-expanded', 'false')
    return_to_task_workspace(page)


def check_mobile_reopen(page):
    if page.viewport_size['width'] >= 780:
        return None
    open_navigation(page)
    selected = project_control(page, LONG_PROJECT)
    expect(selected).to_have_attribute('aria-pressed', 'true')
    expect(selected).to_be_focused()
    assert_focus_visible(page)
    scroll_before = page.locator('#workspaceSidebarScroll').evaluate('node => node.scrollTop')
    assert scroll_before > 0, 'Reopening the last project did not reveal its position in the scroll pane'
    page.keyboard.press('Escape')
    toggle = page.locator('#workspaceNavToggle')
    expect(toggle).to_have_attribute('aria-expanded', 'false')
    expect(toggle).to_be_focused()
    toggle.click()
    expect(toggle).to_have_attribute('aria-expanded', 'true')
    settle(page)
    expect(project_control(page, LONG_PROJECT)).to_be_focused()
    assert_focus_visible(page)
    page.locator('#workspaceNavBackdrop').click(position={'x':page.viewport_size['width'] - 4, 'y':100})
    expect(toggle).to_have_attribute('aria-expanded', 'false')
    expect(toggle).to_be_focused()
    return {'selected_scope_focused_on_open':True, 'selected_scroll_top':scroll_before,
            'escape_and_backdrop_restore_toggle_focus':True}


def check_notice_does_not_cover_settings(page, output):
    before = get_task_records(page)
    views_before = stored_views(page)
    open_navigation(page)
    apply = page.locator('#savedViewsList .saved-view-chip').filter(
        has=page.locator('.saved-view-name', has_text=SAVED_NAMES[0])).locator('.saved-view-apply')
    assert_reachable(page, apply)
    apply.click()
    expect(page.locator('.task-item .task-name')).to_have_count(1)
    assert visible_task_names(page) == [TASKS[0]], 'The notice scenario did not apply the real saved view'
    notice = page.locator('#notification')
    expect(notice).to_have_class(re.compile(r'\bshow\b'))
    expect(notice).to_have_class(re.compile(r'\bsuccess\b'))
    expect(page.locator('#notificationText')).to_contain_text(SAVED_NAMES[0])
    expect(notice).to_be_visible()
    mobile = page.viewport_size['width'] < 780
    if mobile:
        open_navigation(page)
        # The notice remains active, while the real drawer suppresses its background overlay.
        expect(notice).to_have_class(re.compile(r'\bshow\b'))
        expect(notice).to_be_hidden()
    observed = page.locator('#workspaceSettingsBtn').evaluate("""node => {
        const r = node.getBoundingClientRect(), x = (r.left+r.right)/2, y = (r.top+r.bottom)/2;
        const hit = document.elementFromPoint(x,y), notice = document.querySelector('#notification');
        const n = notice.getBoundingClientRect();
        return {x,y,hit:hit === node || node.contains(hit),hitId:hit?.id || '',
            settings:{left:r.left,right:r.right,top:r.top,bottom:r.bottom},
            notice:{left:n.left,right:n.right,top:n.top,bottom:n.bottom,
                visibility:getComputedStyle(notice).visibility,active:notice.classList.contains('show')}};
    }""")
    assert observed['notice']['active'], 'The success notice expired before the Settings overlap check'
    assert observed['hit'], f'The active success notice blocks the fixed Settings entry: {observed}'
    if mobile:
        assert observed['notice']['visibility'] == 'hidden', 'The background notice stays visible over the open drawer'
    else:
        assert observed['notice']['left'] >= observed['settings']['right'], 'Desktop notice still overlaps the sidebar column'
    width, height = page.viewport_size['width'], page.viewport_size['height']
    page.screenshot(path=str(output / f'{width}x{height}-notice-settings.png'))
    page.mouse.click(observed['x'], observed['y'])
    expect(page.locator('#settingsWorkspace')).to_be_visible()
    observed['pointer_settings_opened'] = True
    return_to_task_workspace(page)
    open_navigation(page)
    all_tasks = page.locator('#workspaceAllTasks')
    assert_reachable(page, all_tasks)
    all_tasks.click()
    page.locator('#searchInput').fill('')
    expect(page.locator('.task-item .task-name')).to_have_count(40)
    settle(page)
    assert get_task_records(page) == before, 'Applying the saved view or opening Settings changed task records'
    assert stored_views(page) == views_before, 'The overlay scenario rewrote saved views'
    return observed


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256((REPO_ROOT / 'index.html').read_bytes()).hexdigest()
    report = {'started_at':datetime.now(timezone.utc).isoformat(), 'index_sha256':source_hash,
              'passed':False, 'runs':[], 'workload_injected':False, 'csp_bypassed':False}
    server = contextlib.nullcontext(args.url) if args.url else local_server()
    try:
        with server as url, sync_playwright() as playwright:
            options = browser_launch_options()
            options['executable_path'] = args.executable
            browser = playwright.chromium.launch(**options)
            report['browser'] = {'engine':'chromium', 'version':browser.version, 'executable':args.executable}
            context = browser.new_context(viewport={'width':1280, 'height':720}, timezone_id='UTC', reduced_motion='reduce')
            page = context.new_page()
            page_errors, console_errors = [], []
            page.on('pageerror', lambda error:page_errors.append(str(error)))
            page.on('console', lambda message:console_errors.append(message.text) if message.type == 'error' else None)
            report['page_errors'], report['console_errors'] = page_errors, console_errors
            try:
                clear_app_data(page, url)
                report['workload'], baseline = build_workload(page)
                for width, height in VIEWPORTS:
                    page.set_viewport_size({'width':width, 'height':height})
                    settle(page)
                    entry = {'width':width, 'height':height, 'passed':False, 'checks':[]}
                    report['runs'].append(entry)
                    try:
                        for name, check in (
                            ('fixed top and bottom, independent middle scroll, all projects and saved views reachable, long name wraps',
                             lambda:check_scroll_and_reachability(page, entry)),
                            ('first, middle and final project open the correct task scope',
                             lambda:entry.update(filter_targets=check_filter_targets(page))),
                            ('every project is keyboard reachable with visible focus and Enter opens fixed Settings',
                             lambda:entry.update(keyboard=check_keyboard(page))),
                            ('four task views and bottom Settings remain actionable',
                             lambda:check_views_and_settings(page)),
                            ('mobile reopen focuses selected project; Escape and backdrop restore toggle focus',
                             lambda:entry.update(mobile_reopen=check_mobile_reopen(page))),
                            ('active saved-view success notice leaves fixed Settings directly pointer actionable',
                             lambda:entry.update(notice_overlay=check_notice_does_not_cover_settings(page, args.output))),
                        ):
                            started = time.perf_counter()
                            check()
                            entry['checks'].append({'name':name, 'passed':True, 'seconds':round(time.perf_counter()-started, 2)})
                            print(f'Sidebar {width}x{height} passed: {name}', flush=True)
                        assert get_task_records(page) == baseline, 'Sidebar navigation changed stored task records'
                        assert len(stored_views(page)) == 4, 'Sidebar navigation changed saved views'
                        assert not page_errors, page_errors
                        assert not console_errors, console_errors
                        open_navigation(page)
                        page.screenshot(path=str(args.output / f'{width}x{height}-sidebar.png'))
                        close_workspace_navigation(page)
                        page.screenshot(path=str(args.output / f'{width}x{height}-workspace.png'))
                        entry['passed'] = True
                    except Exception:
                        page.screenshot(path=str(args.output / f'{width}x{height}-failure.png'))
                        raise
                assert hashlib.sha256((REPO_ROOT / 'index.html').read_bytes()).hexdigest() == source_hash, 'Application source changed during sidebar acceptance'
                report['passed'] = True
            finally:
                context.close()
                browser.close()
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-4.13.2-sidebar'))
    parser.add_argument('--url')
    parser.add_argument('--executable', default='/usr/bin/chromium')
    run(parser.parse_args())
