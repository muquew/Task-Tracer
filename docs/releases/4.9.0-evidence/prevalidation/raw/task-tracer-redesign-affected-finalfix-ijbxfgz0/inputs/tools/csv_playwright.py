#!/usr/bin/env python3
"""Verify Unicode JSON transfer and spreadsheet downloads with isolated profiles."""
from __future__ import annotations
import argparse
import csv
import io
import json
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, assert_backup_payload_integrity, browser_launch_options, clear_app_data,
    get_task_records, local_server, stable_fnv1a32, wait_for_app_ready,
)


def backup_stamp(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
        const request = indexedDB.open('TaskTrackerDB', 2);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('config');
            const value = tx.objectStore('config').get('lastBackupAt');
            tx.oncomplete = () => { db.close(); resolve(value.result?.value ?? null); };
            tx.onabort = () => reject(tx.error);
        };
    })""")


def download_csv(page):
    page.locator('#openMenuBtn').click()
    with page.expect_download() as info:
        page.locator('#exportCsvBtn').click()
    download = info.value
    assert download.suggested_filename.endswith('.csv')
    data = download.path().read_bytes()
    assert data.startswith(b'\xef\xbb\xbf'), 'Missing Excel-compatible UTF-8 BOM'
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))), data


def assert_unicode_json_roundtrip(page, url, launcher, options, errors):
    """Restore the actual downloaded bytes, including every stored task field."""
    before = get_task_records(page)
    page.locator('#openMenuBtn').click()
    with page.expect_download() as info:
        page.locator('#backupBtn').click()
    download = info.value
    raw = download.path().read_bytes()
    payload = json.loads(raw)
    assert payload['version'] == '2.4'
    assert_backup_payload_integrity(payload, 'backup')
    assert payload['tasks'] == before, 'JSON download changed or omitted task fields'
    assert get_task_records(page) == before, 'JSON export modified source tasks'

    # Known FNV-1a values retain empty/ASCII/BMP behavior and cover a surrogate pair.
    for text, expected in [('', '811c9dc5'), ('hello', '4f9f2cab'),
                           ('中文', '5132b5ad'), ('😀', 'cb31c4b8')]:
        assert stable_fnv1a32(text) == expected, f'Incorrect FNV-1a checksum for {text!r}'

    with tempfile.TemporaryDirectory() as target_profile:
        target_context = launcher.launch_persistent_context(
            target_profile, accept_downloads=True, timeout=30000, **options)
        try:
            target = target_context.pages[0]
            target.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(target, url)
            assert get_task_records(target) == [], 'Import target is not a clean profile'
            target.locator('#openMenuBtn').click()
            with target.expect_file_chooser() as chooser:
                target.locator('#importBtn').click()
            chooser.value.set_files({'name': download.suggested_filename,
                                    'mimeType': 'application/json', 'buffer': raw})
            expect(target.locator('#mergeImportMode')).to_be_visible()
            expect(target.locator('[data-import-preview]')).to_have_attribute('data-checksum-status', 'valid')
            language = target.locator('html').get_attribute('lang')
            translations = json.loads((Path(__file__).resolve().parents[1] / 'resources' / f'{language}.json').read_text())
            expect(target.locator('.restore-checklist')).to_contain_text(
                translations['messages']['import']['restoreIntegrityOk'])
            target.locator('#submitBtn').click()
            expect(target.locator('#taskModal')).to_be_hidden()
            assert get_task_records(target) == before, 'Unicode JSON transfer changed task fields'
            target.reload()
            wait_for_app_ready(target)
            assert get_task_records(target) == before, 'Imported task fields did not survive reload'
        finally:
            target_context.close()
    assert get_task_records(page) == before, 'Import in another profile changed source tasks'


def run(engine):
    with local_server() as url, sync_playwright() as p, tempfile.TemporaryDirectory() as profile:
        launcher = getattr(p, engine)
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        context = launcher.launch_persistent_context(profile, accept_downloads=True, timeout=30000, **options)
        try:
            page = context.pages[0]
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            add_task(page, '🔬 审核 👩🏽‍💻 Café e\u0301',
                     description=('Line "quoted", commas <not-html> 👩🏽‍💻 e\u0301\n' * 40).rstrip('\n'),
                     no_deadline=True, project='研究 👩🏽‍💻', tags=['🔒', 'Café', 'e\u0301'],
                     subtasks=['👩🏽‍💻 中文子任务', 'e\u0301 "quoted"'])
            add_task(page, '📅 Scheduled 👨‍👩‍👧‍👦 e\u0301',
                     description='First line 👨‍👩‍👧‍👦\nSecond line e\u0301, "quoted"',
                     due_date='2030-06-20', due_time='15:30', reminder_offset='60',
                     repeat_type='custom', repeat_interval='3', repeat_paused=True,
                     project='计划 📅', tags=['repeat', '家人'])
            assert_unicode_json_roundtrip(page, url, launcher, options, errors)
            page.evaluate("""() => new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction('tasks', 'readwrite');
                    const store = tx.objectStore('tasks');
                    const all = store.getAll();
                    all.onsuccess = () => {
                        const base = all.result[0];
                        store.clear();
                        const names = ['=SUM(1,2)', '+formula', '-formula', '@formula', '\\t=1+1', '中文 👩🏽‍💻 é, "quoted"\\nsecond line'];
                        names.forEach((name, index) => store.put({...base, id: 100000 + index,
                            name, description: index === 0 ? 'notes "quoted", commas\\nline two' : '\\uFEFF =1+1',
                            project: index === 0 ? '=project' : '报告', tags: ['中文', 'comma,tag'],
                            archived: index === 1, archivedAt: index === 1 ? new Date().toISOString() : null,
                            completed: index === 2, completedAt: index === 2 ? new Date().toISOString() : null}));
                    };
                    tx.oncomplete = () => { db.close(); resolve(); };
                    tx.onabort = () => reject(tx.error);
                };
                request.onerror = () => reject(request.error);
            })""")
            page.reload()
            wait_for_app_ready(page)
            before = get_task_records(page)
            stamp = backup_stamp(page)
            page.locator('#searchInput').fill('No matching CSV report rows')
            expect(page.locator('.task-item')).to_have_count(0)
            rows, raw = download_csv(page)
            assert len(rows) == len(before), 'Export omitted filtered or archived records'
            by_id = {row['id']: row for row in rows}
            for task in before:
                row = by_id[str(task['id'])]
                name = task['name']
                expected = "'" + name if name[0] in '=+-@\t' else name
                assert row['name'] == expected, (row['name'], expected)
                assert json.loads(row['tags']) == task['tags']
                assert json.loads(row['subtasks']) == task['subtasks']
                if task['name'] == '=SUM(1,2)':
                    assert row['project'] == "'=project"
                    assert row['description'] == task['description']
                else:
                    assert row['description'].startswith("'"), 'Whitespace-prefixed formula was not neutralized'
            assert by_id['100001']['status'] == 'archived'
            assert by_id['100002']['status'] == 'completed'
            assert b'\r\n' in raw
            assert get_task_records(page) == before, 'CSV export modified task data'
            assert backup_stamp(page) == stamp, 'CSV was incorrectly recorded as a restorable JSON backup'
            clear_app_data(page, url)
            rows, _ = download_csv(page)
            assert rows == [], 'Empty workspace CSV must contain only headers'
            if errors: raise AssertionError(errors)
            print(f'{engine}: real Unicode JSON checksum/full-field clean-profile restore; CSV Unicode/multiline/quotes, formula neutralization, full-scope export and backup isolation passed')
        finally:
            context.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    run(parser.parse_args().browser)
