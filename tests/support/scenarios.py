"""Reusable UI scenarios shared by focused browser checks."""
from __future__ import annotations
from tests.support.paths import input_path
import json
import re
import tempfile
from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect

from tests.support.browser import (
    assert_accessibility_baseline,
    assert_backup_payload_integrity,
    get_task_records,
    is_workbench_v5,
    open_settings,
    return_to_task_workspace,
    select_filter,
    select_language,
    task_locator,
    wait_for_notification,
)

def exercise_export_backup(page: Page) -> dict[str, Any]:
    open_settings(page)
    with page.expect_download() as download_info:
        page.locator("#backupBtn").click()
    download = download_info.value
    path = download.path()
    if not path:
        raise AssertionError("Export/backup did not produce a readable download file")

    backup = json.loads(Path(path).read_text(encoding="utf-8"))
    includes = set((backup.get("schema") or {}).get("includes") or [])
    if backup.get("version") != "2.4" or backup.get("type") != "backup" or not backup.get("date") or not backup.get("versionNotes") or "todayPlan" not in includes:
        raise AssertionError(f"Export/backup payload metadata is incomplete: {backup}")
    assert_backup_payload_integrity(backup, "backup")
    if not isinstance(backup.get("tasks"), list) or not backup["tasks"]:
        raise AssertionError(f"Export/backup payload did not include tasks: {backup}")
    last_backup = page.evaluate(
        """async () => {
            return await new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['config'], 'readonly');
                    const get = tx.objectStore('config').get('lastBackupAt');
                    get.onsuccess = () => {
                        db.close();
                        resolve(get.result ? get.result.value : null);
                    };
                    get.onerror = () => reject(get.error);
                };
            });
        }"""
    )
    if not last_backup:
        raise AssertionError("Backup did not record the last backup timestamp")
    open_settings(page)
    expect(page.locator("#backupHealthText")).to_contain_text(re.compile("今天|today", re.I))
    page.keyboard.press("Escape")
    return backup

