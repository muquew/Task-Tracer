"""Shared calendar performance fixtures and assertions; no test entry point."""
from __future__ import annotations
from playwright.sync_api import expect
from tests.support.browser import add_task, wait_for_app_ready

def seed(page, per_section):
    add_task(page, 'Calendar scale seed', no_deadline=True)
    page.evaluate("""perSection => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            const store = tx.objectStore('tasks');
            const all = store.getAll();
            all.onsuccess = () => {
                const template = all.result[0];
                store.clear();
                for (let i = 0; i < perSection; i++) {
                    for (const dated of [false, true]) {
                        const key = dated ? '2039-01-01' : null;
                        const instant = key ? key + 'T12:00:00.000Z' : null;
                        store.put({...template, id: (dated ? 200000 : 100000) + i,
                            name: `Calendar ${dated ? 'deadline' : 'inbox'} ${String(i).padStart(5, '0')} 中文`,
                            description: `Synthetic calendar entry ${i}`, project: i % 2 ? 'Odd' : 'Even',
                            tags: ['calendar-scale'], order:i * 1000,
                            dueDate:instant, dueAt:instant, dueLocalDate:key,
                            dueLocalTime:key ? '12:00' : null, dueTimeZone:key ? 'UTC' : null,
                            reminderOffset:-1, reminderRepeat:-1});
                    }
                }
                tx.objectStore('config').put({key:'recoveryHistory', value:[]});
            };
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
    })""", per_section)
    page.reload()
    wait_for_app_ready(page)

def open_day(page):
    page.locator('[data-calendar-detail-date="2039-01-01"]').click()
    expect(page.locator('.calendar-day-detail')).to_be_visible()
    expect(page.locator('.calendar-detail-close')).to_be_focused()
