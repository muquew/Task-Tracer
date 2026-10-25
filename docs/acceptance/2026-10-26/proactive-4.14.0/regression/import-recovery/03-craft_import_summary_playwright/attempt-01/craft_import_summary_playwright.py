#!/usr/bin/env python3
"""Compare live import decisions with actual task data and snapshot protection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from batch_selection_playwright import transaction_state
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, get_task_records,
    local_server, open_settings, select_language, select_visible_option,
)

ROOT = Path(__file__).resolve().parents[1]


def translations(page):
    language = page.locator('html').get_attribute('lang')
    return json.loads((ROOT / 'resources' / f'{language}.json').read_text())['dataReview']


def prepare(page, url):
    clear_app_data(page, url)
    select_language(page, 'en')
    add_task(page, 'Local reviewed A', description='Original local A', no_deadline=True, project='Inbox', tags=['keep-original'])
    add_task(page, 'Local protected B', description='Original local B', no_deadline=True, project='Protected', subtasks=['Original child'])
    before = get_task_records(page)
    first = next(task for task in before if task['name'] == 'Local reviewed A')
    incoming = [
        {**first, 'description': 'Incoming reviewed A'},
        {**first, 'id': 9901122, 'name': 'Incoming distinct C', 'description': 'Incoming unique C'},
    ]
    return before, incoming


def open_preview(page, tasks):
    open_settings(page, 'data')
    with page.expect_file_chooser() as chooser:
        page.locator('#importBtn').click()
    chooser.value.set_files({'name': 'small-reviewed-import.json', 'mimeType': 'application/json', 'buffer': json.dumps(tasks).encode()})
    expect(page.locator('#mergeImportMode')).to_be_visible()
    expect(page.locator('#importOutcomeSummary')).to_be_visible()


def assert_summary(page, mode, **values):
    text = translations(page)[f'{mode}Summary'].format(**values)
    expect(page.locator('#importOutcomeSummary')).to_have_text(text)


def assert_merge_action(page, count):
    resource = translations(page)
    key = 'importNoChanges' if count == 0 else 'importMergeActionOne' if count == 1 else 'importMergeAction'
    expect(page.locator('#submitBtn')).to_have_text(resource[key].format(count=count))


def dynamic_merge(page, url):
    before, incoming = prepare(page, url)
    baseline = transaction_state(page)
    open_preview(page, incoming)
    assert_summary(page, 'replace', current=2, incoming=2, after=2)
    page.locator('#mergeImportMode').check()
    select_visible_option(page, '#import-conflict-0', 'keep')
    assert_summary(page, 'merge', added=2, replaced=0, skipped=0, kept=2, after=4)
    assert_merge_action(page, 2)
    assert transaction_state(page) == baseline, 'Previewing keep-both wrote task data, revision or history'
    select_visible_option(page, '#import-conflict-0', 'skip')
    assert_summary(page, 'merge', added=1, replaced=0, skipped=1, kept=2, after=3)
    assert_merge_action(page, 1)
    assert transaction_state(page) == baseline
    select_visible_option(page, '#import-conflict-0', 'replace')
    assert_summary(page, 'merge', added=1, replaced=1, skipped=0, kept=1, after=3)
    assert_merge_action(page, 2)
    if page.locator('#mergeImportMode').get_attribute('type') == 'radio':
        page.locator('#replaceImportMode').check()
    else:
        page.locator('#mergeImportMode').uncheck()
    assert_summary(page, 'replace', current=2, incoming=2, after=2)
    page.locator('#mergeImportMode').check()
    assert_summary(page, 'merge', added=1, replaced=1, skipped=0, kept=1, after=3)
    assert transaction_state(page) == baseline, 'Changing import decisions changed committed data'
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = get_task_records(page)
    assert len(after) == 3, 'Actual merged count differs from the reviewed result'
    protected = next(task for task in before if task['name'] == 'Local protected B')
    assert protected in after, 'Conflict replacement altered an unrelated protected task'
    assert [task['description'] for task in after if task['name'] == 'Local reviewed A'] == ['Incoming reviewed A']
    assert [task['description'] for task in after if task['name'] == 'Incoming distinct C'] == ['Incoming unique C']
    page.locator('#undoBtn').click()
    expect(page.locator('#undoBtn')).to_be_disabled()
    assert get_task_records(page) == before, 'Undo did not restore the exact pre-merge tasks'
    print('Import decision summary passed: keep/skip/replace and mode changes match final task counts, untouched records and Undo', flush=True)


def all_skip(page, url):
    before, _ = prepare(page, url)
    baseline = transaction_state(page)
    incoming = [{**task, 'description': 'An incoming conflict that must be skipped'} for task in before]
    open_preview(page, incoming)
    page.locator('#mergeImportMode').check()
    select_visible_option(page, '#importConflictDefaultAction', 'skip')
    assert_summary(page, 'merge', added=0, replaced=0, skipped=2, kept=2, after=2)
    assert_merge_action(page, 0)
    expect(page.locator('#submitBtn')).to_be_disabled()
    assert transaction_state(page) == baseline, 'All-skip review changed data before confirmation'
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert transaction_state(page) == baseline, 'Cancelling an all-skip review wrote task data'
    print('Import zero-change passed: live all-skip result, disabled write action and unchanged full task/revision/history state', flush=True)


def replace_snapshot(page, url):
    before, incoming = prepare(page, url)
    baseline = transaction_state(page)
    open_preview(page, incoming[1:])
    assert_summary(page, 'replace', current=2, incoming=1, after=1)
    with page.expect_download() as result:
        page.locator('#submitBtn').click()
    snapshot = json.loads(result.value.path().read_text())
    assert snapshot['tasks'] == before, 'The pre-replacement download does not contain the exact current tasks'
    expect(page.locator('#taskModal')).to_be_visible()
    assert transaction_state(page) == baseline, 'Snapshot download applied replacement before the second explicit action'
    expect(page.locator('#submitBtn')).to_have_text(translations(page)['importReplaceActionOne'].format(count=1))
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = get_task_records(page)
    assert len(after) == 1 and after[0]['name'] == 'Incoming distinct C'
    assert after[0]['description'] == 'Incoming unique C'
    page.locator('#undoBtn').click()
    expect(page.locator('#undoBtn')).to_be_disabled()
    assert get_task_records(page) == before
    print('Import replacement passed: live impact, genuine exact snapshot download, second confirmation and exact task Undo', flush=True)


CASES = {'dynamic': dynamic_merge, 'skip': all_skip, 'replace': replace_snapshot}


def run(selected):
    with local_server() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        try:
            for name, check in CASES.items():
                if selected not in ('all', name):
                    continue
                context = browser.new_context(accept_downloads=True, reduced_motion='reduce', viewport={'width': 390, 'height': 844})
                try:
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    check(page, url)
                    assert not errors, (name, errors)
                finally:
                    context.close()
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('all', *CASES), default='all')
    run(parser.parse_args().case)
