"""Shared import reference fixtures and assertions; no test entry point."""
from __future__ import annotations
from playwright.sync_api import expect
from tests.support.browser import select_filter

def finish_occurrence(page, task_id):
    select_filter(page, 'all')
    button = page.locator(f'.task-item[data-task-id="{task_id}"] [data-action="toggle"]')
    expect(button).to_be_enabled()
    button.click()
    page.wait_for_function("""id => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction('tasks');
            const task = tx.objectStore('tasks').get(id);
            tx.oncomplete = () => { db.close(); resolve(task.result?.completed === true); };
            tx.onabort = () => reject(tx.error);
        };
    })""", arg=task_id)
    expect(page.locator(f'.task-item[data-task-id="{task_id}"] [data-action="toggle"]')).to_be_enabled()
