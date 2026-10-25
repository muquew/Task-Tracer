#!/usr/bin/env python3
"""Regression checks for undo isolation and concurrent task changes."""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task,
    browser_launch_options,
    clear_app_data,
    delete_task,
    discard_task_draft,
    edit_task,
    local_server,
    task_locator,
    wait_for_app_ready,
)


def read_tasks(page):
    return page.evaluate("""async () => {
        const db = await new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB');
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
        try {
            return await new Promise((resolve, reject) => {
                const request = db.transaction('tasks').objectStore('tasks').getAll();
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        } finally { db.close(); }
    }""")


def external_write(page, task):
    page.evaluate("""async task => {
        const db = await new Promise((resolve, reject) => {
            const request = indexedDB.open('TaskTrackerDB');
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
        try {
            await new Promise((resolve, reject) => {
                const transaction = db.transaction('tasks', 'readwrite');
                transaction.oncomplete = resolve;
                transaction.onabort = () => reject(transaction.error);
                transaction.objectStore('tasks').put(task);
            });
        } finally { db.close(); }
    }""", task)


def check_undo(url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        context = browser.new_context()
        page = context.new_page()
        clear_app_data(page, url)

        add_task(page, 'Undo isolated task', no_deadline=True)
        source = next(task for task in read_tasks(page) if task['name'] == 'Undo isolated task')
        external = {**source, 'id': source['id'] + 1, 'name': 'Unrelated external task'}
        external_write(page, external)
        page.locator('#undoBtn').click()
        expect(task_locator(page, 'Undo isolated task')).to_have_count(0)
        expect(task_locator(page, 'Unrelated external task')).to_have_count(1)
        assert [task['name'] for task in read_tasks(page)] == ['Unrelated external task']
        print('Undo preserves unrelated records written by another database client')

        add_task(page, 'Task with newer change', no_deadline=True)
        touched = next(task for task in read_tasks(page) if task['name'] == 'Task with newer change')
        external_write(page, {**touched, 'name': 'Newer external value'})
        page.locator('#undoBtn').click()
        expect(task_locator(page, 'Newer external value')).to_have_count(1)
        persisted = read_tasks(page)
        assert any(task['name'] == 'Newer external value' for task in persisted), persisted
        assert any(task['name'] == 'Unrelated external task' for task in persisted), persisted
        print('Undo refuses to overwrite a newer value on the same task')

        page.reload()
        wait_for_app_ready(page)
        add_task(page, 'Before tab change', no_deadline=True)
        other = context.new_page()
        other.goto(url)
        wait_for_app_ready(other)
        add_task(other, 'Other tab task', no_deadline=True)
        page.locator('#undoBtn').click()
        expect(task_locator(page, 'Other tab task')).to_have_count(1)
        persisted = read_tasks(page)
        assert any(task['name'] == 'Other tab task' for task in persisted), persisted
        assert any(task['name'] == 'Before tab change' for task in persisted), persisted
        print('Undo refuses a stale revision after a second app tab changes tasks')
        context.close()
        browser.close()


def check_stale_form(url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        for remote_action in ('edit', 'delete'):
            context = browser.new_context()
            page = context.new_page()
            clear_app_data(page, url)
            original_name = f'Concurrent {remote_action} original'
            draft_name = f'Unsaved local {remote_action} draft'
            add_task(page, original_name, no_deadline=True)
            other = context.new_page()
            other.goto(url)
            wait_for_app_ready(other)
            click_task_action(task_locator(page, original_name), 'edit')
            expect(page.locator('#taskModal')).to_be_visible()
            page.locator('#taskName').fill(draft_name)
            page.locator('#taskDesc').fill('Keep this unsaved local description')

            remote_name = f'Concurrent {remote_action} remote value'
            if remote_action == 'edit':
                edit_task(other, original_name, remote_name)
            else:
                delete_task(other, original_name)
            expected_tasks = read_tasks(other)
            language = page.locator('html').get_attribute('lang') or 'en'
            translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())

            page.locator('#submitBtn').click()
            expect(page.locator('#notificationText')).to_have_text(translations['storage']['conflict'])
            if remote_action == 'edit':
                expect(task_locator(page, remote_name)).to_have_count(1)
            else:
                expect(task_locator(page, original_name)).to_have_count(0)
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#taskName')).to_have_value(draft_name)
            expect(page.locator('#taskDesc')).to_have_value('Keep this unsaved local description')
            assert read_tasks(page) == expected_tasks

            page.locator('#submitBtn').click()
            expect(page.locator('#notificationText')).to_have_text(translations['storage']['editConflict'])
            expect(page.locator('#taskModal')).to_be_visible()
            expect(page.locator('#taskName')).to_have_value(draft_name)
            expect(page.locator('#taskDesc')).to_have_value('Keep this unsaved local description')
            assert read_tasks(page) == expected_tasks
            page.locator('#cancelBtn').click()
            discard_task_draft(page)
            expect(page.locator('#taskModal')).to_be_hidden()
            if remote_action == 'edit':
                edit_task(page, remote_name, 'Reviewed latest task')
                assert any(task['name'] == 'Reviewed latest task' for task in read_tasks(page))
            else:
                assert all(task['name'] != original_name for task in read_tasks(page))
            print(f'Stale {remote_action} form refuses two saves, preserves draft and remote data')
            context.close()
        browser.close()


def main() -> None:
    url = os.environ.get('TASK_TRACER_URL')
    if url:
        check_undo(url)
        check_stale_form(url)
    else:
        with local_server() as local_url:
            check_undo(local_url)
            check_stale_form(local_url)
    print('Undo concurrency checks passed')


if __name__ == '__main__':
    main()
