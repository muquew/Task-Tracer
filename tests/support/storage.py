"""Read-only task/configuration snapshots for browser assertions."""

def stored(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const config = tx.objectStore('config').getAll();
            tx.oncomplete = () => {db.close(); resolve({tasks:tasks.result, config:config.result});};
            tx.onabort = () => reject(tx.error);
        };
    })""")

def config(snapshot):
    return {entry['key']: entry['value'] for entry in snapshot['config']}

read_workspace = stored
