#!/usr/bin/env python3
"""Verify empty-first onboarding, explicit examples and atomic task preservation."""
from __future__ import annotations
import argparse

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, get_task_records, local_server,
    wait_for_app_ready,
)


def fresh_page(browser, url):
    context = browser.new_context(locale='en-US')
    page = context.new_page()
    page.goto(url)
    wait_for_app_ready(page)
    return context, page


def run(engine='chromium'):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        print(f'Onboarding {engine}: {browser.version}', flush=True)
        context, page = fresh_page(browser, url)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        expect(page.locator('.task-item')).to_have_count(0)
        expect(page.locator('#addExampleTasksBtn')).to_have_accessible_name('Add 3 example tasks')
        page.reload()
        wait_for_app_ready(page)
        assert get_task_records(page) == [], 'Reload populated an intentionally empty workspace'
        page.locator('#addExampleTasksBtn').evaluate('(button) => { button.click(); button.click(); }')
        expect(page.locator('.task-item')).to_have_count(3)
        records = get_task_records(page)
        assert len(records) == 3 and all(task['name'].startswith('Example: ') for task in records)
        page.reload()
        wait_for_app_ready(page)
        assert get_task_records(page) == records, 'Reload changed or duplicated examples'
        assert not errors, errors
        context.close()
        print('Onboarding passed: fresh/reloaded workspace stays empty; examples are explicit, labeled and duplicate-safe')

        context, page = fresh_page(browser, url)
        page.locator('#addExampleTasksBtn').focus()
        page.keyboard.press('Enter')
        expect(page.locator('.task-item')).to_have_count(3)
        page.locator('#undoBtn').click()
        expect(page.locator('.task-item')).to_have_count(0)
        page.reload()
        wait_for_app_ready(page)
        assert get_task_records(page) == [], 'Undo was followed by automatic reseeding'
        page.locator('#addExampleTasksBtn').click()
        expect(page.locator('.task-item')).to_have_count(3)
        context.close()
        print('Onboarding passed: example addition is undoable and an empty workspace remains empty after reload')

        context, page = fresh_page(browser, url)
        other = context.new_page()
        other.goto(url)
        wait_for_app_ready(other)
        add_task(other, 'Existing personal task', no_deadline=True)
        expected = get_task_records(other)
        page.locator('#addExampleTasksBtn').click()
        expect(page.locator('.task-item')).to_have_count(1)
        assert get_task_records(page) == expected, 'Examples changed tasks added in another window'
        page.reload()
        wait_for_app_ready(page)
        expect(page.locator('#addExampleTasksBtn')).to_have_count(0)
        assert get_task_records(page) == expected
        page.locator('#searchInput').fill('No matching example report')
        expect(page.locator('.task-item')).to_have_count(0)
        expect(page.locator('#taskList .empty-state')).to_be_visible()
        expect(page.locator('#addExampleTasksBtn')).to_have_count(0)
        assert get_task_records(page) == expected
        context.close()
        print('Onboarding passed: stale empty window preserves a task created elsewhere')

        context, page = fresh_page(browser, url)
        page.evaluate("""() => {
            const original = IDBObjectStore.prototype.add;
            let count = 0;
            IDBObjectStore.prototype.add = function(...args) {
                if (this.name === 'tasks' && ++count === 2) {
                    throw new DOMException('Synthetic examples quota failure', 'QuotaExceededError');
                }
                return original.apply(this, args);
            };
        }""")
        page.locator('#addExampleTasksBtn').click()
        expect(page.locator('#storageUnavailableBanner')).to_be_visible()
        expect(page.locator('#addExampleTasksBtn')).to_have_count(0)
        assert get_task_records(page) == [], 'Failed example addition left partially saved tasks'
        context.close()
        browser.close()
        print('Onboarding passed: quota failure rolls back all examples atomically')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
