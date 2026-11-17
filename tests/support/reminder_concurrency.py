"""Shared reminder concurrency fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.browser import due_fields_from_now, iso_minutes_from_now

def seed(page, name):
    task = {'id': 123456, 'name': name, 'description': 'Original description',
            **due_fields_from_now(-1), 'reminderOffset': 15, 'reminderRepeat': -1,
            'snoozedUntil': None, 'lastReminderAt': None, 'repeatType': 'none',
            'repeatInterval': 1, 'repeatWeekdays': [], 'repeatPaused': False,
            'subtasks': [], 'completed': False, 'completedAt': None,
            'archived': False, 'archivedAt': None, 'createdAt': iso_minutes_from_now(-120), 'order': 100}
    page.evaluate("""task => new Promise((resolve, reject) => {
        const open = indexedDB.open('TaskTrackerDB', 2);
        open.onsuccess = () => {
            const db = open.result;
            const tx = db.transaction(['tasks', 'config'], 'readwrite');
            tx.objectStore('tasks').put(task);
            tx.objectStore('config').put({key:'notifications_enabled',value:true});
            tx.oncomplete = () => {db.close(); resolve();};
            tx.onabort = () => reject(tx.error);
        };
        open.onerror = () => reject(open.error);
    })""", task)
