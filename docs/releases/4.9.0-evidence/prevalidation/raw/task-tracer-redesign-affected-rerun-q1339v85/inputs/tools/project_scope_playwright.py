#!/usr/bin/env python3
"""Exercise literal project names and versioned saved-view scopes through the UI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright
from saved_views_playwright import save_view, stored_views
from smoke_playwright import click_task_action, reveal_workspace_control, select_language, task_locator
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, get_task_records, local_server,
    visible_task_names, wait_for_app_ready,
)
from views_portability_playwright import (
    checksum, choose_file, export_views, open_manager, payload, preview, seed_views, view,
)


LITERAL_JSON_PROJECT = '{"kind":"all"}'
UNASSIGNED_LABELS = {
    language: json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())['projects']['none']
    for language in ('en', 'zh-CN')
}
PROJECTS = list(dict.fromkeys([
    'all', '__none__', LITERAL_JSON_PROJECT, 'project:all', 'Ordinary', 'Unassigned',
    *UNASSIGNED_LABELS.values(),
]))


def assert_visible(page, expected):
    expect(page.locator('.task-item .task-name')).to_have_count(len(expected))
    actual = set(visible_task_names(page))
    assert actual == set(expected), f'Project scope displayed {actual}, expected {set(expected)}'


def select_literal_project(page, name):
    page.locator('#projectFilterBtn').click()
    page.locator('#projectFilterMenu .dropdown-option').filter(
        has=page.locator('span').filter(has_text=re.compile('^' + re.escape(name) + '$'))
    ).last.click()
    expect(page.locator('#projectFilterBtn')).to_have_attribute('aria-expanded', 'false')


def select_sentinel(page, index):
    page.locator('#projectFilterBtn').click()
    page.locator('#projectFilterMenu .dropdown-option').nth(index).click()


def apply_view(page, name, expected):
    control = page.locator('#savedViewsList .saved-view-chip').filter(
        has=page.locator('.saved-view-name', has_text=name)
    ).locator('.saved-view-apply')
    reveal_workspace_control(page, control).click()
    assert_visible(page, expected)


def assert_language_grouping(page):
    add_task(page, 'Named English unassigned', project=UNASSIGNED_LABELS['en'], no_deadline=True)
    add_task(page, 'Named Chinese unassigned', project=UNASSIGNED_LABELS['zh-CN'], no_deadline=True)
    add_task(page, 'Actually unassigned', no_deadline=True)
    before = get_task_records(page)
    for language in ('en', 'zh-CN'):
        if language != 'en':
            select_language(page, language)
            page.keyboard.press('Escape')
        expect(page.locator('#taskList .task-group-header')).to_have_count(3)
        groups = page.locator('#taskList').evaluate("""list => {
            const groups = [];
            for (const element of list.children) {
                if (element.classList.contains('task-group-header')) groups.push([]);
                else if (element.matches('.task-item')) groups.at(-1).push(element.querySelector('.task-name').textContent);
            }
            return groups;
        }""")
        assert {tuple(group) for group in groups} == {('Named English unassigned',),
            ('Named Chinese unassigned',), ('Actually unassigned',)}, groups
    assert get_task_records(page) == before
    print('Project scope passed: localized missing-project labels never merge exact-name projects with the unassigned scope: '
          + json.dumps(UNASSIGNED_LABELS, ensure_ascii=False), flush=True)


def assert_sidebar_project_exits_today_plan(page, url):
    original_viewport = page.viewport_size
    page.set_viewport_size({'width': 390, 'height': 844})
    clear_app_data(page, url)
    project = 'Sidebar full project'
    add_task(page, 'Sidebar planned task', project=project, no_deadline=True)
    add_task(page, 'Sidebar unplanned task', project=project, no_deadline=True)
    add_task(page, 'Sidebar other planned task', project='Other sidebar project', no_deadline=True)
    add_task(page, 'Sidebar archived task', project=project, no_deadline=True)
    click_task_action(task_locator(page, 'Sidebar archived task'), 'archive')
    expect(task_locator(page, 'Sidebar archived task')).to_have_count(0)
    for name in ('Sidebar planned task', 'Sidebar other planned task'):
        click_task_action(task_locator(page, name), 'focus')
    reveal_workspace_control(page, '#focusModeToggleBtn').click()
    expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'true')
    assert_visible(page, {'Sidebar planned task', 'Sidebar other planned task'})
    before = get_task_records(page)
    translations = json.loads((Path(__file__).resolve().parents[1] / 'resources'
                               / f'{page.locator("html").get_attribute("lang")}.json').read_text())
    unarchived = [task for task in before if not task.get('archived')]
    global_summary = translations['focus']['summary'].replace('{completed}', str(sum(task['completed'] for task in unarchived))).replace('{total}', str(len(unarchived)))

    def assert_global_summary():
        expect(page.locator('.workspace-list-footer')).to_contain_text(translations['workspace']['progressScope'])
        expect(page.locator('#workspaceCompletionSummary')).to_contain_text(global_summary)

    assert len(unarchived) == 3 and len(before) == 4
    assert_global_summary()

    select_literal_project(page, project)
    assert_visible(page, {'Sidebar planned task'})
    expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'true')
    assert_global_summary()

    encoded = json.dumps({'kind': 'project', 'name': project}, ensure_ascii=False, separators=(',', ':'))
    button = page.locator(f'#workspaceProjects [data-workspace-project={json.dumps(encoded, ensure_ascii=False)}]')
    reveal_workspace_control(page, button).click()
    expect(page.locator('#focusModeToggleBtn')).to_have_attribute('aria-pressed', 'false')
    expect(button).to_have_attribute('aria-current', 'page')
    assert_visible(page, {'Sidebar planned task', 'Sidebar unplanned task'})
    assert_global_summary()
    assert get_task_records(page) == before, 'Sidebar or combined project navigation rewrote task/focus data'
    print('Project scope passed: 390px sidebar project exits the daily plan; the project filter keeps the explicit combination', flush=True)
    if original_viewport:
        page.set_viewport_size(original_viewport)


def run(engine, grouping_only=False):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'Project scope {engine}: {browser.version}', flush=True)
        context = browser.new_context(accept_downloads=True, locale='en-US', reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            console_errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
            clear_app_data(page, url)
            select_language(page, 'en')
            page.keyboard.press('Escape')
            if grouping_only:
                assert_language_grouping(page)
                assert not errors, errors
                return
            for index, project in enumerate(PROJECTS):
                add_task(page, f'Literal project task {index}', project=project, no_deadline=True)
            add_task(page, 'Unassigned scope task', no_deadline=True)
            task_records = get_task_records(page)
            all_names = {task['name'] for task in task_records}
            expected_views = {}
            expected_scopes = {}
            for index, project in enumerate(PROJECTS):
                select_literal_project(page, project)
                expected = {f'Literal project task {index}'}
                assert_visible(page, expected)
                name = f'Literal scope {index}'
                save_view(page, name, '')
                expected_views[name] = expected
                expected_scopes[name] = {'kind': 'project', 'name': project}
            select_sentinel(page, 0)
            assert_visible(page, all_names)
            expect(page.locator('#taskList .task-group-header')).to_have_count(len(PROJECTS) + 1)
            save_view(page, 'All scope', '')
            expected_views['All scope'] = all_names
            expected_scopes['All scope'] = {'kind': 'all'}
            select_sentinel(page, 1)
            assert_visible(page, {'Unassigned scope task'})
            save_view(page, 'Unassigned scope', '')
            expected_views['Unassigned scope'] = {'Unassigned scope task'}
            expected_scopes['Unassigned scope'] = {'kind': 'unassigned'}
            assert {item['name']: item['projectFilter'] for item in stored_views(page)} == expected_scopes
            print('Project scope passed: all, __none__, encoded-looking and ordinary project names remain distinct from both sentinels', flush=True)

            for index, project in enumerate(PROJECTS[:3]):
                page.locator('#openMenuBtn').focus()
                page.keyboard.press('Control+p')
                page.locator('#commandPaletteInput').fill(f'Switch project: {project}')
                page.locator('#commandPalette .command-item').filter(
                    has=page.locator('.command-item-title').filter(has_text=re.compile('^Switch project: ' + re.escape(project) + '$'))
                ).click()
                assert_visible(page, {f'Literal project task {index}'})
            print('Project scope passed: command palette selects the same literal project scopes', flush=True)

            page.reload()
            wait_for_app_ready(page)
            for name, expected in expected_views.items():
                apply_view(page, name, expected)
            exported = export_views(page)
            assert exported['version'] == '1.1'
            assert {item['name']: item['projectFilter'] for item in exported['savedViews']} == expected_scopes
            seed_views(page, [])
            preview(page, exported)
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            for name, expected in expected_views.items():
                apply_view(page, name, expected)
            print('Project scope passed: exact scopes survive save, reload, 1.1 export and reviewed reimport', flush=True)

            legacy = [view('Legacy all', '', 'legacy-all') | {'projectFilter': 'all'},
                      view('Legacy unassigned', '', 'legacy-none') | {'projectFilter': '__none__'},
                      view('Legacy literal JSON', '', 'legacy-json') | {'projectFilter': LITERAL_JSON_PROJECT},
                      view('Legacy prefix', '', 'legacy-prefix') | {'projectFilter': 'project:all'}]
            legacy_expected = {'Legacy all': all_names, 'Legacy unassigned': {'Unassigned scope task'},
                               'Legacy literal JSON': {'Literal project task 2'},
                               'Legacy prefix': {'Literal project task 3'}}
            seed_views(page, legacy)
            for name, expected in legacy_expected.items():
                apply_view(page, name, expected)
            select_sentinel(page, 0)
            save_view(page, 'Unrelated new scope', 'tag:unrelated-scope')
            assert stored_views(page)[1:] == legacy, 'Saving a new scope rewrote unrelated legacy view records'
            before = stored_views(page)
            export_views(page)
            assert stored_views(page) == before, 'Export migrated legacy records in storage'
            seed_views(page, [])
            preview(page, payload(legacy))
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            for name, expected in legacy_expected.items():
                apply_view(page, name, expected)
            print('Project scope passed: legacy config and 1.0 files retain sentinel semantics and treat encoded-looking names literally', flush=True)

            missing = payload([view('Missing project scope', '') | {
                'projectFilter': {'kind': 'project', 'name': 'Temporarily absent project'}}])
            missing['version'] = '1.1'
            missing['checksum'] = checksum(missing)
            preview(page, missing)
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            apply_view(page, 'Missing project scope', set())
            expect(page.locator('#projectFilterBtn')).to_contain_text('Temporarily absent project')
            page.reload()
            wait_for_app_ready(page)
            apply_view(page, 'Missing project scope', set())
            print('Project scope passed: a saved project with no current tasks stays empty without expanding to all projects', flush=True)

            bad_scopes = ['all', {'kind': 'unknown'}, {'kind': 'all', 'name': 'all'},
                          {'kind': 'project', 'name': ''}, {'kind': 'project', 'name': 12},
                          {'kind': 'project', 'name': 'Ordinary', 'extra': True}, None, []]
            for scope in bad_scopes:
                invalid = payload([view('Rejected malformed scope', '') | {'projectFilter': scope}])
                invalid['version'] = '1.1'
                invalid['checksum'] = checksum(invalid)
                before = stored_views(page)
                open_manager(page)
                page.evaluate("document.getElementById('notification').classList.remove('show')")
                choose_file(page, invalid)
                expect(page.locator('#notification')).to_have_class('notification error show')
                expect(page.locator('#savedViewsTransferContent')).to_be_visible()
                assert stored_views(page) == before
            assert get_task_records(page) == task_records, 'Project filtering or saved-view transfer changed tasks'
            assert not errors, errors
            print('Project scope passed: malformed 1.1 scope objects rejected without changing saved views or tasks', flush=True)
            assert_sidebar_project_exits_today_plan(page, url)
            assert not errors, errors
        except Exception:
            print(f'Project scope failure diagnostics: page errors={errors}; console errors={console_errors}', flush=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--grouping-only', action='store_true', help='Run only translated project grouping regression')
    args = parser.parse_args()
    run(args.browser, args.grouping_only)
