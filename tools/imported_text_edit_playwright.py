#!/usr/bin/env python3
"""Keep accepted imported text intact when editing another task field."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json

from playwright.sync_api import expect, sync_playwright

from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task, assert_backup_payload_integrity, browser_launch_options, clear_app_data,
    get_task_records, local_server, stable_fnv1a32, stable_json, wait_for_app_ready,
)
from task_draft_playwright import downloaded_drafts, inject_quota_failure


def download_tasks(page):
    page.locator('#openMenuBtn').click()
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
    page.locator('#openMenuBtn').click()
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'valid-imported-text.json', 'mimeType': 'application/json',
                            'buffer': json.dumps(payload, ensure_ascii=False).encode()})
    expect(page.locator('[data-import-preview]')).to_have_attribute('data-checksum-status', 'valid')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
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


def text_fixture():
    return {
        'name': 'Imported\nmultiline\r\nname 👩🏽‍💻 e\u0301',
        'description': '  Imported indentation\r\nSecond line e\u0301\r\n\r\n',
        'project': 'Original project',
        'tags': ['client,private', 'team,,internal', '普通标签 👩🏽‍💻'],
        'subtasks': [{'id': 8201, 'text': 'Imported\nmultiline child 👩🏽‍💻', 'completed': True}],
    }


def long_text(page, url, template):
    baseline = import_fixture(page, url, template, {
        'name': 'Long imported name 👩🏽‍💻 ' + '名称e\u0301' * 1200,
        'description': ('Line 👩🏽‍💻 e\u0301\n' * 900).rstrip('\n'),
        'project': '长项目' + '项目' * 1200,
        'tags': ['长标签' + 'tag' * 1200, 'plain'],
        'subtasks': [{'id': 8201, 'text': '长子任务' + '项目👩🏽‍💻' * 1200, 'completed': True}],
    })
    open_edit(page)
    description = 'Only the description was intentionally edited.'
    page.locator('#taskDesc').fill(description)
    save_and_assert(page, [{**baseline[0], 'description': description}])


def comma_tags(page, url, template):
    baseline = import_fixture(page, url, template, {
        'tags': ['client,private', 'team,,internal', '普通标签 👩🏽‍💻'],
    })
    open_edit(page)
    description = 'Only the description was intentionally edited.'
    page.locator('#taskDesc').fill(description)
    save_and_assert(page, [{**baseline[0], 'description': description}])


def quoted_tags(page, url, template):
    baseline = import_fixture(page, url, template, {
        'tags': ['client,private', 'team "private", dev', 'ordinary "quote"', 'Review'],
    })
    open_edit(page)
    presented = page.locator('#taskTags').input_value()
    page.locator('#taskTags').fill(presented.replace('Review', 'Approved'))
    expected = [{**baseline[0], 'tags': [*baseline[0]['tags'][:-1], 'Approved']}]
    save_and_assert(page, expected)
    open_edit(page)
    presented = page.locator('#taskTags').input_value()
    page.locator('#taskTags').fill(presented + ', "new,tag", "new ""quote"""')
    expected = [{**expected[0], 'tags': [*expected[0]['tags'], 'new,tag', 'new "quote"']}]
    save_and_assert(page, expected)
    open_edit(page)
    presented = page.locator('#taskTags').input_value()
    assert 'team ""private"", dev' in presented
    page.locator('#taskTags').fill(presented.replace('team ""private"", dev', 'team ""revised"", dev'))
    expected = [{**expected[0], 'tags': [tag.replace('team "private", dev', 'team "revised", dev')
                                       for tag in expected[0]['tags']]}]
    save_and_assert(page, expected)
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('New quoted tags')
    page.locator('#taskTags').fill('literal"quote, "comma,tag", "escaped ""quote""", "unfinished')
    page.locator('#noDeadline').check()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    current = get_task_records(page)
    assert len(current) == 2 and expected[0] in current
    created = next(task for task in current if task['id'] != expected[0]['id'])
    assert created['tags'] == ['literal"quote', 'comma,tag', 'escaped "quote"', '"unfinished'], \
        'Quoted or literal quote tag input changed content'
    assert download_tasks(page)['tasks'] == current


