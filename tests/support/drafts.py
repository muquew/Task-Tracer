"""Reusable drafts interactions and controlled browser fault fixtures."""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import Page

def unload_is_guarded(page: Page) -> bool:
    return page.evaluate("""() => {
        const event = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(event);
        return event.defaultPrevented;
    }""")

def hold_next_task_completion(page: Page) -> None:
    page.evaluate("""() => {
        const original = IDBDatabase.prototype.transaction;
        window.taskWriteCommitted = false;
        window.finishTaskWrite = null;
        IDBDatabase.prototype.transaction = function(names, mode, ...rest) {
            const tx = original.call(this, names, mode, ...rest);
            if (mode === 'readwrite' && Array.from(tx.objectStoreNames).includes('tasks')) {
                IDBDatabase.prototype.transaction = original;
                let handler;
                Object.defineProperty(tx, 'oncomplete', {
                    configurable: true,
                    get: () => handler,
                    set: value => { handler = value; }
                });
                tx.addEventListener('complete', event => {
                    window.taskWriteCommitted = true;
                    window.finishTaskWrite = () => {
                        window.finishTaskWrite = null;
                        handler?.call(tx, event);
                    };
                });
            }
            return tx;
        };
    }""")

def inject_quota_failure(page: Page, method: str = 'add') -> None:
    page.evaluate("""method => {
        const original = IDBObjectStore.prototype[method];
        IDBObjectStore.prototype[method] = function(...args) {
            if (this.name === 'tasks') {
                IDBObjectStore.prototype[method] = original;
                throw new DOMException('Synthetic full storage', 'QuotaExceededError');
            }
            return original.apply(this, args);
        };
    }""", method)

def downloaded_drafts(page: Page):
    with page.expect_download() as download:
        page.locator('#taskDraftRecoveryDownloadBtn').click()
    payload = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
    assert payload['app'] == 'Task Tracer' and payload['type'] == 'task-draft'
    assert 'tasks' not in payload and payload['version'] == '1.0'
    return payload['drafts']
