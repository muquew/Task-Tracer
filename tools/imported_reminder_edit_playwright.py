#!/usr/bin/env python3
"""Preserve imported reminder durations through editing and draft recovery."""
from __future__ import annotations

from smoke_playwright import open_task_editor

import argparse
import json

from playwright.sync_api import expect, sync_playwright

from imported_text_edit_playwright import import_fixture, open_edit, save_and_assert
from smoke_playwright import select_language
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, exercise_export_backup,
    get_task_records, local_server,
)
from task_draft_playwright import inject_quota_failure


def assert_controls(page, offset, repeat):
    expect(page.locator('#reminderOffset')).to_have_value(str(offset))
    expect(page.locator('#reminderRepeat')).to_have_value(str(repeat))
    if offset != -1:
        expect(page.locator('#reminderOffset-custom-button')).to_contain_text(str(abs(offset)))
    if repeat != -1:
        expect(page.locator('#reminderRepeat-custom-button')).to_contain_text(str(repeat))


def fixture_overrides(offset=7.5, repeat=22.5, undated=False):
    values = {'reminderOffset': offset, 'reminderRepeat': repeat,
              'snoozedUntil': '2039-01-03T09:00:00.000Z',
              'lastReminderAt': '2039-01-01T09:00:00.000Z'}
    if undated:
        values.update({key: None for key in ('dueAt', 'dueDate', 'dueLocalDate', 'dueLocalTime', 'dueTimeZone')})
    return values


def preserve(page, url, template, offset, repeat, undated=False):
    baseline = import_fixture(page, url, template, fixture_overrides(offset, repeat, undated))
    open_edit(page)
    expect(page.locator('#reminderOffset')).to_have_value(str(offset))
    if offset != -1 and not undated:
        assert_controls(page, offset, repeat)
    description = 'Only description changed; custom reminder values remain exact.'
    page.locator('#taskDesc').fill(description)
    save_and_assert(page, [{**baseline[0], 'description': description}])


def choose(page, control, value):
    page.locator(f'#{control}-custom-button').click()
    page.locator(f'#{control}-custom-button-list [data-value="{value}"]').click()


def change_settings(page, url, template):
    baseline = import_fixture(page, url, template, fixture_overrides())
    open_edit(page)
    assert_controls(page, 7.5, 22.5)
    choose(page, 'reminderOffset', '60')
    choose(page, 'reminderRepeat', '15')
    changed = {**baseline[0], 'reminderOffset': 60, 'reminderRepeat': 15,
               'snoozedUntil': None, 'lastReminderAt': None}
    save_and_assert(page, [changed])
    open_edit(page)
    choose(page, 'reminderOffset', '-1')
    expect(page.locator('#reminderRepeat')).to_be_disabled()
    changed = {**changed, 'reminderOffset': -1, 'reminderRepeat': -1}
    save_and_assert(page, [changed])
    open_edit(page)
    page.locator('#noDeadline').check()
    expected = {**changed, **{key: None for key in ('dueAt', 'dueDate', 'dueLocalDate', 'dueLocalTime', 'dueTimeZone')}}
    save_and_assert(page, [expected])
    baseline = import_fixture(page, url, template, fixture_overrides())
    open_edit(page)
    page.locator('#dueDate').fill('')
    page.locator('#noDeadline').check()
    expected = {**baseline[0], **{key: None for key in ('dueAt', 'dueDate', 'dueLocalDate', 'dueLocalTime', 'dueTimeZone')},
                'reminderOffset': -1, 'reminderRepeat': -1, 'snoozedUntil': None, 'lastReminderAt': None}
    save_and_assert(page, [expected])


def recover(page, url, template):
    baseline = import_fixture(page, url, template, fixture_overrides())
    page.evaluate('window.reminderRecoveryOriginalDocument = true')
    open_edit(page)
    page.locator('#taskDesc').fill('Custom reminders survived a failed save and resume.')
    inject_quota_failure(page, 'put')
    page.locator('#submitBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_visible()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert get_task_records(page) == baseline, 'Aborted save changed reminder fields'
    page.locator('#retryStorageBtn').click()
    expect(page.locator('#storageUnavailableBanner')).to_be_hidden()
    assert page.evaluate('window.reminderRecoveryOriginalDocument === true')
    page.locator('#taskDraftRecoveryRestoreBtn').click()
    assert_controls(page, 7.5, 22.5)
    expect(page.locator('#taskDesc')).to_have_value('Custom reminders survived a failed save and resume.')
    save_and_assert(page, [{**baseline[0], 'description': 'Custom reminders survived a failed save and resume.'}])


def labels_and_reset(page, url, template):
    baseline = import_fixture(page, url, template, fixture_overrides(-2.5, 33.25))
    page.set_viewport_size({'width': 390, 'height': 844})
    for language in ('en', 'zh-CN'):
        select_language(page, language)
        page.keyboard.press('Escape')
        open_edit(page)
        assert_controls(page, -2.5, 33.25)
        for control in ('reminderOffset', 'reminderRepeat'):
            text = page.locator(f'#{control}-custom-button').inner_text()
            assert 'form.' not in text and '{minutes}' not in text, text
        expect(page.locator('#reminderOffset-custom-button')).to_contain_text('after' if language == 'en' else '截止后')
        assert page.locator('#taskModal').evaluate('el => el.scrollWidth <= el.clientWidth + 1'), 'Custom labels overflow the narrow dialog'
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        assert get_task_records(page) == baseline, 'Cancelled inspection modified tasks'
    open_task_editor(page)
    expect(page.locator('#reminderOffset')).to_have_value('15')
    expect(page.locator('#reminderRepeat')).to_have_value('-1')
    expect(page.locator('option[data-reminder-custom]')).to_have_count(0)
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert get_task_records(page) == baseline


def run(engine, case):
    with local_server() as url, sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(**options)
        context = browser.new_context(timezone_id='UTC', accept_downloads=True, reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            add_task(page, 'Imported reminder fixture', due_date='2039-01-04', due_time='12:00', reminder_offset='15')
            template = exercise_export_backup(page)
            cases = {
                'fractional': lambda: preserve(page, url, template, 7.5, 22.5),
                'after-due': lambda: preserve(page, url, template, -2.5, 33.25),
                'off': lambda: preserve(page, url, template, -1, 22.5),
                'undated': lambda: preserve(page, url, template, 7.5, 22.5, True),
                'change': lambda: change_settings(page, url, template),
                'recovery': lambda: recover(page, url, template),
                'labels': lambda: labels_and_reset(page, url, template),
            }
            for name, check in (cases.items() if case == 'all' else [(case, cases[case])]):
                check()
                assert not errors, errors
                print(f'Imported reminders passed: {name}; full fields/reload/download or explicit UI boundary verified', flush=True)
            print(json.dumps({'browser_engine': engine, 'browser': browser.version, 'case': case, 'passed': True}), flush=True)
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'fractional', 'after-due', 'off', 'undated', 'change', 'recovery', 'labels'), default='all')
    args = parser.parse_args()
    run(args.browser, args.case)