def exercise_import(page: Page, imported_name: str) -> None:
    payload = [
        {
            "id": 10001,
            "name": imported_name,
            "description": "Imported by Playwright smoke test.",
            "dueDate": None,
            "createdAt": "2025-05-10T00:00:00.000Z",
            "completed": "false",
            "archived": "false",
            "repeatPaused": "false",
            "order": 1000,
            "subtasks": [
                {"id": 20001, "text": "Imported subtask A", "completed": "false"},
                {"id": 20001, "text": "Imported subtask B", "completed": 0},
            ],
        }
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump(payload, temp_file)
        temp_path = temp_file.name

    try:
        before_import = get_task_records(page)
        open_settings(page)
        with page.expect_file_chooser() as chooser_info:
            page.locator("#importBtn").click()
        chooser_info.value.set_files(temp_path)
        expect(page.locator("#taskModal")).to_be_visible()
        expect(page.locator("#modalTitle")).to_have_text(re.compile("导入预览|Import Preview", re.I))
        expect(page.locator("#replaceImportMode")).to_be_checked()
        metadata = page.locator('[data-import-preview]').evaluate('node => node.importPreviewData')
        expected_matches = [imported_name] if any(
            task['name'].strip().lower() == imported_name.strip().lower() for task in before_import) else []
        assert metadata['currentCount'] == len(before_import) and metadata['importCount'] == 1
        assert metadata['fileDuplicateNames'] == [] and metadata['duplicateIds'] == []
        assert metadata['existingDuplicateNames'] == expected_matches
        language = page.locator('html').get_attribute('lang') or 'zh-CN'
        translations = json.loads((input_path('resources' + '/' + f'{language}.json')).read_text())
        expect(page.locator('#importOutcomeSummary')).to_have_text(
            translations['dataReview']['replaceSummary'].format(current=len(before_import), incoming=1, after=1))
        reference = page.locator('.import-reference')
        if not reference.evaluate('element => element.open'):
            reference.locator(':scope > summary').click()
        expect(page.locator('.import-diff-preview')).to_be_visible()
        expect(page.locator('.import-diff-preview')).to_contain_text(imported_name)
        counts = page.locator('.import-diff-count').all_inner_texts()
        assert counts == [str(0 if expected_matches else 1), str(len(expected_matches)), str(len(before_import))], counts
        expect(page.locator('.confirm-row')).to_have_count(0)
        assert get_task_records(page) == before_import, 'Reviewing import counts and tasks changed current data'
        with page.expect_download() as snapshot_info:
            page.locator("#submitBtn").click()
        snapshot_path = snapshot_info.value.path()
        if not snapshot_path:
            raise AssertionError("Replace import did not download a pre-import snapshot")
        snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        assert_backup_payload_integrity(snapshot, "pre-import-backup")
        if not isinstance(snapshot.get("tasks"), list) or len(snapshot["tasks"]) == 0:
            raise AssertionError(f"Pre-import snapshot did not include current tasks: {snapshot}")
        assert snapshot['tasks'] == before_import, 'Pre-import snapshot differs from current task records'
        assert get_task_records(page) == before_import, 'Snapshot download prematurely replaced current tasks'
        expect(page.locator('[data-import-preview]')).to_have_attribute('data-pre-import-snapshot-confirmed', 'true')
        expect(page.locator("#taskModal")).to_be_visible()
        if page.locator('#workspaceSidebarScroll').count():
            language = page.locator('html').get_attribute('lang') or 'zh-CN'
            translations = json.loads((input_path('resources' + '/' + f'{language}.json')).read_text())
            expect(page.locator('#submitBtn')).to_have_text(translations['dataReview']['importReplaceActionOne'].replace('{count}', '1'))
            expect(page.locator('#submitBtn')).to_have_class(re.compile(r'(^|\s)btn-danger(\s|$)'))
        else:
            expect(page.locator("#submitBtn")).to_have_text(re.compile("继续替换导入|Continue Replace Import", re.I))
        page.locator("#submitBtn").click()
        wait_for_notification(page, re.compile("导入|import", re.I))
        select_filter(page, "all")
        imported_task = task_locator(page, imported_name)
        expect(imported_task).to_have_count(1)
        expect(page.locator(".task-item")).to_have_count(1)
        record = next((item for item in get_task_records(page) if item["name"] == imported_name), None)
        if not record:
            raise AssertionError("Imported task was not written to IndexedDB")
        if record.get("completed") is not False or record.get("archived") is not False or record.get("repeatPaused") is not False:
            raise AssertionError(f"Imported task booleans were not normalized: {record}")
        if any(subtask.get("completed") is not False for subtask in record.get("subtasks", [])):
            raise AssertionError(f"Imported subtask booleans were not normalized: {record}")
        expect(imported_task.locator(".subtasks-wrapper .progress-text")).to_contain_text("0/2")
        imported_task.locator(".subtask-summary-bar").click()
        expect(imported_task.locator(".subtask-display-item")).to_have_count(2)
        imported_task.locator(".subtask-display-item").nth(1).click()
        expect(imported_task.locator(".subtasks-wrapper .progress-text")).to_contain_text("1/2")
        expect(imported_task.locator(".subtask-display-item").first.locator(".subtask-checkbox")).not_to_be_checked()
        expect(imported_task.locator(".subtask-display-item").nth(1).locator(".subtask-checkbox")).to_be_checked()
    finally:
        Path(temp_path).unlink(missing_ok=True)

def exercise_language(page: Page) -> None:
    before = get_task_records(page)
    for language in ('en', 'zh-CN'):
        translations = json.loads((input_path('resources' + '/' + f'{language}.json')).read_text())
        select_language(page, language)
        expect(page.locator('h1:visible')).to_have_count(1)
        expect(page.locator('#workspaceTitle')).to_have_text(translations['workspace']['allTasks'])
        expect(page.locator('#currentFilterLabel')).to_have_text(translations['filters']['active'])
        assert page.title() == translations['app']['title'], page.title()
        expect(page.locator('.controls-bar')).to_have_attribute('aria-label', translations['app']['toolbar'])
        if page.locator('#settingsWorkspace').count():
            open_settings(page, 'appearance')
            expect(page.locator('#languageSelect')).to_be_visible()
        expect(page.locator('#languageSelect')).to_have_role('combobox')
        expect(page.locator('#languageSelect')).to_have_accessible_name(translations['workspace']['language'])
        if page.locator('#settingsWorkspace').count():
            return_to_task_workspace(page)
        assert get_task_records(page) == before, 'Changing the UI language changed stored tasks'
    assert_accessibility_baseline(page, 'language preference')
    page.keyboard.press('Escape')

def exercise_workspace_navigation(page: Page) -> None:
    toggle = page.locator('#workspaceNavToggle')
    if not toggle.is_visible():
        return
    sidebar = page.locator('#workspaceSidebar')
    if toggle.get_attribute('aria-expanded') == 'true':
        page.keyboard.press('Escape')
    expect(toggle).to_have_attribute('aria-expanded', 'false')
    expect(sidebar).to_have_attribute('aria-hidden', 'true')
    expect(sidebar).to_have_js_property('inert', True)
    toggle.focus()
    sidebar.locator('button').first.focus()
    expect(toggle).to_be_focused()
    for _ in range(8):
        page.keyboard.press('Tab')
        assert not sidebar.evaluate('node => node.contains(document.activeElement)'), 'Closed navigation received Tab focus'
    toggle.focus()
    toggle.press('Enter')
    expect(toggle).to_have_attribute('aria-expanded', 'true')
    expect(sidebar).to_have_attribute('aria-hidden', 'false')
    expect(sidebar).to_have_js_property('inert', False)
    if page.locator('#workspaceSidebarScroll').count():
        if page.locator('#workspaceScopeNav').count():
            selected = sidebar.locator('.workspace-nav-button[aria-pressed="true"]')
            current = selected if selected.count() else sidebar.locator('.workspace-nav-button').first
        elif is_workbench_v5(page):
            current = sidebar.locator('.workspace-nav-button[aria-current="page"]')
        else:
            current = (sidebar.locator('.workspace-sidebar-footer #workspaceSettingsBtn')
                       if page.locator('#settingsWorkspace').is_visible()
                       else sidebar.locator('.workspace-nav-button[aria-pressed="true"]'))
        expect(current).to_have_count(1)
        expect(current).to_be_focused()
        expect(current).to_be_in_viewport()
    else:
        expect(sidebar.locator('button').first).to_be_focused()
    assert_accessibility_baseline(page, 'open workspace navigation')
    page.keyboard.press('Escape')
    expect(toggle).to_have_attribute('aria-expanded', 'false')
    expect(sidebar).to_have_js_property('inert', True)
    expect(toggle).to_be_focused()
