#!/usr/bin/env python3
"""Protect accent preferences, real cross-tab updates and unsaved task drafts."""
from __future__ import annotations

import argparse

from playwright.sync_api import expect, sync_playwright

from accessibility_i18n_audit import find_axe_source, run_axe
from appearance_preferences_playwright import (
    assert_draft, begin_inline_edit, capture_draft, open_unsaved_draft,
    save_preserved_draft, seed_tasks, select_draft_text,
)
from recovery_management_playwright import stored
from smoke_playwright import (
    browser_launch_options, clear_app_data, local_server, open_settings,
    return_to_task_workspace, select_accent_preference, select_theme_preference,
    wait_for_app_ready,
)

ACCENTS = ('iris', 'ocean', 'pine', 'berry')


def assert_accent(page, value):
    expect(page.locator('html')).to_have_attribute('data-accent', value)
    expect(page.locator('#accentSelect')).to_have_value(value)


def assert_native_control(page):
    control = page.locator('#accentSelect')
    expect(control).to_have_count(1)
    assert control.evaluate('node => Boolean(node.closest("#settingsAppearance"))')
    assert control.get_attribute('data-native-select') is not None
    values = control.locator('option').evaluate_all('items => items.map(item => item.value)')
    assert len(values) == len(ACCENTS) and set(values) == set(ACCENTS), values
    expect(page.locator('#accentSelect-custom-button')).to_have_count(0)


def round_trip(page, url):
    clear_app_data(page, url)
    records = seed_tasks(page)
    before = stored(page)
    assert_native_control(page)
    assert_accent(page, 'iris')
    axe_source = find_axe_source().read_text()
    violations = []
    for theme in ('light', 'dark', 'system'):
        select_theme_preference(page, theme)
        resolved = page.locator('html').get_attribute('data-theme')
        for accent in ACCENTS:
            select_accent_preference(page, accent)
            assert_accent(page, accent)
            expect(page.locator('html')).to_have_attribute('data-theme', resolved)
            expect(page.locator('#themeToggleBtn')).to_have_value(theme)
            assert page.evaluate('localStorage.getItem("accent")') == accent
            assert stored(page) == before, 'Changing accent wrote task, revision, history or other IndexedDB configuration'
            if theme != 'system':
                try:
                    run_axe(page, axe_source, f'accent {accent} / {theme} task workspace')
                except AssertionError as error:
                    violations.append(str(error))
                    print(str(error), flush=True)
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, 'berry')
    assert stored(page) == before and before['tasks'] == records
    assert not violations, f'{len(violations)} accent/theme task surfaces failed the original axe rules'
    print('Accent round trip passed: all four values, refresh, native settings-only control and independent theme preferences preserve IndexedDB', flush=True)


def observe_accent_storage(page):
    return page.evaluate_handle('''() => {
        const watch = {events: []};
        addEventListener('storage', event => {
            if (event.storageArea === localStorage && (event.key === 'accent' || event.key === null))
                watch.events.push({key:event.key, value:event.newValue, trusted:event.isTrusted});
        });
        return watch;
    }''')


def assert_event(page, watch, count, key, value):
    page.wait_for_function('(watch) => watch.events.length >= ' + str(count), arg=watch)
    events = watch.evaluate('watch => watch.events')
    assert len(events) == count and events[-1] == {'key': key, 'value': value, 'trusted': True}, events


def cross_tab_draft(page, url):
    clear_app_data(page, url)
    select_theme_preference(page, 'light')
    records = seed_tasks(page)
    before = stored(page)
    other = page.context.new_page()
    watch = observe_accent_storage(page)
    try:
        other.goto(url)
        wait_for_app_ready(other)
        open_unsaved_draft(page)
        for index, (accent, selector) in enumerate(zip(('ocean', 'pine', 'iris', 'berry'), ('#taskName', '#taskDesc', '#taskName', '#taskDesc')), 1):
            select_draft_text(page, selector)
            draft = capture_draft(page)
            try:
                select_accent_preference(other, accent)
                assert_event(page, watch, index, 'accent', accent)
                assert_accent(page, accent)
                expect(page.locator('html')).to_have_attribute('data-theme', 'light')
                assert_draft(page, draft)
                assert stored(page) == before, 'Cross-tab accent updates changed saved data'
            finally:
                draft.dispose()
        begin_inline_edit(page)
        select_draft_text(page, '#subtaskListPreview .subtask-edit-input')
        draft = capture_draft(page)
        try:
            select_theme_preference(other, 'dark')
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            assert_accent(page, 'berry')
            assert_draft(page, draft)
            other.evaluate('localStorage.removeItem("accent")')
            assert_event(page, watch, 5, 'accent', None)
            assert_accent(page, 'iris')
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            assert_draft(page, draft)
            select_accent_preference(other, 'pine')
            assert_event(page, watch, 6, 'accent', 'pine')
            other.evaluate('localStorage.clear()')
            assert_event(page, watch, 7, None, None)
            assert_accent(page, 'iris')
            expect(page.locator('#themeToggleBtn')).to_have_value('system')
            expect(page.locator('html')).to_have_attribute('data-theme', 'light')
            assert_draft(page, draft)
            assert stored(page) == before
        finally:
            draft.dispose()
        save_preserved_draft(page, records)
        print('Accent cross-tab passed: trusted events/removal/clear, theme independence, exact draft fields/focus/selection and a subsequent real save', flush=True)
    finally:
        watch.dispose()
        other.close()


def invalid_and_unavailable_storage(page, url):
    clear_app_data(page, url)
    seed_tasks(page)
    before = stored(page)
    page.evaluate('localStorage.setItem("accent", "invalid-legacy-colour")')
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, 'iris')
    assert stored(page) == before
    page.add_init_script('''(() => {
        const get = Storage.prototype.getItem;
        const set = Storage.prototype.setItem;
        Storage.prototype.getItem = function(key) {
            if (key === 'accent') throw new DOMException('Synthetic blocked accent read', 'SecurityError');
            return get.call(this, key);
        };
        Storage.prototype.setItem = function(key, value) {
            if (key === 'accent') throw new DOMException('Synthetic blocked accent write', 'SecurityError');
            return set.call(this, key, value);
        };
    })();''')
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, 'iris')
    select_accent_preference(page, 'ocean')
    assert_accent(page, 'ocean')
    assert stored(page) == before
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, 'iris')
    assert stored(page) == before
    open_settings(page, 'appearance')
    expect(page.locator('#accentSelect')).to_be_enabled()
    return_to_task_workspace(page)
    print('Accent fallback passed: invalid saved values and genuine browser Storage errors leave the app usable without data changes', flush=True)


CASES = {'roundtrip': round_trip, 'sync-draft': cross_tab_draft, 'fallback': invalid_and_unavailable_storage}


def run(selected):
    with local_server() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        try:
            for name, check in CASES.items():
                if selected not in ('all', name):
                    continue
                context = browser.new_context(reduced_motion='reduce', color_scheme='light', viewport={'width': 390, 'height': 844})
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
