#!/usr/bin/env python3
"""Check task draft close, unload, failure, and delayed-save session safety."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Error, Page, expect, sync_playwright

from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task,
    browser_launch_options,
    clear_app_data,
    edit_task,
    get_task_records,
    local_server,
    task_locator,
    wait_for_app_ready,
)


def unload_is_guarded(page: Page) -> bool:
    return page.evaluate("""() => {
        const event = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(event);
        return event.defaultPrevented;
    }""")


def discard(page: Page, retained: bool = False) -> None:
    if not page.locator('#draftDiscardPrompt').is_visible():
        page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert unload_is_guarded(page) is retained


def check_close_paths(page: Page) -> None:
    assert not unload_is_guarded(page)
    for close in ('cancel', 'x', 'escape', 'background'):
        page.locator('#openModalBtn').click()
        assert not unload_is_guarded(page)
        if close == 'cancel':
            page.locator('#cancelBtn').click()
        elif close == 'x':
            page.locator('#closeModalBtn').click()
        elif close == 'escape':
            page.keyboard.press('Escape')
        else:
            page.locator('#taskModal').click(position={'x': 2, 'y': 2})
        expect(page.locator('#taskModal')).to_be_hidden()
        expect(page.locator('#draftDiscardPrompt')).to_have_count(0)

    for close in ('cancel', 'x', 'escape', 'background'):
        page.locator('#openModalBtn').click()
        name = f'Unsaved {close} draft'
        page.locator('#taskName').fill(name)
        page.locator('#taskDesc').fill('A private draft description, retained only in this form.')
        page.locator('#dueDate').fill('2031-04-09')
        page.locator('#dueTime').fill('14:25')
        page.locator('#repeatType').select_option('weekly-days')
        page.locator('#repeatWeekday2').check()
        page.locator('#repeatPaused').check()
        page.locator('#subtaskInput').fill('First draft subtask')
        page.locator('#addSubtaskBtn').click()
        page.locator('#subtaskInput').fill('Unsubmitted subtask text')
        page.locator('#taskDesc').focus()
        assert unload_is_guarded(page)
        if close == 'cancel':
            page.locator('#cancelBtn').click()
        elif close == 'x':
            page.locator('#closeModalBtn').click()
        elif close == 'escape':
            page.keyboard.press('Escape')
        else:
            page.locator('#taskModal').click(position={'x': 2, 'y': 2})
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#draftDiscardPrompt')).to_be_visible()
        expect(page.locator('#taskModal')).to_have_attribute('aria-labelledby', 'draftDiscardTitle')
        expect(page.locator('#draftKeepEditingBtn')).to_be_focused()
        assert unload_is_guarded(page)
        assert page.locator('#taskName').evaluate('(el) => el.closest(".form-group").inert')
        page.keyboard.press('Shift+Tab')
        expect(page.locator('#draftDiscardBtn')).to_be_focused()
        page.keyboard.press('Tab')
        expect(page.locator('#draftKeepEditingBtn')).to_be_focused()
        page.keyboard.press('Tab')
        expect(page.locator('#draftDiscardBtn')).to_be_focused()
        page.keyboard.press('Tab')
        expect(page.locator('#draftKeepEditingBtn')).to_be_focused()
        if close == 'escape':
            page.keyboard.press('Escape')
        else:
            page.locator('#draftKeepEditingBtn').click()
        expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
        expect(page.locator('#taskDesc')).to_be_focused()
        expect(page.locator('#taskName')).to_have_value(name)
        expect(page.locator('#taskDesc')).to_have_value('A private draft description, retained only in this form.')
        expect(page.locator('#dueDate')).to_have_value('2031-04-09')
        expect(page.locator('#dueTime')).to_have_value('14:25')
        expect(page.locator('#repeatWeekday2')).to_be_checked()
        expect(page.locator('#repeatPaused')).to_be_checked()
        expect(page.locator('#subtaskListPreview .subtask-preview-text')).to_have_text('First draft subtask')
        expect(page.locator('#subtaskInput')).to_have_value('Unsubmitted subtask text')
        expect(page.locator('#submitBtn')).to_be_enabled()
        discard(page)
        expect(page.locator('#openModalBtn')).to_be_focused()
        assert get_task_records(page) == []
    page.locator('#openModalBtn').click()
    expect(page.locator('#taskName')).to_have_value('')
    expect(page.locator('#taskDesc')).to_have_value('')
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(0)
    page.locator('#taskName').fill('Reverted change')
    page.locator('#taskName').fill('')
    assert not unload_is_guarded(page)
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    print('New forms: all four close paths, full draft retention, prompt focus, explicit discard, and reverted changes passed')


def check_single_field_changes(page: Page) -> None:
    changes = (
        ('#taskDesc', 'Only description'),
        ('#taskProject', 'Only project'),
        ('#taskTags', 'only-tag'),
        ('#dueDate', '2031-11-21'),
        ('#dueTime', '23:17'),
        ('#subtaskInput', 'Only unsubmitted subtask'),
    )
    for selector, value in changes:
        page.locator('#openModalBtn').click()
        page.locator(selector).fill(value)
        assert unload_is_guarded(page), selector
        discard(page)
    for selector, value in (('#reminderOffset', '60'), ('#repeatType', 'custom')):
        page.locator('#openModalBtn').click()
        page.locator(selector).select_option(value)
        if selector == '#repeatType':
            page.locator('#repeatInterval').fill('7')
        assert unload_is_guarded(page), selector
        discard(page)
    page.locator('#openModalBtn').click()
    page.locator('#noDeadline').check()
    assert unload_is_guarded(page)
    discard(page)
    print('Description, project, tags, deadline, reminder, repeat, and unsubmitted subtask changes independently trigger protection')


def check_edit_and_stale(page: Page, url: str) -> None:
    add_task(page, 'Existing task', description='Original description', no_deadline=True, subtasks=['Original subtask'])
    expect(page.locator('#taskModal')).to_be_hidden()
    original = get_task_records(page)
    click_task_action(task_locator(page, 'Existing task'), 'edit')
    assert not unload_is_guarded(page)
    page.keyboard.press('Escape')
    expect(page.locator('#taskModal')).to_be_hidden()
    click_task_action(task_locator(page, 'Existing task'), 'edit')
    page.locator('#subtaskListPreview .subtask-preview-text').click()
    page.locator('#subtaskListPreview .subtask-edit-input').fill('Changed subtask draft')
    assert unload_is_guarded(page)
    page.keyboard.press('Escape')
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').click()
    assert unload_is_guarded(page)
    expect(page.locator('#subtaskListPreview .subtask-preview-text')).to_have_text('Changed subtask draft')
    discard(page)
    assert get_task_records(page) == original

    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        click_task_action(task_locator(page, 'Existing task'), 'edit')
        page.locator('#taskName').fill('Stale local draft')
        page.locator('#taskDesc').fill('Never overwrite the newer saved record')
        edit_task(other, 'Existing task', 'Newer remote task')
        latest = get_task_records(other)
        page.locator('#submitBtn').click()
        expect(page.locator('#submitBtn')).to_be_enabled()
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskName')).to_have_value('Stale local draft')
        assert unload_is_guarded(page)
        assert get_task_records(page) == latest
        page.locator('#cancelBtn').click()
        expect(page.locator('#draftDiscardPrompt')).to_be_visible()
        page.locator('#draftKeepEditingBtn').click()
        page.locator('#submitBtn').click()
        expect(page.locator('#submitBtn')).to_be_enabled()
        assert unload_is_guarded(page)
        discard(page)
        assert get_task_records(page) == latest
    finally:
        other.close()
    print('Existing unchanged edits close directly; subtask-only and stale drafts remain protected without changing committed data')


def check_failed_save(page: Page) -> None:
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Retry after failed write')
    page.locator('#taskDesc').fill('Keep after transaction failure')
    before = get_task_records(page)
    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.add;
        IDBObjectStore.prototype.add = function(...args) {
            if (this.name === 'tasks') {
                IDBObjectStore.prototype.add = original;
                throw new Error('Synthetic task write failure');
            }
            return original.apply(this, args);
        };
    }""")
    page.locator('#submitBtn').click()
    expect(page.locator('#submitBtn')).to_be_enabled()
    expect(page.locator('#taskDraftSavingStatus')).to_have_count(0)
    expect(page.locator('#taskDesc')).to_be_focused()
    expect(page.locator('#taskDesc')).to_have_value('Keep after transaction failure')
    assert unload_is_guarded(page)
    assert get_task_records(page) == before
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').click()
    page.locator('#taskDesc').fill('Retried and committed')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert not unload_is_guarded(page)
    saved = [task for task in get_task_records(page) if task['name'] == 'Retry after failed write']
    assert len(saved) == 1 and saved[0]['description'] == 'Retried and committed', saved
    print('A genuine aborted write preserves the draft and unlocks editing; explicit retry commits once and closes normally')


