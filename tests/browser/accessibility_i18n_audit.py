#!/usr/bin/env python3
from __future__ import annotations
import tests.support.accessibility_i18n_audit as audit_support
from tests.support.accessibility_i18n_audit import (
    assert_focus_visible,
    assert_layout,
    assert_workspace_theme_gallery,
    audit_subtask_checkbox_visibility,
    color_contrast,
    find_axe_source,
    inject_axe,
    run_axe,
    settle_animations,
    subtask_checkbox_paint,
)
from tests.support.paths import (
    REPO_ROOT,
    SOURCE_HTML,
    SITE_ROOT,
    input_path,
    source_path,
    read_application_source,
    read_source_html,
)

from tests.support.browser import open_help, open_task_editor, ensure_capture

from tests.support.browser import open_settings, return_to_task_workspace

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page, expect, sync_playwright

from tests.support.views_portability import (
    payload as views_payload,
    view as saved_view,
    choose_file as choose_views_file,
)
from tests.support.drafts import inject_quota_failure
from tests.support.views_delete import save_named as save_delete_audit_view
from tests.support.storage import stored

from tests.support.browser import (
    close_workspace_navigation,
    reveal_workspace_control,
    select_language,
    select_theme_preference,
)
from tests.support.browser import (
    add_task,
    assert_accessibility_baseline,
    browser_launch_options,
    clear_app_data,
    click_batch_action,
    enter_batch_mode,
    ensure_conda_library_path,
    future_date,
    get_task_records,
    select_view,
    reveal_batch_action,
    wait_for_app_ready,
)
from tests.support.scenarios import exercise_workspace_navigation
from tests.support.http import local_server


def assert_focus_baseline(page: Page, label: str) -> None:
    if page.locator('#draftDiscardPrompt').is_visible():
        for selector in ('#draftKeepEditingBtn', '#draftDiscardBtn'):
            assert_focus_visible(page, selector, label)
        return
    selectors = ["#taskName", "#cancelBtn", "#submitBtn"] if page.locator("#taskModal").is_visible() else [
        "#openModalBtn",
        "#searchInput",
        "#projectFilterBtn",
        "#filterBtn",
        "#sortBtn",
        '#languageSelect',
        '#themeToggleBtn',
        '#workspaceNavToggle',
        '#viewSwitcher .view-tab[aria-current="page"]',
    ]
    if page.locator('#settingsWorkspace').is_visible():
        selectors = ['#settingsBackBtn', '#themeToggleBtn', '#languageSelect',
                     'input[type="radio"][name="workspaceTheme"]:checked',
                     '#backupBtn', '#importBtn', '#recoveryBtn', '#storageHealthBtn',
                     '#notificationToggleBtn', '#archiveCompletedBtn', '#clearCompletedBtn', '#helpMenuBtn']
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() and locator.is_visible() and locator.is_enabled():
            if locator.evaluate('node => Boolean(node.closest("[inert], [hidden], [aria-hidden=true]"))'):
                continue
            assert_focus_visible(page, selector, label)


def switch_to_english(page: Page) -> None:
    select_language(page, 'en')
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.keyboard.press("Escape")


def audit_page_state(page: Page, axe_source: str, label: str) -> None:
    print(f'Accessibility state: {label}', flush=True)
    settle_animations(page, label)
    assert_accessibility_baseline(page, label)
    run_axe(page, axe_source, label)
    assert_focus_baseline(page, label)
    assert_layout(page, label)


def audit_workspace_navigation(page: Page, axe_source: str, label: str) -> None:
    """Audit the real project drawer and the global navigation that opens it."""
    before = stored(page)
    sidebar = page.locator('#workspaceSidebar')
    toggle = page.locator('#workspaceNavToggle')
    mobile = toggle.is_visible()
    was_open = mobile and toggle.get_attribute('aria-expanded') == 'true'
    if mobile and not was_open:
        toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'true')
    expect(sidebar).to_be_visible()
    assert not sidebar.evaluate('node => Boolean(node.closest("[hidden],[inert],[aria-hidden=true]"))')
    contextual = bool(page.locator('#workspaceScopeNav').count())
    selectors = ('#workspaceNavClose',) if contextual else ('#workspaceAllTasks', '#workspaceSettingsBtn')
    if contextual and page.locator('#workspaceProjects [data-workspace-project]').count():
        selectors += ('#workspaceProjects [data-workspace-project] >> nth=0',)
    for selector in selectors:
        if page.locator(selector).is_visible() and page.locator(selector).is_enabled():
            assert_focus_visible(page, selector, label)
    audit_page_state(page, axe_source, label)
    if mobile and not was_open:
        close_workspace_navigation(page)
        if contextual:
            for selector in ('#workspaceAllTasks', '#mobileTasksBtn', '#workspaceSettingsBtn'):
                if page.locator(selector).is_visible() and page.locator(selector).is_enabled():
                    assert_focus_visible(page, selector, label)
    assert stored(page) == before, 'Auditing navigation changed task or configuration data'


