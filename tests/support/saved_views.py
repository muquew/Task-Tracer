"""Reusable saved views interactions and controlled browser fault fixtures."""
from __future__ import annotations
from tests.support.browser import return_to_task_workspace
from playwright.sync_api import expect

def stored_views(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction('config');
            const request = tx.objectStore('config').get('savedViews');
            tx.oncomplete = () => { db.close(); resolve(request.result?.value || []); };
            tx.onabort = () => reject(tx.error);
        };
    })""")

def start_save(page, name, query):
    return_to_task_workspace(page)
    page.locator('#searchInput').fill(query)
    page.locator('#saveSmartViewBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#savedViewNameInput').fill(name)

def save_view(page, name, query):
    start_save(page, name, query)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#savedViewsList .saved-view-name').filter(has_text=name)).to_have_count(1)

def inject_aborted_save(page):
    page.evaluate("""() => {
        const put = IDBObjectStore.prototype.put;
        window.abortNextSavedViewWrite = true;
        IDBObjectStore.prototype.put = function(value, ...args) {
            const result = put.call(this, value, ...args);
            if (this.name === 'config' && value?.key === 'savedViews' && window.abortNextSavedViewWrite) {
                window.abortNextSavedViewWrite = false;
                this.transaction.abort();
            }
            return result;
        };
    }""")