def hold_next_task_completion(page: Page) -> None:
    page.evaluate("""() => {
        const original = IDBDatabase.prototype.transaction;
        window.taskWriteCommitted = false;
        window.finishTaskWrite = null;
        IDBDatabase.prototype.transaction = function(names, mode, ...rest) {
            const tx = original.call(this, names, mode, ...rest);
            if (mode === 'readwrite' && Array.from(tx.objectStoreNames).includes('tasks')) {
                IDBDatabase.prototype.transaction = original;
                let handler;
                Object.defineProperty(tx, 'oncomplete', {
                    configurable: true,
                    get: () => handler,
                    set: value => { handler = value; }
                });
                tx.addEventListener('complete', event => {
                    window.taskWriteCommitted = true;
                    window.finishTaskWrite = () => {
                        window.finishTaskWrite = null;
                        handler?.call(tx, event);
                    };
                });
            }
            return tx;
        };
    }""")


def check_delayed_save(page: Page) -> None:
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Committed while saving indicator waits')
    page.locator('#taskDesc').fill('Immutable submitted snapshot')
    hold_next_task_completion(page)
    page.locator('#submitBtn').click()
    page.wait_for_function('() => window.taskWriteCommitted')
    expect(page.locator('#taskDraftSavingStatus')).to_be_visible()
    expect(page.locator('#taskDraftSavingStatus')).to_be_focused()
    for selector in ('#cancelBtn', '#closeModalBtn', '#submitBtn'):
        expect(page.locator(selector)).to_be_disabled()
    assert page.locator('#taskName').evaluate('(el) => el.closest(".form-group").inert')
    page.keyboard.press('Tab')
    expect(page.locator('#taskDraftSavingStatus')).to_be_focused()
    page.keyboard.press('Escape')
    page.locator('#taskModal').click(position={'x': 2, 'y': 2})
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
    page.locator('#taskName').evaluate('(el) => el.focus()')
    page.keyboard.type('Cannot alter saving task')
    expect(page.locator('#taskName')).to_have_value('Committed while saving indicator waits')
    records = get_task_records(page)
    assert any(task['name'] == 'Committed while saving indicator waits' for task in records)
    page.evaluate('() => window.finishTaskWrite()')
    expect(page.locator('#taskModal')).to_be_hidden()
    assert not unload_is_guarded(page)

    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Older save that finishes later')
    hold_next_task_completion(page)
    page.locator('#submitBtn').click()
    page.wait_for_function('() => window.taskWriteCommitted')
    page.locator('#openModalBtn').dispatch_event('click')
    expect(page.locator('#taskName')).to_have_value('')
    expect(page.locator('#submitBtn')).to_be_enabled()
    page.locator('#taskName').fill('Newer unsaved form must survive')
    page.locator('#taskDesc').fill('Later form remains editable')
    page.evaluate('() => window.finishTaskWrite()')
    expect(task_locator(page, 'Older save that finishes later')).to_have_count(1)
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value('Newer unsaved form must survive')
    expect(page.locator('#submitBtn')).to_be_enabled()
    assert not page.locator('#taskName').evaluate('(el) => el.closest(".form-group").inert')
    assert unload_is_guarded(page)
    discard(page)
    assert all(task['name'] != 'Newer unsaved form must survive' for task in get_task_records(page))

    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Save completing behind a later import gate')
    hold_next_task_completion(page)
    page.locator('#submitBtn').click()
    page.wait_for_function('() => window.taskWriteCommitted')
    page.evaluate("""() => {
        const original = FileReader.prototype.readAsText;
        FileReader.prototype.readAsText = function() {
            FileReader.prototype.readAsText = original;
            window.taskReadHeld = true;
        };
    }""")
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').dispatch_event('click')
    chooser.value.set_files({'name': 'held-tasks.json', 'mimeType': 'application/json', 'buffer': b'[]'})
    page.wait_for_function('() => window.taskReadHeld === true')
    expect(page.locator('#taskImportReadStatus')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_disabled()
    assert not unload_is_guarded(page)
    page.evaluate('() => window.finishTaskWrite()')
    expect(task_locator(page, 'Save completing behind a later import gate')).to_have_count(1)
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    expect(page.locator('#taskImportReadStatus')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_disabled()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    print('Real committed transaction delay: saving freezes input and close paths; late completion preserves both a later draft and a disabled import gate')


def check_native_beforeunload(page: Page) -> None:
    dialogs = []

    def cancel_unload(dialog):
        dialogs.append(dialog.type)
        dialog.dismiss()

    page.on('dialog', cancel_unload)
    try:
        page.locator('#openModalBtn').click()
        page.reload(wait_until='domcontentloaded')
        wait_for_app_ready(page)
        assert dialogs == [], 'An unchanged form unexpectedly blocked navigation'
        page.locator('#openModalBtn').click()
        page.locator('#taskName').fill('Native unload cancellation draft')
        try:
            page.reload(timeout=10_000, wait_until='domcontentloaded')
        except Error as error:
            if not dialogs:
                raise AssertionError(f'Navigation failed without a beforeunload dialog: {error}') from error
        if dialogs:
            assert dialogs == ['beforeunload'], dialogs
            expect(page.locator('#taskName')).to_have_value('Native unload cancellation draft')
            assert unload_is_guarded(page)
            discard(page)
            print('Native beforeunload cancellation preserved the live task draft')
        else:
            wait_for_app_ready(page)
            print('Engine did not surface a native beforeunload dialog; cancelable event gating was verified separately')
    finally:
        page.remove_listener('dialog', cancel_unload)


def inject_quota_failure(page: Page, method: str = 'add') -> None:
    page.evaluate("""method => {
        const original = IDBObjectStore.prototype[method];
        IDBObjectStore.prototype[method] = function(...args) {
            if (this.name === 'tasks') {
                IDBObjectStore.prototype[method] = original;
                throw new DOMException('Synthetic full storage', 'QuotaExceededError');
            }
            return original.apply(this, args);
        };
    }""", method)


def downloaded_drafts(page: Page):
    with page.expect_download() as download:
        page.locator('#taskDraftRecoveryDownloadBtn').click()
    payload = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
    assert payload['app'] == 'Task Tracer' and payload['type'] == 'task-draft'
    assert 'tasks' not in payload and payload['version'] == '1.0'
    return payload['drafts']


def retry_memory_storage(page: Page) -> None:
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_enabled()
    assert page.evaluate('() => window.taskDraftOriginalDocument === true'), 'Retry reloaded away memory drafts'


def check_quota_recovery(page: Page, url: str) -> None:
    before = get_task_records(page)
    page.evaluate('() => { window.taskDraftOriginalDocument = true; }')
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Quota interrupted unsaved draft')
    page.locator('#taskDesc').fill('This draft is not in any committed task backup')
    page.locator('#taskProject').fill('Unsaved private project')
    page.locator('#taskTags').fill('draft, retain')
    page.locator('#dueDate').fill('2032-05-06')
    page.locator('#dueTime').fill('16:35')
    page.locator('#repeatType').select_option('custom')
    page.locator('#repeatInterval').fill('9')
    page.locator('#subtaskInput').fill('Retain this subtask')
    page.locator('#addSubtaskBtn').click()
    page.locator('#subtaskInput').fill('Also retain unsubmitted subtask text')
    inject_quota_failure(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_disabled()
    expect(page.locator('#taskDraftRecoveryDownloadBtn')).to_be_focused()
    assert unload_is_guarded(page)
    assert get_task_records(page) == before
    drafts = downloaded_drafts(page)
    assert len(drafts) == 1
    recovered = drafts[0]
    assert recovered['editingTaskId'] is None
    assert recovered['form']['values']['name'] == 'Quota interrupted unsaved draft'
    assert recovered['form']['values']['desc'] == 'This draft is not in any committed task backup'
    assert recovered['form']['values']['subtask'] == 'Also retain unsubmitted subtask text'
    assert recovered['form']['subtasks'][0]['text'] == 'Retain this subtask'
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    page.locator('#taskDraftRecoveryDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_visible()
    assert len(downloaded_drafts(page)) == 1, 'Cancelling discard removed a retained draft'

    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(record, ...rest) {
            if (this.name === 'config' && record.key === '__task_tracer_storage_probe__') {
                IDBObjectStore.prototype.put = original;
                throw new DOMException('Synthetic quota persists during retry', 'QuotaExceededError');
            }
            return original.call(this, record, ...rest);
        };
    }""")
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#retryStorageBtn')).to_be_enabled()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    assert downloaded_drafts(page)[0]['id'] == recovered['id']
    retry_memory_storage(page)
    assert unload_is_guarded(page)
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('A later current form must not be overwritten')
    expect(page.locator('#taskDraftRecoveryRestoreBtn')).to_be_disabled()
    expect(page.locator('#taskDraftRecoveryDiscardBtn')).to_be_disabled()
    page.locator('#taskDraftRecoveryRestoreBtn').dispatch_event('click')
    expect(page.locator('#taskName')).to_have_value('A later current form must not be overwritten')
    discard(page, retained=True)
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskDraftRecoveryBanner')).to_be_hidden()
    expect(page.locator('#taskName')).to_have_value('Quota interrupted unsaved draft')
    expect(page.locator('#taskProject')).to_have_value('Unsaved private project')
    expect(page.locator('#taskTags')).to_have_value('draft, retain')
    expect(page.locator('#dueDate')).to_have_value('2032-05-06')
    expect(page.locator('#dueTime')).to_have_value('16:35')
    expect(page.locator('#repeatType')).to_have_value('custom')
    expect(page.locator('#repeatInterval')).to_have_value('9')
    expect(page.locator('#subtaskInput')).to_have_value('Also retain unsubmitted subtask text')
    assert unload_is_guarded(page)
    page.locator('#addSubtaskBtn').click()
    inject_quota_failure(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    repeated = downloaded_drafts(page)
    assert len(repeated) == 1 and repeated[0]['id'] == recovered['id']
    retry_memory_storage(page)
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert not unload_is_guarded(page)
    saved = [task for task in get_task_records(page) if task['name'] == 'Quota interrupted unsaved draft']
    assert len(saved) == 1 and len(saved[0]['subtasks']) == 2
    assert saved[0]['repeatType'] == 'custom' and saved[0]['repeatInterval'] == 9

    add_task(page, 'Quota edit original', description='Original saved record', no_deadline=True, subtasks=['Original child'])
    click_task_action(task_locator(page, 'Quota edit original'), 'edit')
    page.locator('#taskName').fill('Quota local edit draft')
    page.locator('#taskDesc').fill('Do not overwrite a newer task after recovery')
    inject_quota_failure(page, 'put')
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    old_edit = downloaded_drafts(page)[0]
    assert json.loads(old_edit['editingTaskSnapshot'])['name'] == 'Quota edit original'
    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        edit_task(other, 'Quota edit original', 'Quota newer remote record')
        remote = get_task_records(other)
        retry_memory_storage(page)
        page.locator('#taskDraftRecoveryRestoreBtn').click()
        expect(page.locator('#taskName')).to_have_value('Quota local edit draft')
        page.locator('#submitBtn').click()
        expect(page.locator('#submitBtn')).to_be_enabled()
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskDesc')).to_have_value('Do not overwrite a newer task after recovery')
        assert get_task_records(page) == remote
        assert unload_is_guarded(page)
        discard(page)
    finally:
        other.close()

    saved_before_queue = get_task_records(page)
    for name in ('First queued unsaved task', 'Second queued unsaved task'):
        page.locator('#openModalBtn').click()
        page.locator('#taskName').fill(name)
        inject_quota_failure(page)
        page.locator('#submitBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        retry_memory_storage(page)
    queued = downloaded_drafts(page)
    assert [draft['form']['values']['name'] for draft in queued] == ['First queued unsaved task', 'Second queued unsaved task']
    page.locator('#taskDraftRecoveryDiscardBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    remaining = downloaded_drafts(page)
    assert len(remaining) == 1 and remaining[0]['id'] == queued[1]['id']
    assert get_task_records(page) == saved_before_queue
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskName')).to_have_value('Second queued unsaved task')
    discard(page)

    click_task_action(task_locator(page, 'Quota newer remote record'), 'edit')
    page.locator('#subtaskListPreview .subtask-preview-text').click()
    page.locator('#subtaskListPreview .subtask-edit-input').fill('  In-progress inline subtask text  ')
    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(record, ...rest) {
            if (this.name === 'config' && record.key === 'language') {
                IDBObjectStore.prototype.put = original;
                throw new DOMException('Synthetic settings quota interrupts an inline edit', 'QuotaExceededError');
            }
            return original.call(this, record, ...rest);
        };
    }""")
    page.locator('#languageSelect').evaluate("""select => {
        select.value = 'en';
        select.dispatchEvent(new Event('change', {bubbles: true}));
    }""")
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#languageSelect')).to_have_value(page.locator('html').get_attribute('lang'))
    inline = downloaded_drafts(page)[0]
    assert inline['editingSubtaskIndex'] == 0
    assert inline['form']['subtasks'][0]['text'] == '  In-progress inline subtask text  '
    retry_memory_storage(page)
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#subtaskListPreview .subtask-edit-input')).to_have_value('  In-progress inline subtask text  ')
    discard(page)
    assert get_task_records(page) == saved_before_queue
    print('Quota: genuine abort, downloadable raw/partial drafts, failed retry, same-document recovery, repeat-failure deduplication, queued discard, blocked overwrite, and stale edit conflict passed')


def check_weekday_recovery(page: Page) -> None:
    before = get_task_records(page)
    page.evaluate('() => { window.taskDraftOriginalDocument = true; }')
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Quota weekday raw selection draft')
    page.locator('#repeatType').select_option('weekly-days')
    for value in ('0', '1', '2', '3', '4', '5', '6'):
        page.locator(f'#repeatWeekday{value}').uncheck()
    assert page.locator('.repeat-weekday-input:checked').count() == 0
    inject_quota_failure(page)
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    drafts = downloaded_drafts(page)
    assert drafts[0]['form']['values']['weekdays'] == [False] * 7
    retry_memory_storage(page)
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#repeatType')).to_have_value('weekly-days')
    expect(page.locator('.repeat-weekday-input:checked')).to_have_count(0)
    assert unload_is_guarded(page)
    assert get_task_records(page) == before
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    saved = [task for task in get_task_records(page) if task['name'] == 'Quota weekday raw selection draft']
    assert len(saved) == 1 and saved[0]['repeatWeekdays'] == [1, 3, 5]
    assert not unload_is_guarded(page)
    print('Quota weekday raw recovery: all-unchecked selection survives; explicit save retains the existing default weekday policy')


def run(browser_name: str, case: str) -> None:
    with local_server() as url, sync_playwright() as playwright:
        options = browser_launch_options() if browser_name == 'chromium' else {'headless': True}
        browser = getattr(playwright, browser_name).launch(**options)
        context = browser.new_context(reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            print(f'Task draft regression: {browser_name} {browser.version}')
            if case == 'quota':
                check_quota_recovery(page, url)
                return
            if case == 'weekdays':
                check_weekday_recovery(page)
                return
            check_close_paths(page)
            check_single_field_changes(page)
            check_edit_and_stale(page, url)
            check_failed_save(page)
            check_delayed_save(page)
            check_quota_recovery(page, url)
            check_weekday_recovery(page)
            check_native_beforeunload(page)
            assert not errors, errors
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'quota', 'weekdays'), default='all')
    arguments = parser.parse_args()
    run(arguments.browser, arguments.case)