def seed_tasks(page: Page) -> None:
    stamp = int(time.time())
    add_task(page, f"A11y Audit No Deadline {stamp}", no_deadline=True, project="Audit Project", tags=["keyboard", "screen reader"])
    add_task(
        page,
        f"A11y Audit Deadline {stamp}",
        due_date=future_date(1),
        due_time="12:30",
        reminder_offset="15",
        project="Audit Project",
        tags=["deadline"],
        subtasks=["Review focus order", "Check translation length"],
    )


def audit_views_transfer(page: Page, axe_source: str, label: str) -> None:
    open_settings(page)
    page.locator('#savedViewsTransferBtn').click()
    expect(page.locator('#savedViewsTransferContent')).to_be_visible()
    audit_page_state(page, axe_source, f'{label} view transfer')
    choose_views_file(page, views_payload([saved_view('Study layout', 'tag:study')]))
    expect(page.locator('#savedViewsImportPreview')).to_be_visible()
    audit_page_state(page, axe_source, f'{label} view import preview')
    page.locator('#cancelBtn').click()


def audit_view_delete(page: Page, axe_source: str, label: str) -> None:
    view = save_delete_audit_view(page, 'UnbrokenAccessibilityViewName' * 3, 'tag:accessibility-delete-view')
    remove = page.locator(f'[data-saved-view-delete-id="{view["id"]}"]')
    for language in ('zh-CN', 'en'):
        close_workspace_navigation(page)
        if page.locator('html').get_attribute('lang') != language:
            select_language(page, language)
            expect(page.locator('html')).to_have_attribute('lang', language)
            page.keyboard.press('Escape')
        reveal_workspace_control(page, remove).click()
        expect(page.locator('#savedViewDeleteName')).to_have_text(view['name'])
        expect(page.locator('#cancelBtn')).to_be_focused()
        assert page.locator('#savedViewDeleteConfirm').evaluate('node => node.scrollWidth <= node.clientWidth + 1 && node.getBoundingClientRect().right <= document.querySelector(".modal-content").getBoundingClientRect().right + 1'), 'Long view name is clipped in the deletion confirmation'
        audit_page_state(page, axe_source, f'{label} {language} saved-view deletion confirmation')
        page.locator('#cancelBtn').click()
        expect(remove).to_be_focused()
    close_workspace_navigation(page)
    page.locator('#clearSearchBtn').click()


def audit_task_reading(page: Page, axe_source: str) -> None:
    page.evaluate("""() => {
        window.auditNativeFileRead = FileReader.prototype.readAsText;
        FileReader.prototype.readAsText = function() {};
    }""")
    try:
        open_settings(page)
        with page.expect_file_chooser() as result:
            page.locator('#importBtn').click()
        result.value.set_files({'name': 'accessibility-tasks.json', 'mimeType': 'application/json', 'buffer': b'[]'})
        expect(page.locator('#taskImportReadStatus')).to_be_visible()
        audit_page_state(page, axe_source, 'cancellable task file reading')
        page.locator('#cancelBtn').click()
    finally:
        page.evaluate('() => { FileReader.prototype.readAsText = window.auditNativeFileRead; delete window.auditNativeFileRead; }')


