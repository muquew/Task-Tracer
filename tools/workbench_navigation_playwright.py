#!/usr/bin/env python3
"""Exercise the five-page workbench with real creation and unchanged data checks."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from check import source_identity, verification_identity
from recovery_management_playwright import stored
from smoke_playwright import (
    browser_launch_options, get_task_records, is_workbench_v5, local_server,
    navigate_workbench, open_settings, open_task_editor, select_project,
    select_view, task_locator, wait_for_app_ready, workbench_screen,
)


TODAY = '2039-02-15'
TOMORROW = '2039-02-16'
NAMES = {
    'today': 'Today capture',
    'library': 'Library capture',
    'both': 'Planned and due',
    'future': 'Planned tomorrow',
    'due': 'Deadline only',
}


def dismiss_notice(page):
    close = page.locator('#workspaceNotificationClose')
    if close.is_visible():
        close.click()


def capture(page, output, name):
    dismiss_notice(page)
    page.wait_for_function("""() => document.getAnimations().every(animation =>
        animation.playState !== 'running' || animation.effect?.getComputedTiming().iterations === Infinity)""")
    page.screenshot(path=str(output / f'{name}.png'), full_page=False)


def assert_active_page(page, screen):
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', screen)
    expect(page.locator('main h1:visible')).to_have_count(1)
    assert page.locator('main h1:visible').inner_text().strip(), 'Active page has no heading'
    if screen == 'review':
        language = page.locator('html').get_attribute('lang')
        translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
        expect(page.locator('#workspaceTitle')).to_have_text(translations['v5.nav.review'])
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Workbench overflows the viewport'
    assert page.evaluate("""() => !document.activeElement?.closest('[hidden],[inert],[aria-hidden="true"]')"""), 'Navigation left focus in a hidden page'
    for selector in ('#todayWorkspace', '#projectsWorkspace', '#tasksWorkspace', '#settingsWorkspace'):
        panel = page.locator(selector)
        if panel.count() and not panel.is_visible():
            expect(panel).to_have_js_property('inert', True)
    desktop, mobile = {
        'today': ('#workspaceTodayBtn', '#mobileTodayBtn'),
        'tasks': ('#workspaceAllTasks', '#mobileTasksBtn'),
        'projects': ('#workspaceProjectsBtn', '#mobileProjectsBtn'),
        'review': ('#viewTab-stats', '#mobileReviewBtn'),
        'settings': ('#workspaceSettingsBtn', '#workspaceSettingsBtn'),
    }[screen]
    active = page.locator(mobile) if page.locator(mobile).is_visible() else page.locator(desktop)
    if active.is_visible():
        expect(active).to_have_attribute('aria-current', 'page')


def create_on_current_page(page, name, *, project=None, deadline=None):
    """A global Add must honor the current page; no helper changes its scope."""
    before = get_task_records(page)
    origin = workbench_screen(page)
    open_task_editor(page, preserve_context=True)
    expect(page.locator('#taskName')).to_be_focused()
    expect(page.locator('#noDeadline')).to_be_checked()
    if project is None:
        expect(page.locator('#taskProject')).to_have_value('')
    else:
        page.locator('#taskProject').fill(project)
    page.locator('#taskName').fill(name)
    if deadline:
        page.locator('#noDeadline').uncheck()
        page.locator('#dueDate').fill(deadline)
        page.locator('#dueTime').fill('10:00')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', origin)
    after = get_task_records(page)
    added = [task for task in after if task['id'] not in {old['id'] for old in before}]
    assert len(after) == len(before) + 1 and len(added) == 1, 'Creation saved zero or duplicate tasks'
    assert all(task in after for task in before), 'Creation changed a prior task'
    assert added[0]['name'] == name
    return added[0]


def check_first_creation_and_today(page, output, checks):
    assert is_workbench_v5(page)
    assert_active_page(page, 'today')
    assert get_task_records(page) == [], 'Fresh context contains automatic or existing tasks'
    expect(page.locator('#openModalBtn')).to_have_count(1)
    expect(page.locator('#openModalBtn')).to_be_in_viewport(ratio=1)
    capture(page, output, '01-fresh-today')

    planned = create_on_current_page(page, NAMES['today'])
    assert planned['project'] == '' and planned.get('dueAt') is None and planned.get('dueDate') is None
    assert planned.get('focusDate') == TODAY, 'Today creation did not plan the task for today'
    expect(page.locator('#todayWorkspace').get_by_text(NAMES['today'], exact=True)).to_have_count(1)
    before_reload = get_task_records(page)
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    assert get_task_records(page) == before_reload, 'Reload duplicated or rewrote the first task'
    checks.append('Fresh Today is empty; title-only creation is undated/unassigned, plans today and survives reload exactly once')

    navigate_workbench(page, 'tasks')
    ordinary = create_on_current_page(page, NAMES['library'])
    assert ordinary['project'] == '' and ordinary.get('focusDate') is None and ordinary.get('dueAt') is None
    checks.append('Task-library creation stays unassigned/undated and does not inherit Today planning')

    navigate_workbench(page, 'today')
    both = create_on_current_page(page, NAMES['both'], project='Studio', deadline=TODAY)
    future = create_on_current_page(page, NAMES['future'], project='Studio', deadline=TOMORROW)
    assert both.get('focusDate') == TODAY and both.get('dueLocalDate') == TODAY
    assert future.get('focusDate') == TODAY and future.get('dueLocalDate') == TOMORROW
    navigate_workbench(page, 'tasks')
    due_only = create_on_current_page(page, NAMES['due'], project='Personal', deadline=TODAY)
    assert due_only.get('focusDate') is None and due_only.get('dueLocalDate') == TODAY
    baseline = stored(page)
    navigate_workbench(page, 'today')
    today = page.locator('#todayWorkspace')
    for key in ('today', 'both', 'future', 'due'):
        expect(today.get_by_text(NAMES[key], exact=True)).to_have_count(1)
    expect(today.get_by_text(NAMES['library'], exact=True)).to_have_count(0)
    assert stored(page) == baseline, 'Today rendering changed task dates, plans or configuration'
    assert_active_page(page, 'today')
    capture(page, output, '02-today-plan-and-deadline')
    checks.append('Planned, due-only and future-deadline plans remain distinct; a task planned and due today appears once; opening Today never assigns plans')


def assert_today_focus_reachable(page):
    focused = page.locator(':focus')
    expect(focused).to_be_visible()
    expect(focused).to_be_in_viewport(ratio=1)
    geometry = focused.evaluate("""node => {
        const rect = node.getBoundingClientRect();
        const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        const bounds = el => el ? {top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom,left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right} : null;
        return {reachable:Boolean(node.closest('#todayWorkspace') && hit && (node === hit || node.contains(hit))),
            focused:bounds(node),hit:hit ? {tag:hit.tagName,id:hit.id,className:hit.className} : null,
            topbar:bounds(document.querySelector('.workspace-topbar')),dock:bounds(document.querySelector('.workspace-mobile-dock')),
            notices:[...document.querySelectorAll('.notification.show')].filter(el=>el.getClientRects().length).map(bounds),scrollY};
    }""")
    assert geometry['reachable'], f'Today action left keyboard focus outside its page or beneath another control: {json.dumps(geometry)}'


def check_today_actions(page, output, checks):
    before = get_task_records(page)
    planned = next(task for task in before if task['name'] == NAMES['today'])
    row = page.locator(f'#todayWorkspace [data-workbench-task="{planned["id"]}"]')
    toggle = row.locator('[data-workbench-action="toggle"]')
    toggle.focus()
    page.keyboard.press('Space')
    expect(toggle).to_have_attribute('aria-pressed', 'true')
    after = get_task_records(page)
    completed = next(task for task in after if task['id'] == planned['id'])
    assert completed['completed'] is True and completed['completedAt']
    assert {k:v for k,v in completed.items() if k not in {'completed','completedAt'}} == {k:v for k,v in planned.items() if k not in {'completed','completedAt'}}
    assert all(task in after for task in before if task['id'] != planned['id']), 'Today completion changed another task'
    expect(toggle).to_be_focused()
    assert_today_focus_reachable(page)
    expect(page.locator('#notificationUndoBtn')).to_be_visible()
    page.locator('#undoBtn').click()
    expect(row.locator('[data-workbench-action="toggle"]')).to_have_attribute('aria-pressed', 'false')
    assert get_task_records(page) == before, 'Undo of Today completion did not restore every original task field'

    due = next(task for task in before if task['name'] == NAMES['due'])
    candidate = page.locator(f'#todayWorkspace [data-workbench-task="{due["id"]}"] [data-workbench-action="plan"]')
    candidate.focus()
    page.keyboard.press('Enter')
    planned_row = page.locator(f'#todayWorkspace .today-plan [data-workbench-task="{due["id"]}"]')
    expect(planned_row).to_have_count(1)
    expect(page.locator(f'#todayWorkspace [data-workbench-task="{due["id"]}"]')).to_have_count(1)
    changed = next(task for task in get_task_records(page) if task['id'] == due['id'])
    assert changed == {**due, 'focusDate': TODAY}, 'Adding a deadline task to Today changed its original date or another field'
    assert_today_focus_reachable(page)
    expect(page.locator('#notificationUndoBtn')).to_be_visible()
    page.locator('#undoBtn').click()
    expect(page.locator(f'#todayWorkspace .today-candidates [data-workbench-task="{due["id"]}"]')).to_have_count(1)
    assert get_task_records(page) == before, 'Undo of Today planning did not restore original deadlines/plans'
    capture(page, output, '03-today-actions-and-undo')
    checks.append('Today keyboard completion and candidate planning write only their intended fields; Undo restores exact records and moving rows retain reachable focus')


def check_projects_and_independent_scopes(page, output, checks):
    baseline = stored(page)
    navigate_workbench(page, 'projects')
    projects = page.locator('#projectsWorkspace')
    studio = projects.get_by_role('button', name=re.compile('Studio'))
    expect(studio).to_have_count(1)
    studio.click()
    assert_active_page(page, 'tasks')
    expect(page.locator('#projectFilterBtn')).to_have_attribute('aria-label', re.compile('Studio'))
    expect(page.locator('#taskList .task-name')).to_have_text([NAMES['both'], NAMES['future']])
    assert stored(page) == baseline, 'Opening a project changed task/configuration records'

    open_task_editor(page, preserve_context=True)
    expect(page.locator('#taskProject')).to_have_value('Studio')
    expect(page.locator('#taskName')).to_have_value('')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_active_page(page, 'tasks')
    assert stored(page) == baseline, 'Cancelling a project-context editor changed data'
    checks.append('Project overview opens its exact task scope and editor; cancellation preserves every field')

    select_view(page, 'timeline')
    expect(page.locator('.timeline-view')).to_be_visible()
    page.locator('#searchInput').fill('tomorrow')
    navigate_workbench(page, 'review')
    expect(page.locator('#searchInput')).to_have_value('')
    select_project(page, 'all')
    assert_active_page(page, 'review')
    page.locator('#searchInput').fill('Library')
    expect(page.locator('.stats-view')).to_be_visible()

    navigate_workbench(page, 'today')
    expect(page.locator('#todayWorkspace').get_by_text(NAMES['due'], exact=True)).to_have_count(1)
    open_task_editor(page, preserve_context=True)
    expect(page.locator('#taskProject')).to_have_value('')
    expect(page.locator('#noDeadline')).to_be_checked()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_active_page(page, 'today')
    navigate_workbench(page, 'projects')
    expect(projects.get_by_text('Studio', exact=True)).to_have_count(1)
    navigate_workbench(page, 'tasks')
    expect(page.locator('#searchInput')).to_have_value('tomorrow')
    expect(page.locator('#projectFilterBtn')).to_have_attribute('aria-label', re.compile('Studio'))
    expect(page.locator('#viewTab-timeline')).to_have_attribute('aria-current', 'page')
    expect(page.locator('.timeline-view')).to_be_visible()
    expect(page.locator('#taskList .task-name')).to_have_text([NAMES['future']])
    navigate_workbench(page, 'review')
    expect(page.locator('#searchInput')).to_have_value('Library')
    assert stored(page) == baseline, 'Page scope changes changed persisted task/configuration data'
    capture(page, output, '03-review-independent-scope')
    checks.append('Today/project overviews ignore hidden library filters; Tasks and Review retain independent query, project and task-view state')


def check_review_and_settings_return(page, output, checks):
    baseline = stored(page)
    drilldown = page.locator('[data-stats-action="undated"]')
    expect(drilldown).to_be_visible()
    expect(drilldown).to_be_enabled()
    expect(drilldown.locator('.stats-action-value')).to_have_text('1')
    drilldown.click()
    assert_active_page(page, 'tasks')
    expect(page.locator('#taskList .task-name')).to_have_text([NAMES['library']])
    expect(task_locator(page, NAMES['library'])).to_be_visible()
    expect(page.locator('#statsReturnBar')).to_be_visible()
    page.locator('#statsReturnBtn').click()
    assert_active_page(page, 'review')
    expect(page.locator('#searchInput')).to_have_value('Library')
    expect(drilldown).to_be_focused()
    assert stored(page) == baseline, 'Review drilldown/return changed task/configuration records'
    checks.append('Review drills into the matching task and returns to its own query and keyboard focus')

    for screen in ('today', 'tasks', 'projects', 'review'):
        navigate_workbench(page, screen)
        origin_query = page.locator('#searchInput').input_value() if screen in {'tasks', 'review'} else None
        open_settings(page, 'help')
        assert_active_page(page, 'settings')
        expect(page.locator('#checkUpdateBtn')).to_be_visible()
        page.locator('#settingsBackBtn').click()
        assert_active_page(page, screen)
        if origin_query is not None:
            expect(page.locator('#searchInput')).to_have_value(origin_query)
        assert stored(page) == baseline, f'Settings return from {screen} changed task/configuration records'
    capture(page, output, '04-settings-return-to-review')
    checks.append('Settings Back returns to each of the four originating pages without losing its task/review query')


def check_primary_keyboard(page, output, checks):
    baseline = stored(page)
    dismiss_notice(page)
    mobile = page.locator('#mobileTodayBtn').is_visible()
    selectors = ['#mobileTodayBtn', '#mobileTasksBtn', '#mobileProjectsBtn', '#mobileReviewBtn'] if mobile else ['#workspaceTodayBtn', '#workspaceAllTasks', '#workspaceProjectsBtn', '#viewTab-stats']
    page.locator(selectors[0]).focus()
    for selector in selectors[1:]:
        page.keyboard.press('Tab')
        expect(page.locator(selector)).to_be_focused()
        expect(page.locator(selector)).to_be_in_viewport(ratio=1)
    page.keyboard.press('Enter')
    assert_active_page(page, 'review')
    expect(page.locator(':focus')).to_be_in_viewport(ratio=1)
    page.locator(selectors[0]).focus()
    page.keyboard.press('Space')
    assert_active_page(page, 'today')
    expect(page.locator(':focus')).to_be_in_viewport(ratio=1)
    assert stored(page) == baseline, 'Keyboard page navigation changed persisted records'
    capture(page, output, '05-keyboard-today')
    checks.append('All four primary destinations are reachable in visible keyboard order; Enter/Space activates their actual page')


def run(args):
    output = args.output / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    source = source_identity()
    verification = verification_identity()
    report = {'scope': 'Fresh isolated contexts, real UI creation; only read-only storage inspection', 'browser_engine': args.browser,
              'started_at': datetime.now(timezone.utc).isoformat(), 'source': source, 'verification': verification,
              'viewports': [], 'passed': False, 'output': str(output)}
    server = contextlib.nullcontext(args.url) if args.url else local_server()
    try:
        with server as url, sync_playwright() as p:
            options = browser_launch_options() if args.browser == 'chromium' else {'headless': True}
            browser = getattr(p, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                for width in args.widths:
                    folder = output / str(width)
                    folder.mkdir()
                    context = browser.new_context(viewport={'width': width, 'height': 568 if width == 320 else 844 if width < 780 else 960}, locale='en-US', timezone_id='UTC', reduced_motion='reduce')
                    page = context.new_page()
                    page.clock.install(time=datetime(2039, 2, 15, 12, tzinfo=timezone.utc))
                    errors = []
                    page.on('pageerror', lambda error, sink=errors: sink.append(str(error)))
                    entry = {'width': width, 'checks': [], 'page_errors': errors, 'passed': False}
                    report['viewports'].append(entry)
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        wait_for_app_ready(page)
                        entry['language'] = page.locator('html').get_attribute('lang')
                        entry['theme'] = page.locator('html').get_attribute('data-theme')
                        check_first_creation_and_today(page, folder, entry['checks'])
                        check_today_actions(page, folder, entry['checks'])
                        check_projects_and_independent_scopes(page, folder, entry['checks'])
                        check_review_and_settings_return(page, folder, entry['checks'])
                        check_primary_keyboard(page, folder, entry['checks'])
                        assert not errors, errors
                        entry['saved_tasks'] = len(get_task_records(page))
                        assert entry['saved_tasks'] == len(NAMES)
                        entry['passed'] = True
                        print(f'Workbench {width}px passed: ' + '; '.join(entry['checks']), flush=True)
                    except Exception:
                        entry['error'] = traceback.format_exc()
                        entry['route'] = workbench_screen(page)
                        entry['state'] = page.evaluate("""() => ({
                            active:{tag:document.activeElement?.tagName,id:document.activeElement?.id,
                                action:document.activeElement?.dataset?.workbenchAction,
                                text:document.activeElement?.textContent?.trim().slice(0,160)},
                            view:document.body.dataset.taskView,
                            query:document.getElementById('searchInput')?.value,
                            scrollY,headings:[...document.querySelectorAll('main h1')]
                                .filter(node=>node.getClientRects().length).map(node=>node.textContent)
                        })""")
                        page.screenshot(path=str(folder / 'failure.png'), full_page=False)
                        raise
                    finally:
                        context.close()
            finally:
                browser.close()
        report['source_final'] = source_identity()
        report['verification_final'] = verification_identity()
        report['source_unchanged'] = report['source_final'] == source
        report['verification_unchanged'] = report['verification_final'] == verification
        assert report['source_unchanged'] and report['verification_unchanged'], 'Application or verification inputs changed during the run'
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        if 'source_final' not in report:
            try:
                report['source_final'] = source_identity()
                report['verification_final'] = verification_identity()
                report['source_unchanged'] = report['source_final'] == source
                report['verification_unchanged'] = report['verification_final'] == verification
            except Exception:
                report['identity_error'] = traceback.format_exc()
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': report['passed'], 'report': str(output / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--widths', type=int, nargs='+', default=[1440, 390, 320])
    parser.add_argument('--url')
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-v5-workbench'))
    run(parser.parse_args())
