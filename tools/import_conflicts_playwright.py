#!/usr/bin/env python3
"""Verify lazy conflict review and explicit bulk actions across unrendered rows."""
from __future__ import annotations

from smoke_playwright import open_settings, return_to_task_workspace

import json

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    browser_launch_options, clear_app_data, get_task_records,
    import_payload_replace, local_server,
)


def run():
    with local_server() as url, sync_playwright() as p:
        browser = p.chromium.launch(**browser_launch_options())
        context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            existing = [{'id': 1000 + index, 'name': f'Conflict task {index:03d}',
                         'description': f'Original description {index}'} for index in range(250)]
            import_payload_replace(page, existing)
            before = get_task_records(page)
            incoming = [{'id': 1000 + index, 'name': f'Conflict task {index:03d}',
                         'description': f'Incoming description {index}'} for index in range(250)]
            incoming.append({'id': 2000, 'name': 'Distinct incoming task', 'description': 'Must be added'})
            open_settings(page)
            with page.expect_file_chooser() as chooser:
                page.locator('#importBtn').click()
            chooser.value.set_files({'name': 'synthetic-conflicts.json', 'mimeType': 'application/json',
                                     'buffer': json.dumps(incoming).encode()})
            expect(page.locator('#mergeImportMode')).to_be_visible()
            expect(page.locator('.import-conflict-select')).to_have_count(0)
            expect(page.locator('[data-import-conflict-section] .custom-select')).to_have_count(0)
            page.locator('#mergeImportMode').check()
            expect(page.locator('.import-conflict-select')).to_have_count(100)
            page.locator('#cancelBtn').click()
            open_settings(page)
            with page.expect_file_chooser() as chooser:
                page.locator('#importBtn').click()
            chooser.value.set_files({'name': 'synthetic-conflicts.json', 'mimeType': 'application/json',
                                     'buffer': json.dumps(incoming).encode()})
            expect(page.locator('#mergeImportMode')).to_be_visible()
            expect(page.locator('#mergeImportMode')).not_to_be_checked()
            expect(page.locator('.import-conflict-select')).to_have_count(0)
            assert get_task_records(page) == before
            page.locator('#mergeImportMode').check()
            expect(page.locator('.import-conflict-select')).to_have_count(100)
            expect(page.locator('#importConflictSummary')).to_contain_text('250')
            page.locator('[data-import-conflict-index="0"]').select_option('replace')
            page.locator('#importConflictDefaultAction').select_option('skip')
            expect(page.locator('[data-import-conflict-index="0"]')).to_have_value('skip')
            page.locator('[data-import-conflict-index="0"]').select_option('replace')
            page.locator('[data-import-conflict-index="42"]').select_option('keep')
            page.locator('#importConflictMoreBtn').click()
            expect(page.locator('.import-conflict-select')).to_have_count(200)
            expect(page.locator('[data-import-conflict-index="0"]')).to_have_value('replace')
            expect(page.locator('[data-import-conflict-index="42"]')).to_have_value('keep')
            expect(page.locator('[data-import-conflict-index="199"]')).to_have_value('skip')
            expect(page.locator('#import-conflict-100-custom-button')).to_be_focused()
            expect(page.locator('[data-import-conflict-index="220"]')).to_have_count(0)
            page.locator('#mergeImportMode').uncheck()
            page.locator('#mergeImportMode').check()
            expect(page.locator('.import-conflict-select')).to_have_count(200)
            expect(page.locator('[data-import-conflict-index="0"]')).to_have_value('replace')
            expect(page.locator('[data-import-conflict-index="42"]')).to_have_value('keep')
            expect(page.locator('#importConflictDefaultAction')).to_have_value('skip')
            page.locator('#importConflictDefaultAction').select_option('replace')
            expect(page.locator('[data-import-conflict-index="42"]')).to_have_value('replace')
            page.locator('#importConflictDefaultAction').select_option('skip')
            page.locator('[data-import-conflict-index="0"]').select_option('replace')
            page.locator('[data-import-conflict-index="42"]').select_option('keep')
            page.locator('#submitBtn').click()
            expect(page.locator('#taskModal')).to_be_hidden()
            records = get_task_records(page)
            assert len(records) == 252, 'Bulk default did not apply to all hidden conflicts'
            by_name = {}
            for task in records:
                by_name.setdefault(task['name'], []).append(task)
            assert [task['description'] for task in by_name['Conflict task 000']] == ['Incoming description 0']
            assert {task['description'] for task in by_name['Conflict task 042']} == {'Original description 42', 'Incoming description 42'}
            assert by_name['Distinct incoming task'][0]['description'] == 'Must be added'
            for original in before:
                if original['name'] == 'Conflict task 000':
                    assert all(task['id'] != original['id'] for task in records)
                else:
                    assert original in by_name[original['name']], f'An unrelated original task changed: {original["id"]}'
            assert [task['description'] for task in by_name['Conflict task 220']] == ['Original description 220']
            assert not errors, errors
            print('Import conflicts passed: lazy/paged controls, persistent choices, bulk reset and hidden-row defaults preserve actual tasks')
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    run()