def audit_task_draft_guard(page: Page, axe_source: str, label: str) -> None:
    return_to_task_workspace(page)
    open_task_editor(page)
    page.locator('#taskName').fill('Accessibility draft kept in this browser only')
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    audit_page_state(page, axe_source, f'{label} unsaved task prompt')
    page.locator('#draftKeepEditingBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_hidden()
    expect(page.locator('#taskName')).to_have_value('Accessibility draft kept in this browser only')
    page.locator('#cancelBtn').click()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()


def audit_batch_project(page: Page, axe_source: str) -> None:
    before = stored(page)
    enter_batch_mode(page)
    page.locator('#batchSelectVisibleBtn').click()
    audit_page_state(page, axe_source, 'batch selection')
    reveal_batch_action(page, 'move-project')
    audit_page_state(page, axe_source, 'batch More actions')
    click_batch_action(page, 'move-project')
    expect(page.locator('#batchMoveProjectInput')).to_be_visible()
    audit_page_state(page, axe_source, 'batch move project dialog')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('#exitBatchModeBtn').click()
    assert stored(page) == before, 'Auditing and cancelling batch movement changed stored data'


def audit_import_decision(page: Page, axe_source: str) -> None:
    before = stored(page)
    record = get_task_records(page)[0]
    open_settings(page, 'data')
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'small-a11y-import.json', 'mimeType': 'application/json',
                            'buffer': json.dumps([{**record, 'description': 'Incoming synthetic a11y preview'}]).encode()})
    expect(page.locator('#importOutcomeSummary')).to_be_visible()
    audit_page_state(page, axe_source, 'task import replacement decision')
    page.locator('#mergeImportMode').check()
    audit_page_state(page, axe_source, 'task import merge decision')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert stored(page) == before, 'Auditing import decisions wrote tasks, revision, history or settings'


def audit_task_draft_recovery(page: Page, axe_source: str, label: str) -> None:
    return_to_task_workspace(page)
    open_task_editor(page)
    page.locator('#taskName').fill('Accessibility unsaved quota draft')
    page.locator('#taskDesc').fill('Synthetic draft retained only in the current page memory')
    page.evaluate("""() => {
        const add = IDBObjectStore.prototype.add;
        IDBObjectStore.prototype.add = function(...args) {
            if (this.name !== 'tasks') return add.apply(this, args);
            IDBObjectStore.prototype.add = add;
            throw new DOMException('Synthetic draft accessibility quota failure', 'QuotaExceededError');
        };
    }""")
    page.locator('#submitBtn').click()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_disabled()
    audit_page_state(page, axe_source, f'{label} retained draft with unavailable storage')
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_enabled()
    audit_page_state(page, axe_source, f'{label} retained draft after storage recovery')
    page.locator('#taskDraftRecoveryDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    audit_page_state(page, axe_source, f'{label} discard retained draft confirmation')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskName')).to_have_value('Accessibility unsaved quota draft')
    expect(page.locator('#taskDesc')).to_have_value('Synthetic draft retained only in the current page memory')
    page.locator('#cancelBtn').click()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()