def formatting(page, url, template):
    baseline = import_fixture(page, url, template, text_fixture())
    open_edit(page)
    # HTML single-line inputs and textareas normalize these imported line breaks.
    assert page.locator('#taskName').input_value() != baseline[0]['name']
    assert page.locator('#taskDesc').input_value() != baseline[0]['description']
    page.locator('#taskProject').fill('Changed project')
    expected = [{**baseline[0], 'project': 'Changed project'}]
    save_and_assert(page, expected)
    open_edit(page)
    page.locator('#taskName').fill('Renamed after import')
    save_and_assert(page, [{**expected[0], 'name': 'Renamed after import'}])


def normalization(page, url, template):
    baseline = import_fixture(page, url, template, text_fixture())
    inputs = {'#taskName': '  Explicit name 👩🏽‍💻  ',
              '#taskDesc': '  Edited\n description  \n',
              '#taskProject': '  Edited  Project  ',
              '#taskTags': ' #new , New , alpha,beta , , #last '}
    fields = {'name': 'Explicit name 👩🏽‍💻', 'description': 'Edited\n description',
              'project': 'Edited Project', 'tags': ['new', 'alpha', 'beta', 'last']}
    open_edit(page)
    for selector, value in inputs.items():
        page.locator(selector).fill(value)
    expected = [{**baseline[0], **fields}]
    save_and_assert(page, expected)
    page.locator('#openModalBtn').click()
    for selector, value in inputs.items():
        page.locator(selector).fill(value.replace('Explicit name', 'New name'))
    page.locator('#noDeadline').check()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    current = get_task_records(page)
    assert len(current) == 2 and expected[0] in current
    created = next(task for task in current if task['id'] != expected[0]['id'])
    assert {key: created[key] for key in fields} == {**fields, 'name': 'New name 👩🏽‍💻'}, \
        'New task text bypassed existing normalization'
    assert download_tasks(page)['tasks'] == current


def recovery(page, url, template):
    baseline = import_fixture(page, url, template, text_fixture())
    page.evaluate('window.importedTextOriginalDocument = true')
    open_edit(page)
    page.locator('#taskProject').fill('Recovered project')
    inject_quota_failure(page, 'put')
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert get_task_records(page) == baseline, 'Failed save committed part of the edit'
    drafts = downloaded_drafts(page)
    assert len(drafts) == 1
    assert json.loads(drafts[0]['editingTaskSnapshot']) == baseline[0]
    assert json.loads(drafts[0]['baseline'])['values']['tags'] == '"client,private", "team,,internal", 普通标签 👩🏽‍💻'
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    assert page.evaluate('window.importedTextOriginalDocument === true'), 'Retry discarded the document'
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    expect(page.locator('#taskProject')).to_have_value('Recovered project')
    save_and_assert(page, [{**baseline[0], 'project': 'Recovered project'}])


def stale_edit(page, url, template):
    baseline = import_fixture(page, url, template, text_fixture())
    open_edit(page)
    page.locator('#taskDesc').fill('Local draft must not overwrite a remote edit')
    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        open_edit(other)
        other.locator('#taskProject').fill('Newer remote project')
        other.locator('#submitBtn').click()
        expect(other.locator('#taskModal')).to_be_hidden()
        remote = [{**baseline[0], 'project': 'Newer remote project'}]
        assert get_task_records(other) == remote
        page.locator('#submitBtn').click()
        expect(page.locator('#submitBtn')).to_be_enabled()
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskDesc')).to_have_value('Local draft must not overwrite a remote edit')
        assert get_task_records(page) == remote, 'Stale edit overwrote newer task fields'
        page.locator('#cancelBtn').click()
        page.locator('#draftDiscardBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        assert download_tasks(page)['tasks'] == remote
    finally:
        other.close()


CASES = {'long': long_text, 'comma-tags': comma_tags, 'quoted-tags': quoted_tags, 'formatting': formatting,
         'normalization': normalization, 'recovery': recovery, 'stale': stale_edit}


def run(engine, case):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(**options)
        try:
            context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
            try:
                page = context.new_page()
                clear_app_data(page, url)
                add_task(page, 'Canonical export template', no_deadline=True)
                template = download_tasks(page)
            finally:
                context.close()
            selected = CASES if case == 'all' else {case: CASES[case]}
            for name, operation in selected.items():
                context = browser.new_context(accept_downloads=True, reduced_motion='reduce')
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    operation(page, url, template)
                    assert not errors, errors
                    print(f'Imported text edit passed: {name}; browser={engine}', flush=True)
                finally:
                    context.close()
            print(json.dumps({'browser_engine': engine, 'browser': browser.version,
                              'cases': len(selected), 'passed': True}), flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
