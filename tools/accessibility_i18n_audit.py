#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from views_portability_playwright import payload as views_payload, view as saved_view, choose_file as choose_views_file
from task_draft_playwright import inject_quota_failure
from views_delete_playwright import save_named as save_delete_audit_view

from smoke_playwright import (
    add_task,
    assert_accessibility_baseline,
    browser_launch_options,
    clear_app_data,
    ensure_conda_library_path,
    future_date,
    local_server,
    select_view,
    wait_for_app_ready,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def find_axe_source() -> Path:
    source = REPO_ROOT / 'node_modules' / 'axe-core' / 'axe.min.js'
    if not source.is_file():
        raise AssertionError('Pinned axe-core is missing. Run npm ci --ignore-scripts in the repository root')
    return source


def inject_axe(page: Page, axe_source: str) -> None:
    page.add_script_tag(content=axe_source)


def run_axe(page: Page, axe_source: str, label: str) -> None:
    inject_axe(page, axe_source)
    results: dict[str, Any] = page.evaluate(
        """async () => {
            return await axe.run(document, {
                runOnly: {
                    type: 'tag',
                    values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
                }
            });
        }"""
    )
    violations = results.get("violations", [])
    serious = [
        violation for violation in violations
        if violation.get("impact") in {"critical", "serious", "moderate"}
    ]
    if serious:
        compact = [
            {
                "id": item.get("id"),
                "impact": item.get("impact"),
                "help": item.get("help"),
                "nodes": [{"target": node.get("target"), "failure": node.get("failureSummary")} for node in item.get("nodes", [])[:8]],
            }
            for item in serious
        ]
        raise AssertionError(f"axe violations during {label}:\n{json.dumps(compact, ensure_ascii=False, indent=2)}")


def assert_focus_visible(page: Page, selector: str, label: str) -> None:
    page.locator(selector).focus()
    expect(page.locator(selector)).to_be_focused()
    visible = page.evaluate(
        """() => {
            const el = document.activeElement;
            const style = getComputedStyle(el);
            const outline = Number.parseFloat(style.outlineWidth || '0');
            const boxShadow = style.boxShadow && style.boxShadow !== 'none';
            return outline > 0 || boxShadow;
        }"""
    )
    if not visible:
        raise AssertionError(f"Focused control has no visible focus treatment: {label}")


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
        '#viewSwitcher .view-tab[aria-selected="true"]',
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() and locator.is_visible() and locator.is_enabled():
            assert_focus_visible(page, selector, label)


def assert_layout(page: Page, label: str) -> None:
    metrics = page.evaluate(
        """() => {
            const doc = document.documentElement;
            const viewportWidth = window.innerWidth;
            const visibleControls = [...document.querySelectorAll('button:not([hidden]), input:not([type="hidden"]), select, textarea, a[href]')]
                .filter((el) => {
                    if (el.getAttribute('aria-hidden') === 'true' || el.classList.contains('native-select-hidden')) return false;
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                })
                .map((el) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        className: typeof el.className === 'string' ? el.className : '',
                        width: rect.width,
                        height: rect.height,
                        left: rect.left,
                        right: rect.right
                    };
                });
            return {
                viewportWidth,
                scrollWidth: doc.scrollWidth,
                smallControls: visibleControls.filter((item) => item.width < 24 || item.height < 24),
                overflowingControls: visibleControls.filter((item) => item.left < -1 || item.right > viewportWidth + 1)
            };
        }"""
    )
    if metrics["scrollWidth"] - metrics["viewportWidth"] > 1:
        raise AssertionError(f"{label} has horizontal overflow: {metrics}")
    if metrics["smallControls"]:
        raise AssertionError(f"{label} has undersized controls: {metrics['smallControls'][:8]}")
    if metrics["overflowingControls"]:
        raise AssertionError(f"{label} has controls outside viewport: {metrics['overflowingControls'][:8]}")


def switch_to_english(page: Page) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#langMenuToggle").click()
    page.locator('#lang-container .lang-btn[data-lang="en"]').click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.keyboard.press("Escape")


def audit_page_state(page: Page, axe_source: str, label: str) -> None:
    page.evaluate("""async () => {
        await Promise.all(document.getAnimations()
            .filter(animation => animation.effect?.getTiming().iterations !== Infinity)
            .map(animation => animation.finished.catch(() => {})));
    }""")
    assert_accessibility_baseline(page, label)
    run_axe(page, axe_source, label)
    assert_focus_baseline(page, label)
    assert_layout(page, label)


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
    page.locator('#openMenuBtn').click()
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
        if page.locator('html').get_attribute('lang') != language:
            page.locator('#openMenuBtn').click()
            page.locator('#langMenuToggle').click()
            page.locator(f'#lang-container .lang-btn[data-lang="{language}"]').click()
            expect(page.locator('html')).to_have_attribute('lang', language)
            page.keyboard.press('Escape')
        remove.click()
        expect(page.locator('#savedViewDeleteName')).to_have_text(view['name'])
        expect(page.locator('#cancelBtn')).to_be_focused()
        assert page.locator('#savedViewDeleteConfirm').evaluate('node => node.scrollWidth <= node.clientWidth + 1 && node.getBoundingClientRect().right <= document.querySelector(".modal-content").getBoundingClientRect().right + 1'), 'Long view name is clipped in the deletion confirmation'
        audit_page_state(page, axe_source, f'{label} {language} saved-view deletion confirmation')
        page.locator('#cancelBtn').click()
        expect(remove).to_be_focused()
    page.locator('#clearSearchBtn').click()


def audit_task_reading(page: Page, axe_source: str) -> None:
    page.evaluate("""() => {
        window.auditNativeFileRead = FileReader.prototype.readAsText;
        FileReader.prototype.readAsText = function() {};
    }""")
    try:
        page.locator('#openMenuBtn').click()
        with page.expect_file_chooser() as result:
            page.locator('#importBtn').click()
        result.value.set_files({'name': 'accessibility-tasks.json', 'mimeType': 'application/json', 'buffer': b'[]'})
        expect(page.locator('#taskImportReadStatus')).to_be_visible()
        audit_page_state(page, axe_source, 'cancellable task file reading')
        page.locator('#cancelBtn').click()
    finally:
        page.evaluate('() => { FileReader.prototype.readAsText = window.auditNativeFileRead; delete window.auditNativeFileRead; }')


def audit_task_draft_guard(page: Page, axe_source: str, label: str) -> None:
    page.locator('#openModalBtn').click()
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


def audit_task_draft_recovery(page: Page, axe_source: str, label: str) -> None:
    page.locator('#openModalBtn').click()
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
                page.locator('#themeToggleBtn').click()
            label = f'{viewport["width"]}px {theme}'
            select_view(page, 'calendar')
            expect(page.locator('#calendarUndatedTasks .task-item')).to_have_count(100)
            expect(page.locator('[data-calendar-action="undated-more"]')).to_be_visible()
            audit_page_state(page, axe_source, f'{label} calendar pagination')
            assert_focus_visible(page, '[data-calendar-action="undated-more"]', label)
            page.locator(f'[data-calendar-detail-date="{day}"]').click()
            expect(page.locator('#calendarDayTasks .calendar-detail-task')).to_have_count(100)
            audit_page_state(page, axe_source, f'{label} calendar day pagination')
            assert_focus_visible(page, '[data-calendar-action="detail-more"]', label)
            page.locator('#openMenuBtn').click()
            page.locator('#recoveryBtn').click()
            expect(page.locator('#recoveryTaskPreview > li')).to_have_count(100)
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
            raw_quick_text = 'Accessibility quick-add draft 中文 #review /Audit'
            page.locator('#quickAddInput').fill(raw_quick_text)
            inject_quota_failure(page)
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
            page.locator('#quickAddInput').fill('')
    finally:
        context.close()


def audit_context(url: str, axe_source: str, reduced_motion: bool = False) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        context = browser.new_context(
            reduced_motion="reduce" if reduced_motion else "no-preference",
            viewport={"width": 390, "height": 844} if reduced_motion else {"width": 1280, "height": 720},
        )
        page = context.new_page()
        clear_app_data(page, url)
        audit_page_state(page, axe_source, "empty task list")
        seed_tasks(page)
        audit_page_state(page, axe_source, "task list")

        page.locator("#openModalBtn").click()
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
        audit_views_transfer(page, axe_source, 'light')
        audit_view_delete(page, axe_source, 'light')
        audit_task_reading(page, axe_source)
        audit_task_draft_guard(page, axe_source, 'light')
        audit_task_draft_recovery(page, axe_source, 'light')

        page.locator('#helpBtn').click()
        expect(page.locator('#helpDiagnosticsBtn')).to_be_visible()
        audit_page_state(page, axe_source, 'help dialog')
        page.locator('#helpDiagnosticsBtn').click()
        expect(page.locator('#diagnosticPreview')).to_be_visible()
        audit_page_state(page, axe_source, 'diagnostic preview')
        page.locator('#cancelBtn').click()
        page.locator('#openMenuBtn').click()
        page.locator('#recoveryBtn').click()
        expect(page.locator('#recoverySelect')).to_have_count(1)
        audit_page_state(page, axe_source, 'recovery dialog')
        page.locator('#cancelBtn').click()
        page.locator('#openMenuBtn').click()
        page.locator('#storageHealthBtn').click()
        expect(page.locator('#storageUsage')).to_be_visible()
        audit_page_state(page, axe_source, 'data safety dialog')
        page.locator('#cancelBtn').click()
        page.locator('#themeToggleBtn').click()
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        audit_page_state(page, axe_source, 'dark task list')
        audit_views_transfer(page, axe_source, 'dark')
        audit_view_delete(page, axe_source, 'dark')
        audit_task_draft_guard(page, axe_source, 'dark')
        audit_task_draft_recovery(page, axe_source, 'dark')
        page.locator('#helpBtn').click()
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
        audit_scaled_surfaces(browser, url, axe_source, {'width': 390, 'height': 844} if reduced_motion else {'width': 1280, 'height': 720})

        context.close()
        browser.close()


def main() -> int:
    ensure_conda_library_path()
    axe_source = find_axe_source().read_text(encoding="utf-8")
    url = os.environ.get("TASK_TRACER_URL")
    if url:
        audit_context(url, axe_source)
        audit_context(url, axe_source, reduced_motion=True)
    else:
        with local_server() as local_url:
            audit_context(local_url, axe_source)
            audit_context(local_url, axe_source, reduced_motion=True)
    print("Accessibility/i18n audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