def audit_scaled_surfaces(browser, url: str, axe_source: str, viewport: dict) -> None:
    """Exercise pagination controls in an isolated synthetic workspace."""
    context = browser.new_context(locale='en-US', reduced_motion='reduce', viewport=viewport)
    page = context.new_page()
    try:
        clear_app_data(page, url)
        add_task(page, 'Accessibility pagination seed', no_deadline=True)
        day = page.evaluate("""() => {
            const d = new Date();
            return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        }""")
        page.evaluate("""day => new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(['tasks','config'], 'readwrite');
                const store = tx.objectStore('tasks');
                const all = store.getAll();
                all.onsuccess = () => {
                    const template = all.result[0];
                    const historical = [];
                    store.clear();
                    for (let i=0; i<121; i++) {
                        const undated = {...template, id:700000+i, name:`Undated accessibility ${i} 中文`, order:i*1000};
                        historical.push(undated);
                        store.put(undated);
                        store.put({...template, id:800000+i, name:`Dated accessibility ${i} 中文`, order:i*1000,
                            dueDate:day+'T12:00:00.000Z', dueAt:day+'T12:00:00.000Z', dueLocalDate:day,
                            dueLocalTime:'12:00', dueTimeZone:'UTC', reminderOffset:-1, reminderRepeat:-1});
                    }
                    tx.objectStore('config').put({key:'recoveryHistory', value:[{
                        id:'accessibility-history', createdAt:new Date().toISOString(), tasks:historical
                    }]});
                };
                tx.oncomplete = () => {db.close(); resolve();};
                tx.onabort = () => reject(tx.error);
            };
        })""", day)
        page.reload()
        wait_for_app_ready(page)
        for theme in ('light', 'dark'):
            if page.locator('html').get_attribute('data-theme') != theme:
                select_theme_preference(page, theme)
            close_workspace_navigation(page)
            label = f'{viewport["width"]}px {theme}'
            select_view(page, 'calendar')
            expect(page.locator('#calendarUndatedTasks .task-item')).to_have_count(100)
            expect(page.locator('[data-calendar-action="undated-more"]')).to_be_visible()
            audit_page_state(page, axe_source, f'{label} calendar pagination')
            assert_focus_visible(page, '[data-calendar-action="undated-more"]', label)
            day_entry = page.locator(f'[data-calendar-detail-date="{day}"]').filter(visible=True)
            expect(day_entry).to_have_count(1)
            expect(day_entry).to_be_visible()
            day_entry.click()
            expect(page.locator('#calendarDayTasks .calendar-detail-task')).to_have_count(100)
            audit_page_state(page, axe_source, f'{label} calendar day pagination')
            assert_focus_visible(page, '[data-calendar-action="detail-more"]', label)
            open_settings(page)
            page.locator('#recoveryBtn').click()
            expect(page.locator('#recoveryTaskPreview > li')).to_have_count(100)
            preview_details = page.locator('#recoveryPreviewDetails')
            if preview_details.count() and not preview_details.evaluate('element => element.open'):
                preview_details.locator(':scope > summary').click()
            assert page.locator('#recoveryTaskPreview').bounding_box()['height'] < viewport['height'] / 2, 'Recovery preview pushes actions below a full page of task rows'
            audit_page_state(page, axe_source, f'{label} recovery preview pagination')
            for selector in ('#recoveryPreviewMore', '#recoveryExportBtn', '#recoveryClearBtn'):
                assert_focus_visible(page, selector, label)
            page.locator('#recoveryPreviewMore').click()
            expect(page.locator('#recoveryTaskPreview > li')).to_have_count(121)
            expect(page.locator('#recoveryTaskPreview > li').nth(100)).to_be_focused()
            assert_focus_visible(page, '#recoveryTaskPreview > li:nth-child(101)', label)
            page.locator('#recoveryClearBtn').click()
            expect(page.locator('#recoveryClearConfirm')).to_be_visible()
            expect(page.locator('#cancelBtn')).to_be_focused()
            audit_page_state(page, axe_source, f'{label} clear recovery confirmation')
            page.locator('#cancelBtn').click()
            return_to_task_workspace(page)
            raw_quick_text = 'Accessibility quick-add draft 中文 #review /Audit'
            ensure_capture(page)
            page.locator('#quickAddInput').fill(raw_quick_text)
            inject_quota_failure(page)
            ensure_capture(page)
            page.locator('#quickAddInput').press('Enter')
            expect(page.locator('#quickAddRetainedMessage')).to_be_visible()
            expect(page.locator('#quickAddInput')).to_be_enabled()
            expect(page.locator('#quickAddInput')).to_have_attribute('readonly', '')
            audit_page_state(page, axe_source, f'{label} retained read-only quick-add text')
            assert_focus_visible(page, '#quickAddInput', label)
            page.locator('#retryStorageBtn').click()
            expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
            expect(page.locator('#quickAddInput')).to_have_value(raw_quick_text)
            expect(page.locator('#quickAddInput')).not_to_have_attribute('readonly', '')
            audit_page_state(page, axe_source, f'{label} same-page recovered quick-add text')
            ensure_capture(page)
            page.locator('#quickAddInput').fill('')
    finally:
        context.close()


