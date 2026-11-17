"""Shared imported text edit fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.browser import open_settings, return_to_task_workspace
from copy import deepcopy
import json
from playwright.sync_api import expect
from tests.support.browser import click_task_action
from tests.support.browser import (
    assert_backup_payload_integrity,
    clear_app_data,
    get_task_records,
    stable_fnv1a32,
    stable_json,
    wait_for_app_ready,
)

def download_tasks(page):
    open_settings(page)
    with page.expect_download() as info:
        page.locator('#backupBtn').click()
    payload = json.loads(info.value.path().read_bytes())
    assert_backup_payload_integrity(payload, 'backup')
    return payload

def import_fixture(page, url, template, overrides):
    clear_app_data(page, url)
    payload = deepcopy(template)
    payload['tasks'][0].update(overrides)
    payload.pop('checksum')
    payload['checksum'] = f'fnv1a32:{stable_fnv1a32(stable_json(payload))}'
    open_settings(page)
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'valid-imported-text.json', 'mimeType': 'application/json',
                            'buffer': json.dumps(payload, ensure_ascii=False).encode()})
    expect(page.locator('[data-import-preview]')).to_have_attribute('data-checksum-status', 'valid')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    return_to_task_workspace(page)
    baseline = get_task_records(page)
    assert baseline == payload['tasks'], 'Valid import changed the text fixture before editing'
    return baseline

def open_edit(page):
    click_task_action(page.locator('.task-item'), 'edit')
    expect(page.locator('#taskModal')).to_be_visible()

def save_and_assert(page, expected):
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert get_task_records(page) == expected, 'Editing one field changed another stored task field'
    page.reload()
    wait_for_app_ready(page)
    assert get_task_records(page) == expected, 'Reload changed edited task text'
    assert download_tasks(page)['tasks'] == expected, 'Real JSON download changed edited task fields'
