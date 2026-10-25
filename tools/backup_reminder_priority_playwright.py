#!/usr/bin/env python3
"""Keep optional backup reminders from interrupting active work or replacing errors."""
from __future__ import annotations

from smoke_playwright import open_task_editor

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import add_task, browser_launch_options, clear_app_data, local_server, wait_for_app_ready
from views_portability_playwright import checksum, choose_file, open_manager, payload, snapshot, view


def hold_reminder_delivery(context):
    context.add_init_script("""(() => {
        const timeout = window.setTimeout;
        window.pendingBackupReminderDeliveries = [];
        window.setTimeout = function(callback, delay, ...args) {
            if (delay !== 900 || typeof callback !== 'function') return timeout.call(this, callback, delay, ...args);
            const timer = timeout.call(this, () => {}, delay);
            window.pendingBackupReminderDeliveries.push(() => {
                clearTimeout(timer);
                callback(...args);
            });
            return timer;
        };
        window.deliverNextBackupReminder = (holdReadCompletion = false) => new Promise((resolve, reject) => {
            const deliver = window.pendingBackupReminderDeliveries.shift();
            if (!deliver) { reject(new Error('No scheduled backup reminder')); return; }
            const transaction = IDBDatabase.prototype.transaction;
            let observed = false;
            IDBDatabase.prototype.transaction = function(stores, mode, ...args) {
                const tx = transaction.call(this, stores, mode, ...args);
                const names = typeof stores === 'string' ? [stores] : Array.from(stores);
                if (mode === 'readonly' && names.length === 2 && names.includes('tasks') && names.includes('config')) {
                    observed = true;
                    if (holdReadCompletion) {
                        const complete = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, 'oncomplete');
                        let handler;
                        Object.defineProperty(tx, 'oncomplete', {
                            configurable: true, get: () => handler,
                            set: value => {
                                handler = value;
                                complete.set.call(tx, typeof value === 'function' ? function(event) {
                                    window.finishHeldBackupStatusRead = () => value.call(tx, event);
                                } : value);
                            }
                        });
                    }
                    tx.addEventListener('complete', () => requestAnimationFrame(() => requestAnimationFrame(resolve)), {once: true});
                    tx.addEventListener('abort', () => reject(tx.error), {once: true});
                }
                return tx;
            };
            try { deliver(); } catch (error) { reject(error); }
            finally { IDBDatabase.prototype.transaction = transaction; }
            if (!observed) requestAnimationFrame(() => requestAnimationFrame(resolve));
        });
    })();""")


def reload_with_reminder(page):
    page.reload()
    wait_for_app_ready(page)
    page.wait_for_function('window.pendingBackupReminderDeliveries.length === 1')
    expect(page.locator('#notification')).not_to_have_class(re.compile(r'\bshow\b'))
    expect(page.locator('#backupHealth')).to_have_class(re.compile(r'\bbackup-due\b'))


def reject_view_file(page):
    invalid = payload([view('Invalid scope must stay rejected', '')])
    invalid['version'] = '1.1'
    invalid['checksum'] = checksum(invalid)
    open_manager(page)
    choose_file(page, invalid)
    expect(page.locator('#notification')).to_have_class('notification error show')
    language = page.locator('html').get_attribute('lang')
    translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
    error_text = translations['viewsTransfer']['invalid']
    expect(page.locator('#notificationText')).to_have_text(error_text)
    expect(page.locator('#savedViewsTransferContent')).to_be_visible()
    return error_text


def run(engine):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'Backup reminder priority {engine}: {browser.version}', flush=True)
        context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
        hold_reminder_delivery(context)
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            add_task(page, 'Synthetic task awaiting its first backup', no_deadline=True)

            reload_with_reminder(page)
            before = snapshot(page)
            error_text = reject_view_file(page)
            page.evaluate('window.deliverNextBackupReminder()')
            print('Reminder after invalid file with modal: ' + json.dumps({
                'class': page.locator('#notification').get_attribute('class'),
                'text': page.locator('#notificationText').text_content()}, ensure_ascii=False), flush=True)
            expect(page.locator('#notification')).to_have_class('notification error show')
            expect(page.locator('#notificationText')).to_have_text(error_text)
            expect(page.locator('#savedViewsTransferContent')).to_be_visible()
            assert snapshot(page) == before, 'Rejected view file or reminder changed workspace data'
            expect(page.locator('#cancelBtn')).to_be_hidden()
            page.locator('#submitBtn').click()
            print('Backup reminder passed: invalid-file error and active transfer dialog stay intact without writes', flush=True)

            reload_with_reminder(page)
            before = snapshot(page)
            open_task_editor(page)
            page.evaluate('window.deliverNextBackupReminder()')
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#notification')).not_to_have_class(re.compile(r'\bshow\b'))
            assert snapshot(page) == before, 'Reminder interrupted a task form or changed workspace data'
            page.locator('#cancelBtn').click()
            print('Backup reminder passed: active task form suppresses the optional reminder', flush=True)

            reload_with_reminder(page)
            before = snapshot(page)
            error_text = reject_view_file(page)
            expect(page.locator('#cancelBtn')).to_be_hidden()
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            page.evaluate('window.deliverNextBackupReminder()')
            expect(page.locator('#notification')).to_have_class('notification error show')
            expect(page.locator('#notificationText')).to_have_text(error_text)
            assert snapshot(page) == before, 'Reminder changed data while an error notification was active'
            print('Backup reminder passed: visible error remains unchanged after the dialog closes', flush=True)

            for operation in ('task-form', 'invalid-file-error'):
                reload_with_reminder(page)
                before = snapshot(page)
                page.evaluate('window.deliverNextBackupReminder(true)')
                page.wait_for_function('typeof window.finishHeldBackupStatusRead === "function"')
                if operation == 'task-form':
                    open_task_editor(page)
                    page.locator('#taskName').fill('New task draft started during backup status read')
                else:
                    error_text = reject_view_file(page)
                    expect(page.locator('#cancelBtn')).to_be_hidden()
                    page.locator('#submitBtn').click()
                    expect(page.locator('#taskModal')).to_be_hidden()
                page.evaluate("""() => {
                    window.finishHeldBackupStatusRead();
                    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                }""")
                if operation == 'task-form':
                    expect(page.locator('#taskModal')).to_be_visible()
                    expect(page.locator('#taskName')).to_have_value('New task draft started during backup status read')
                    expect(page.locator('#notification')).not_to_have_class(re.compile(r'\bshow\b'))
                else:
                    expect(page.locator('#notification')).to_have_class('notification error show')
                    expect(page.locator('#notificationText')).to_have_text(error_text)
                assert snapshot(page) == before, 'Operation during reminder status read changed workspace data'
                if operation == 'task-form':
                    page.locator('#cancelBtn').click()
                    page.locator('#draftDiscardBtn').click()
                print(f'Backup reminder passed: {operation} started during the real status read remains intact', flush=True)

            reload_with_reminder(page)
            before = snapshot(page)
            page.evaluate('window.deliverNextBackupReminder()')
            language = page.locator('html').get_attribute('lang')
            translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
            expect(page.locator('#notification')).to_have_class('notification warning show')
            expect(page.locator('#notificationText')).to_have_text(translations['messages']['backup']['reminder'])
            expect(page.locator('#backupHealth')).to_have_class(re.compile(r'\bbackup-due\b'))
            assert snapshot(page) == before, 'Idle backup reminder changed workspace data'
            assert not errors, errors
            print('Backup reminder passed: idle page still shows the due reminder and keeps backup menu status', flush=True)
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
