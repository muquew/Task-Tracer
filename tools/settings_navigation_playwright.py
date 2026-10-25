#!/usr/bin/env python3
"""Exercise permanent view navigation and the independent settings workspace."""
from __future__ import annotations

from smoke_playwright import enter_batch_mode

from smoke_playwright import ensure_capture

import argparse
import contextlib
import json
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright

from security_playwright import ProductionHeaderHandler
from task_draft_playwright import inject_quota_failure
from smoke_playwright import (
    ThreadingHTTPServer, add_task, assert_accessibility_baseline,
    browser_launch_options, clear_app_data, get_task_records, open_settings,
    return_to_task_workspace, select_filter, select_language, select_project,
    select_view, task_locator,
)

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ('list', 'calendar', 'timeline', 'stats')


@contextlib.contextmanager
def production_server():
    """Use the real deployment CSP rather than bypassing inline-script policy."""
    server = ThreadingHTTPServer(('127.0.0.1', 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive(), 'Settings regression server did not stop'


def assert_view_destinations(page, current):
    expect(page.locator('#viewSwitcher')).to_be_visible()
    expect(page.locator('#viewSwitcher [role="tab"]')).to_have_count(0)
    for view in VIEWS:
        button = page.locator(f'#viewTab-{view}')
        expect(button).to_be_visible()
        expect(button).to_be_enabled()
        expect(button).to_have_role('button')
        expect(button).to_have_attribute('tabindex', '0')
        label = button.locator('span')
        expect(label).to_be_visible()
        assert (label.inner_text()).strip(), f'{view} has no persistent visible label'
        if view == current:
            expect(button).to_have_attribute('aria-current', 'page')
        else:
            assert button.get_attribute('aria-current') is None, f'{view} falsely announces the current page'
    if current:
        expect(page.locator('#taskList')).to_have_role('region')
        expect(page.locator('#taskList')).to_have_attribute('aria-labelledby', f'viewTab-{current}')


def assert_mobile_targets(page):
    """Verify four usable equal dock columns and hit-test their actual pointer targets."""
    dock = page.locator('#viewSwitcher').bounding_box()
    viewport = page.viewport_size
    assert dock and viewport and dock['width'] >= viewport['width'] - 32, ('Dock does not fill its viewport', dock)
    boxes = [page.locator(f'#viewTab-{view}').bounding_box() for view in VIEWS]
    assert all(box and box['width'] >= 44 and box['height'] >= 44 for box in boxes), ('Undersized dock targets', boxes)
    assert max(box['width'] for box in boxes) - min(box['width'] for box in boxes) <= 2, ('Unequal dock columns', boxes)
    assert boxes[0]['x'] < boxes[1]['x'] < boxes[2]['x'] < boxes[3]['x'], ('Wrong dock order', boxes)
    assert boxes[-1]['x'] + boxes[-1]['width'] - boxes[0]['x'] >= dock['width'] - 32, ('Dock columns leave unused width', boxes)
    for view in VIEWS:
        button = page.locator(f'#viewTab-{view}')
        geometry = button.evaluate('''node => {
            const rect = node.getBoundingClientRect();
            const target = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
            return {left:rect.left, right:rect.right, top:rect.top, bottom:rect.bottom,
                viewportWidth:innerWidth, viewportHeight:innerHeight,
                hit:target?.closest('button')?.id === node.id};
        }''')
        assert geometry['hit'], f'Dock target is covered: {view}: {geometry}'
        assert 0 <= geometry['left'] and geometry['right'] <= geometry['viewportWidth'] + 1, geometry
        assert geometry['top'] >= 0 and geometry['bottom'] <= geometry['viewportHeight'] + 1, geometry


def assert_dialog_return(page, action, content):
    open_settings(page, 'help' if action == '#helpMenuBtn' else 'data')
    page.locator(action).click()
    expect(page.locator(content)).to_be_visible()
    expect(page.locator('#taskModal')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#settingsWorkspace')).to_be_visible()
    expect(page.locator(action)).to_be_focused()
    expect(page.locator(action)).to_be_in_viewport()


def exercise_workspace(browser, url, width, language):
    context = browser.new_context(viewport={'width': width, 'height': 900 if width > 779 else 844},
                                  locale='en-US', timezone_id='Asia/Shanghai',
                                  accept_downloads=True, reduced_motion='reduce')
    errors = []
    try:
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(page, url)
        select_language(page, language)
        add_task(page, 'Settings retained task A', no_deadline=True, project='Design')
        add_task(page, 'Settings retained task B', no_deadline=True, project='Design')
        add_task(page, 'Outside scoped project', no_deadline=True, project='Outside')
        select_filter(page, 'all')
        select_project(page, 'Design')
        page.locator('#searchInput').fill('Settings retained')
        expect(page.locator('.task-item')).to_have_count(2)
        enter_batch_mode(page)
        task_locator(page, 'Settings retained task A').locator('.task-select-checkbox').check()
        ensure_capture(page)
        page.locator('#quickAddInput').fill('Keep this unsaved quick draft #design')
        preserved = {
            'tasks': get_task_records(page),
            'query': page.locator('#searchInput').input_value(),
            'filter': page.locator('#currentFilterLabel').inner_text(),
            'project': page.locator('#projectFilterBtn').inner_text(),
            'quick_draft': page.locator('#quickAddInput').input_value(),
        }
        assert_view_destinations(page, 'list')
        translations = json.loads((ROOT / 'resources' / f'{language}.json').read_text())
        scope = page.locator('#workspaceAllTasks [data-i18n]')
        expect(scope).to_have_text(translations['settings']['allTasksScope'])
        assert len(scope.inner_text()) <= 40, 'Primary scope label is a paragraph rather than a short destination'
        assert translations['settings']['scopeAll'] not in page.locator('#workspaceAllTasks').inner_text(), \
            'Cleanup scope explanation leaked into primary task navigation'
        if width > 779:
            host = page.locator('#workspaceViewNavHost').bounding_box()
            for view in VIEWS:
                box = page.locator(f'#viewTab-{view}').bounding_box()
                assert host and box and box['width'] >= host['width'] - 4, ('Desktop navigation does not fill its sidebar', box, host)
        open_settings(page)
        expect(page.locator('#settingsWorkspace')).not_to_have_role('dialog')
        expect(page.locator('#settingsWorkspace [role="menuitem"]')).to_have_count(0)
        assert_view_destinations(page, None)
        for selector in ('#settingsAppearance', '#settingsData', '#settingsExperience',
                         '#settingsCleanup', '#settingsHelp'):
            panel = page.locator(selector)
            expect(panel).to_have_count(1)
            expect(panel).to_have_role('tabpanel')
            if selector == '#settingsData':
                expect(panel).to_be_visible()
            else:
                expect(panel).to_be_hidden()
        expect(page.locator('#settingsWorkspace [data-settings-section][aria-selected="true"]')).to_have_count(1)
        expect(page.locator('#languageSelect')).to_have_count(1)
        expect(page.locator('#themeToggleBtn')).to_have_count(1)
        expect(page.locator('#settingsLanguageSelect, #settingsThemeSelect')).to_have_count(0)
        expect(page.locator('header #languageSelect, header #themeToggleBtn')).to_have_count(0)
        for action in ('backupBtn', 'exportCsvBtn', 'importBtn', 'recoveryBtn', 'storageHealthBtn',
                       'notificationToggleBtn', 'archiveCompletedBtn', 'clearCompletedBtn',
                       'savedViewsTransferBtn', 'helpMenuBtn'):
            expect(page.locator(f'#{action}')).to_have_count(1)
        assert get_task_records(page) == preserved['tasks'], 'Opening settings changed task records'
        assert_dialog_return(page, '#helpMenuBtn', '.help-guide')
        assert_dialog_return(page, '#storageHealthBtn', '#storageUsage')
        with page.expect_download() as pending:
            page.locator('#backupBtn').click()
        actual = json.loads(pending.value.path().read_bytes())
        assert actual['tasks'] == preserved['tasks'], 'Settings backup changed its task scope or content'
        expect(page.locator('#settingsWorkspace')).to_be_visible()
        expect(page.locator('#backupHealthText')).to_be_visible()
        initial_health = translations['backup']['health']
        expect(page.locator('#backupHealthText')).to_have_text(
            initial_health['ok'].replace('{age}', initial_health['today']))
        expect(page.locator('#backupBtn')).to_be_focused()
        open_settings(page, 'appearance')
        for theme in ('dark', 'light', 'system'):
            page.locator('#themeToggleBtn').select_option(theme)
            expect(page.locator('#themeToggleBtn')).to_have_value(theme)
            resolved = theme if theme != 'system' else page.evaluate(
                "matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'")
            expect(page.locator('html')).to_have_attribute('data-theme', resolved)
        other_language = 'en' if language == 'zh-CN' else 'zh-CN'
        for next_language in (other_language, language):
            open_settings(page, 'appearance')
            page.locator('#languageSelect').select_option(next_language)
            expect(page.locator('html')).to_have_attribute('lang', next_language)
            expect(page.locator('#languageSelect')).to_have_value(next_language)
            open_settings(page, 'data')
            target_health = json.loads((ROOT / 'resources' / f'{next_language}.json').read_text())['backup']['health']
            expect(page.locator('#backupHealthText')).to_have_text(
                target_health['ok'].replace('{age}', target_health['today']))
            expect(page.locator('#settingsWorkspace')).to_be_visible()
        assert_accessibility_baseline(page, f'{width}px {language} settings')
        if width <= 779:
            assert_mobile_targets(page)
            open_settings(page, 'help')
            page.locator('#helpMenuBtn').click(trial=True)
            action_box = page.locator('#helpMenuBtn').bounding_box()
            dock_box = page.locator('#viewSwitcher').bounding_box()
            assert action_box and dock_box and action_box['y'] + action_box['height'] <= dock_box['y'] + 1, \
                'The final settings action is obscured by the mobile dock'
        return_to_task_workspace(page)
        ensure_capture(page)
        expect(page.locator('#searchInput')).to_have_value(preserved['query'])
        expect(page.locator('#currentFilterLabel')).to_have_text(preserved['filter'])
        expect(page.locator('#projectFilterBtn')).to_have_text(preserved['project'])
        expect(page.locator('#quickAddInput')).to_have_value(preserved['quick_draft'])
        expect(page.locator('#batchModeBtn')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('.task-select-checkbox:checked')).to_have_count(1)
        expect(page.locator('.task-item')).to_have_count(2)
        assert get_task_records(page) == preserved['tasks'], 'Settings interactions changed task records'

        # Collapsing auxiliary tools must never conceal the primary view destinations.
        pin = page.locator('#toolsDrawerPinBtn')
        if pin.count() and pin.get_attribute('aria-pressed') == 'true':
            pin.click()
        toggle = page.locator('#toolsDrawerToggleBtn')
        if toggle.get_attribute('aria-expanded') == 'true':
            toggle.click()
        expect(page.locator('#toolsDrawerContent')).to_be_hidden()
        for view in VIEWS:
            assert_view_destinations(page, page.locator('#viewSwitcher [aria-current="page"]').get_attribute('data-view'))
            select_view(page, view)
            open_settings(page)
            # Selecting the already active view must still leave settings.
            page.locator(f'#viewTab-{view}').click()
            expect(page.locator('#settingsWorkspace')).to_be_hidden()
            expect(page.locator('#tasksWorkspace')).to_be_visible()
            assert_view_destinations(page, view)
            expect(page.locator('#toolsDrawerContent')).to_be_hidden()
            if width <= 779:
                assert_mobile_targets(page)
        assert get_task_records(page) == preserved['tasks'], 'Navigation wrote task data'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Settings/nav causes horizontal overflow'
        assert not errors, errors
        print(f'{width}px {language}: permanent labelled views, collapsed-tools access, settings/back/current-view, '
              'scoped state and draft/selection preservation, real backup, dialog focus, appearance and language passed', flush=True)
    finally:
        context.close()


def exercise_empty_backup_language(browser, url, width):
    context = browser.new_context(viewport={'width': width, 'height': 844},
                                  locale='en-US', timezone_id='Asia/Shanghai', reduced_motion='reduce')
    errors = []
    try:
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        clear_app_data(page, url)
        select_language(page, 'zh-CN')
        before = get_task_records(page)
        assert before == [], 'Empty backup-language fixture unexpectedly contains tasks'
        open_settings(page)
        initial_health = json.loads((ROOT / 'resources' / 'zh-CN.json').read_text())['backup']['health']
        expect(page.locator('#backupHealthText')).to_have_text(initial_health['empty'])
        for language in ('en', 'zh-CN'):
            open_settings(page, 'appearance')
            page.locator('#languageSelect').select_option(language)
            expect(page.locator('html')).to_have_attribute('lang', language)
            expect(page.locator('#languageSelect')).to_have_value(language)
            open_settings(page, 'data')
            target_health = json.loads((ROOT / 'resources' / f'{language}.json').read_text())['backup']['health']
            expect(page.locator('#backupHealthText')).to_have_text(target_health['empty'])
            expect(page.locator('#settingsWorkspace')).to_be_visible()
            assert get_task_records(page) == before, 'Translating the empty backup status changed task data'
        assert not errors, errors
        print(f'{width}px empty backup status: both language directions update the exact backup status through real appearance/data categories without task changes', flush=True)
    finally:
        context.close()


def exercise_unavailable_storage(browser, url):
    context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    errors = []
    try:
        context.add_init_script('''(() => {
            window.__settingsDenyStorage = sessionStorage.getItem('__settingsStorageRecovered') !== 'true';
            const open = indexedDB.open.bind(indexedDB);
            indexedDB.open = (...args) => {
                if (window.__settingsDenyStorage) throw new DOMException('Synthetic settings storage guard', 'SecurityError');
                return open(...args);
            };
        })();''')
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='domcontentloaded')
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        expect(page.locator('#openModalBtn')).to_be_disabled()
        expect(page.locator('#openMenuBtn')).to_be_enabled()
        open_settings(page, 'help')
        for action in ('backupBtn', 'importBtn', 'recoveryBtn', 'notificationToggleBtn',
                       'archiveCompletedBtn', 'clearCompletedBtn'):
            expect(page.locator(f'#{action}')).to_be_disabled()
        expect(page.locator('#helpMenuBtn')).to_be_enabled()
        assert_dialog_return(page, '#helpMenuBtn', '.help-guide')
        open_settings(page, 'appearance')
        page.locator('#themeToggleBtn').select_option('dark')
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        expect(page.locator('#themeToggleBtn')).to_have_value('dark')
        return_to_task_workspace(page)
        page.evaluate("() => { window.__settingsDenyStorage = false; sessionStorage.setItem('__settingsStorageRecovered', 'true'); }")
        page.locator('#retryStorageBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
        expect(page.locator('#quickAddInput')).to_be_enabled()
        expect(page.locator('#openModalBtn')).to_be_enabled()
        assert get_task_records(page) == [], 'Recovering storage invented a task record'

        raw = 'Keep this raw capture available to copy after storage failure'
        ensure_capture(page).fill(raw)
        inject_quota_failure(page)
        page.locator('#quickAddInput').press('Enter')
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        expect(page.locator('#openModalBtn')).to_be_enabled()
        page.locator('#captureCloseBtn').click()
        expect(page.locator('#captureShelf')).to_be_hidden()
        page.locator('#openModalBtn').click()
        expect(page.locator('#quickAddInput')).to_be_visible()
        expect(page.locator('#quickAddInput')).to_have_value(raw)
        expect(page.locator('#quickAddInput')).to_have_attribute('readonly', '')
        assert get_task_records(page) == [], 'Failed retained capture wrote a partial task'
        page.locator('#retryStorageBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
        expect(page.locator('#openModalBtn')).to_be_enabled()
        expect(page.locator('#quickAddInput')).to_have_value(raw)
        expect(page.locator('#quickAddInput')).not_to_have_attribute('readonly', '')
        assert get_task_records(page) == [], 'Retry saved a retained capture without explicit submission'
        assert not errors, errors
        print('Unavailable storage: empty Add is disabled; retained raw capture can reopen for copying; settings/help/theme and real retry preserve data', flush=True)
    finally:
        context.close()


def exercise_language_rollback(browser, url):
    for selector in ('#languageSelect',):
        context = browser.new_context(reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            add_task(page, 'Language rollback keeps real task data', no_deadline=True)
            before = get_task_records(page)
            previous = page.locator('html').get_attribute('lang')
            open_settings(page, 'appearance')
            page.evaluate("""() => {
                const put = IDBObjectStore.prototype.put;
                window.__languageAbortInjected = false;
                IDBObjectStore.prototype.put = function(value, ...args) {
                    const request = put.call(this, value, ...args);
                    if (this.name === 'config' && value?.key === 'language') {
                        IDBObjectStore.prototype.put = put;
                        window.__languageAbortInjected = true;
                        this.transaction.abort();
                    }
                    return request;
                };
            }""")
            page.locator(selector).select_option('en' if previous == 'zh-CN' else 'zh-CN')
            page.wait_for_function('window.__languageAbortInjected === true')
            expect(page.locator('html')).to_have_attribute('lang', previous)
            expect(page.locator('#languageSelect')).to_have_value(previous)
            assert get_task_records(page) == before, 'Failed language preference write changed task data'
            assert not errors, errors
            print(f'Language rollback: aborted config write from {selector} restores the canonical control and document language', flush=True)
        finally:
            context.close()


def run(engine, case='all'):
    with production_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        try:
            print(f'Settings/navigation {engine}: {browser.version}; deployment CSP enforced', flush=True)
            if case == 'all':
                for width in (1440, 390):
                    for language in ('zh-CN', 'en'):
                        exercise_workspace(browser, url, width, language)
                    exercise_empty_backup_language(browser, url, width)
            if case in ('all', 'storage'):
                exercise_unavailable_storage(browser, url)
            if case in ('all', 'language'):
                exercise_language_rollback(browser, url)
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'storage', 'language'), default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
