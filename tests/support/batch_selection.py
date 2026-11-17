"""Shared batch selection fixtures and assertions; no test entry point."""
from __future__ import annotations

def transaction_state(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const revision = tx.objectStore('config').get('taskRevision');
            const history = tx.objectStore('config').get('recoveryHistory');
            tx.oncomplete = () => {
                db.close();
                resolve({tasks:tasks.result, revision:revision.result, history:history.result});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")