def audit_context(url: str, axe_source: str, reduced_motion: bool = False, *, include_scaled: bool = True) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        context = browser.new_context(
            reduced_motion="reduce" if reduced_motion else "no-preference",
            viewport={"width": 390, "height": 844} if reduced_motion else {"width": 1280, "height": 720},
        )
        page = context.new_page()
        clear_app_data(page, url)
        exercise_workspace_navigation(page)
        audit_page_state(page, axe_source, "empty task list")
        seed_tasks(page)
        audit_subtask_checkbox_visibility(page, '390px' if reduced_motion else '1280px')
        audit_page_state(page, axe_source, "task list")
        audit_workspace_navigation(page, axe_source, 'light workspace navigation')
        audit_batch_project(page, axe_source)

        ensure_capture(page)
        audit_page_state(page, axe_source, 'global capture')
        open_task_editor(page)
        expect(page.locator("#taskModal")).to_be_visible()
        audit_page_state(page, axe_source, "task modal")
        page.locator("#cancelBtn").click()

        select_view(page, "calendar")
        audit_page_state(page, axe_source, "calendar view")
        select_view(page, "stats")
        audit_page_state(page, axe_source, "stats view")

        switch_to_english(page)
        select_view(page, "list")
        audit_page_state(page, axe_source, "english task list")
        for section in ('appearance', 'data', 'experience', 'cleanup', 'help'):
            open_settings(page, section)
            if section == 'appearance':
                assert_workspace_theme_gallery(page)
            audit_page_state(page, axe_source, f'english settings {section}')
        return_to_task_workspace(page)
        audit_views_transfer(page, axe_source, 'light')
        audit_view_delete(page, axe_source, 'light')
        audit_task_reading(page, axe_source)
        audit_import_decision(page, axe_source)
        audit_task_draft_guard(page, axe_source, 'light')
        audit_task_draft_recovery(page, axe_source, 'light')

        open_help(page)
        expect(page.locator('#helpDiagnosticsBtn')).to_be_visible()
        audit_page_state(page, axe_source, 'help dialog')
        page.locator('#helpDiagnosticsBtn').click()
        expect(page.locator('#diagnosticPreview')).to_be_visible()
        audit_page_state(page, axe_source, 'diagnostic preview')
        page.locator('#cancelBtn').click()
        open_settings(page)
        page.locator('#recoveryBtn').click()
        expect(page.locator('#recoverySelect')).to_have_count(1)
        audit_page_state(page, axe_source, 'recovery dialog')
        page.locator('#cancelBtn').click()
        open_settings(page)
        page.locator('#storageHealthBtn').click()
        expect(page.locator('#storageUsage')).to_be_visible()
        audit_page_state(page, axe_source, 'data safety dialog')
        page.locator('#cancelBtn').click()
        select_theme_preference(page, 'dark')
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        close_workspace_navigation(page)
        audit_page_state(page, axe_source, 'dark settings page')
        open_settings(page, 'appearance')
        assert_workspace_theme_gallery(page)
        audit_page_state(page, axe_source, 'dark workspace theme gallery')
        open_settings(page, 'data')
        return_to_task_workspace(page)
        audit_page_state(page, axe_source, 'dark task list')
        audit_workspace_navigation(page, axe_source, 'dark workspace navigation')
        audit_views_transfer(page, axe_source, 'dark')
        audit_view_delete(page, axe_source, 'dark')
        audit_task_draft_guard(page, axe_source, 'dark')
        audit_task_draft_recovery(page, axe_source, 'dark')
        open_help(page)
        audit_page_state(page, axe_source, 'dark help dialog')
        page.locator('#helpDiagnosticsBtn').click()
        expect(page.locator('#diagnosticPreview')).to_be_visible()
        audit_page_state(page, axe_source, 'dark diagnostic preview')
        page.locator('#cancelBtn').click()
        select_view(page, 'calendar')
        audit_page_state(page, axe_source, 'dark calendar')
        for kind in ('success', 'warning', 'error'):
            page.evaluate("""kind => {
                document.getElementById('notificationText').textContent = 'Notification contrast check';
                document.getElementById('notification').className = `notification ${kind} show`;
            }""", kind)
            audit_page_state(page, axe_source, f'dark {kind} notification')
        if include_scaled:
            audit_scaled_surfaces(browser, url, axe_source, {'width': 390, 'height': 844} if reduced_motion else {'width': 1280, 'height': 720})

        context.close()
        browser.close()
        print(f'Accessibility workflow completed: {"390px reduced motion" if reduced_motion else "1280px"}', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit task and settings surfaces with axe and real keyboard focus.')
    parser.add_argument('--skip-scaled', action='store_true', help='Audit normal task/settings workflows without the separate pagination workload')
    parser.add_argument('--collect-axe', action='store_true', help='Report all normal-workflow axe violations, then fail the run if any occurred')
    parser.add_argument('--viewport', choices=('both', 'desktop', 'mobile'), default='both', help='Resume only the affected viewport after a focused fix')
    args = parser.parse_args()
    audit_support.AXE_FAILURES = [] if args.collect_axe else None
    ensure_conda_library_path()
    axe_source = find_axe_source().read_text(encoding="utf-8")
    modes = (False, True) if args.viewport == 'both' else (args.viewport == 'mobile',)
    url = os.environ.get("TASK_TRACER_URL")
    if url:
        for reduced in modes:
            audit_context(url, axe_source, reduced_motion=reduced, include_scaled=not args.skip_scaled)
    else:
        with local_server() as local_url:
            for reduced in modes:
                audit_context(local_url, axe_source, reduced_motion=reduced, include_scaled=not args.skip_scaled)
    if audit_support.AXE_FAILURES:
        raise AssertionError(f'{len(audit_support.AXE_FAILURES)} audited states had axe violations; every violation is printed above')
    print("Accessibility/i18n audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
