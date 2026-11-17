"""Shared views portability fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.browser import open_settings
import json
from playwright.sync_api import expect
from tests.support.browser import wait_for_app_ready

def checksum(payload):
    source = {key: value for key, value in payload.items() if key != 'checksum'}
    text = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    encoded = text.encode('utf-16-le', errors='surrogatepass')
    value = 2166136261
    for index in range(0, len(encoded), 2):
        value ^= encoded[index] | (encoded[index + 1] << 8)
        value = value * 16777619 & 0xffffffff
    return f'fnv1a32:{value:08x}'

def view(name, query, identity='external-view'):
    return {'id': identity, 'name': name, 'searchQuery': query, 'filter': 'active',
            'projectFilter': 'all', 'sort': 'smart', 'viewMode': 'list'}

def payload(views):
    result = {'app': 'Task Tracer', 'type': 'saved-views', 'version': '1.0',
              'date': '2026-10-23T00:00:00.000Z', 'savedViews': views}
    result['checksum'] = checksum(result)
    return result

def snapshot(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction(['tasks', 'config']);
            const tasks = tx.objectStore('tasks').getAll();
            const settings = tx.objectStore('config').getAll();
            tx.oncomplete = () => {
                db.close();
                resolve({tasks: tasks.result, config: settings.result,
                    local: {...localStorage}, session: {...sessionStorage}});
            };
            tx.onabort = () => reject(tx.error);
        };
    })""")

def seed_views(page, views):
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

def open_manager(page):
    if page.locator('#taskModal').is_visible():
        page.keyboard.press('Escape')
        expect(page.locator('#taskModal')).to_be_hidden()
    open_settings(page)
    page.locator('#savedViewsTransferBtn').click()
    expect(page.locator('#savedViewsTransferContent')).to_be_visible()

def choose_file(page, data, filename='saved-views.json'):
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
    with page.expect_file_chooser() as info:
        page.locator('#savedViewsImportBtn').click()
    info.value.set_files({'name': filename, 'mimeType': 'application/json', 'buffer': raw})

def preview(page, data):
    open_manager(page)
    choose_file(page, data)
    expect(page.locator('#savedViewsImportPreview')).to_be_visible()

def export_views(page):
    open_manager(page)
    with page.expect_download() as result:
        page.locator('#savedViewsExportBtn').click()
    download = result.value
    assert download.suggested_filename.startswith('task-tracer-saved-views-')
    data = json.loads(download.path().read_text())
    assert set(data) == {'app', 'type', 'version', 'date', 'savedViews', 'checksum'}
    assert data['app'] == 'Task Tracer' and data['type'] == 'saved-views' and data['version'] == '1.1'
    assert data['checksum'] == checksum(data), 'View export checksum does not match actual bytes'
    return data
