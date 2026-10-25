#!/usr/bin/env python3
"""Exercise stale-tab saved-view mutations and an aborted configuration write."""
from __future__ import annotations

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import reveal_workspace_control
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, get_task_records, local_server,
    wait_for_app_ready,
)


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


def names(page):
    return {view['name'] for view in stored_views(page)}


def start_save(page, name, query):
    page.locator('#searchInput').fill(query)
    page.locator('#saveSmartViewBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#savedViewNameInput').fill(name)


def save_view(page, name, query):
    start_save(page, name, query)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#savedViewsList .saved-view-name').filter(has_text=name)).to_have_count(1)


def delete_view(page, name):
    chip = page.locator('#savedViewsList .saved-view-chip').filter(
        has=page.locator('.saved-view-name', has_text=name))
    reveal_workspace_control(page, chip.locator('.saved-view-delete')).click()
    expect(page.locator('#savedViewDeleteName')).to_have_text(name)
    page.locator('#submitBtn').click()
    expect(chip).to_have_count(0)


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



def seed_views(page, count):
    views = [{'id': f'capacity-{index}', 'name': f'Capacity view {index}',
              'searchQuery': f'project:capacity-{index}', 'filter': 'active',
              'projectFilter': 'all', 'sort': 'smart', 'viewMode': 'list'}
             for index in range(count)]
    page.evaluate("""views => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction('config', 'readwrite');
            tx.objectStore('config').put({key: 'savedViews', value: views});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", views)
    page.reload()
    wait_for_app_ready(page)
    return views


def assert_capacity_preserves_existing(first, second, task_records):
    before = seed_views(first, 12)
    start_save(first, 'Rejected thirteenth view draft', 'project:capacity-overflow')
    first.locator('#submitBtn').click()
    actual = stored_views(first)
    assert actual == before, 'A thirteenth view silently evicted an existing view'
    expect(first.locator('#taskModal')).to_be_visible()
    expect(first.locator('#savedViewNameInput')).to_have_value('Rejected thirteenth view draft')
    expect(first.locator('#submitBtn')).to_be_enabled()
    expect(first.locator('#notificationText')).to_contain_text('12')
    assert stored_views(first) == before, 'A thirteenth view silently evicted an existing view'
    first.locator('#cancelBtn').click()
    target = before[5]
    save_view(first, 'Renamed existing at capacity', target['searchQuery'])
    renamed = stored_views(first)
    assert len(renamed) == 12
    assert renamed[5] == {**target, 'name': 'Renamed existing at capacity', 'projectFilter': {'kind': 'all'}}
    assert renamed[:5] + renamed[6:] == before[:5] + before[6:], 'Renaming one view changed unrelated views'
    inject_aborted_save(first)
    start_save(first, 'Uncommitted capacity rename draft', target['searchQuery'])
    first.locator('#submitBtn').click()
    first.wait_for_function('window.abortNextSavedViewWrite === false')
    expect(first.locator('#savedViewNameInput')).to_have_value('Uncommitted capacity rename draft')
    expect(first.locator('#submitBtn')).to_be_enabled()
    assert stored_views(first) == renamed, 'Aborted rename changed saved views at capacity'
    first.locator('#cancelBtn').click()
    print('Saved views passed: capacity rejects new snapshots without eviction; rename preserves identity/order and rollback retains draft', flush=True)

    seed_views(first, 11)
    second.reload()
    wait_for_app_ready(second)
    save_view(first, 'Last slot winner', 'project:capacity-winner')
    winner = stored_views(first)
    start_save(second, 'Stale window pending draft', 'project:capacity-second')
    second.locator('#submitBtn').click()
    expect(second.locator('#taskModal')).to_be_visible()
    expect(second.locator('#savedViewNameInput')).to_have_value('Stale window pending draft')
    expect(second.locator('#submitBtn')).to_be_enabled()
    expect(second.locator('#notificationText')).to_contain_text('12')
    assert stored_views(second) == winner, 'A stale window evicted the last-slot winner'
    delete_view(first, 'Capacity view 0')
    second.locator('#submitBtn').click()
    expect(second.locator('#taskModal')).to_be_hidden()
    final = stored_views(second)
    assert len(final) == 12
    expected = [view for view in winner if view['name'] != 'Capacity view 0']
    assert final[1:] == expected, 'Retry after freeing capacity changed unrelated saved views'
    assert final[0]['name'] == 'Stale window pending draft' and final[0]['searchQuery'] == 'project:capacity-second'
    assert get_task_records(first) == task_records, 'Capacity or rename operations changed task records'
    print('Saved views passed: two stale windows compete safely for the twelfth slot, and retained draft saves after another window frees capacity', flush=True)



def assert_late_confirmation_preserves_draft(page, task_records):
    page.evaluate("""() => {
        window.holdNextSavedViewCompletion = true;
        const transaction = IDBDatabase.prototype.transaction;
        const complete = Object.getOwnPropertyDescriptor(IDBTransaction.prototype, 'oncomplete');
        IDBDatabase.prototype.transaction = function(stores, mode, ...args) {
            const tx = transaction.call(this, stores, mode, ...args);
            const names = typeof stores === 'string' ? [stores] : Array.from(stores);
            if (mode === 'readwrite' && names.length === 1 && names[0] === 'config' && window.holdNextSavedViewCompletion) {
                let handler;
                Object.defineProperty(tx, 'oncomplete', {
                    configurable: true, get: () => handler,
                    set: value => {
                        handler = value;
                        complete.set.call(tx, typeof value === 'function' ? function(event) {
                            if (window.holdNextSavedViewCompletion) {
                                window.holdNextSavedViewCompletion = false;
                                window.finishHeldSavedViewCompletion = () => value.call(tx, event);
                            } else value.call(tx, event);
                        } : value);
                    }
                });
            }
            return tx;
        };
    }""")
    start_save(page, 'Saved view completing after cancellation', 'project:late-confirmation')
    page.locator('#submitBtn').click()
    page.wait_for_function('typeof window.finishHeldSavedViewCompletion === "function"')
    page.locator('#cancelBtn').click()
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Unsubmitted task after canceled view save')
    page.locator('#taskDesc').fill('A newer task draft must survive the older completion')
    page.evaluate('window.finishHeldSavedViewCompletion()')
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#taskName')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value('Unsubmitted task after canceled view save')
    expect(page.locator('#taskDesc')).to_have_value('A newer task draft must survive the older completion')
    assert get_task_records(page) == task_records, 'Delayed saved-view confirmation changed task records'
    assert 'Saved view completing after cancellation' in names(page), 'The completed saved-view transaction was lost'
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    print('Saved views passed: an older confirmation completion cannot close or clear a newer task draft', flush=True)


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        try:
            context = browser.new_context()
            first = context.new_page()
            clear_app_data(first, url)
            add_task(first, 'Saved view task invariant', no_deadline=True)
            task_records = get_task_records(first)
            second = context.new_page()
            second.goto(url)
            wait_for_app_ready(second)
            save_view(first, 'Window Alpha', 'project:alpha')
            save_view(second, 'Window Beta', 'project:beta')
            assert names(second) == {'Window Alpha', 'Window Beta'}, 'A stale tab lost a saved view created in another window'
            delete_view(first, 'Window Alpha')
            assert names(first) == {'Window Beta'}, 'A stale deletion discarded an unrelated newer saved view'
            save_view(first, 'Window Gamma', 'project:gamma')
            save_view(second, 'Window Delta', 'project:delta')
            assert names(second) == {'Window Beta', 'Window Gamma', 'Window Delta'}, 'A stale save resurrected a deleted view or lost a new one'
            print('Saved views passed: stale saves/deletions preserve unrelated changes without resurrection', flush=True)

            before = stored_views(first)
            inject_aborted_save(first)
            start_save(first, 'Uncommitted View', 'project:aborted')
            first.locator('#submitBtn').click()
            first.wait_for_function('window.abortNextSavedViewWrite === false')
            expect(first.locator('#submitBtn')).to_be_enabled()
            expect(first.locator('#taskModal')).to_be_visible()
            expect(first.locator('#savedViewNameInput')).to_have_value('Uncommitted View')
            assert stored_views(first) == before, 'Aborted view write modified persisted configuration'
            first.locator('#cancelBtn').click()
            save_view(first, 'Committed After Failure', 'project:after-failure')
            assert names(first) == {view['name'] for view in before} | {'Committed After Failure'}, 'An aborted saved view leaked into a later successful write'
            first.reload()
            wait_for_app_ready(first)
            assert 'Uncommitted View' not in names(first)
            assert get_task_records(first) == task_records, 'Saved-view operations changed tasks'
            print('Saved views passed: aborted save retains draft and cannot leak phantom state after retry/reload', flush=True)
            assert_late_confirmation_preserves_draft(first, task_records)
            assert_capacity_preserves_existing(first, second, task_records)
            context.close()
        finally:
            browser.close()


if __name__ == '__main__':
    run()
