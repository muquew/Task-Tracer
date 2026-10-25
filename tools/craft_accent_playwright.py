#!/usr/bin/env python3
"""Protect accent preferences, real cross-tab updates and unsaved task drafts."""
from __future__ import annotations

import argparse
import json

from playwright.sync_api import expect, sync_playwright

from accessibility_i18n_audit import (
    assert_focus_visible, assert_layout, assert_workspace_theme_gallery,
    audit_subtask_checkbox_visibility, color_contrast, find_axe_source, run_axe,
    settle_animations, subtask_checkbox_paint,
)
from appearance_preferences_playwright import (
    assert_draft, begin_inline_edit, capture_draft, open_unsaved_draft,
    save_preserved_draft, seed_tasks, select_draft_text,
    task_node_observation, assert_task_nodes,
)
from recovery_management_playwright import stored
from smoke_playwright import (
    assert_theme_chrome, browser_launch_options, clear_app_data, close_workspace_navigation,
    enter_batch_mode, get_task_records, local_server, open_settings, open_task_editor,
    reveal_task_field, select_filter, select_view, task_locator,
    return_to_task_workspace, select_accent_preference, select_theme_preference,
    wait_for_app_ready,
)

ACCENTS = ('iris', 'ocean', 'pine', 'berry')


def assert_accent(page, value):
    expect(page.locator('html')).to_have_attribute('data-accent', value)
    expect(page.locator('input[type="radio"][name="workspaceTheme"]')).to_have_count(4)
    expect(page.locator('input[name="workspaceTheme"]:checked')).to_have_count(1)
    expect(page.locator(f'input[name="workspaceTheme"][value="{value}"]')).to_be_checked()


def assert_native_control(page):
    assert_workspace_theme_gallery(page)
    control = page.locator('#workspaceThemeChoices input[type="radio"][name="workspaceTheme"]')
    values = control.evaluate_all('items => items.map(item => item.value)')
    assert len(values) == len(ACCENTS) and set(values) == set(ACCENTS), values


def audit_skin_surfaces(page, axe_source, accent, theme, violations):
    def audit(surface):
        label = f'workspace skin {accent}/{theme}: {surface}'
        settle_animations(page, label)
        try:
            run_axe(page, axe_source, label)
        except AssertionError as error:
            violations.append(str(error))
            print(str(error), flush=True)
        print('Workspace skin surface checked: ' + label, flush=True)

    return_to_task_workspace(page)
    select_view(page, 'list')
    page.set_viewport_size({'width': 1280, 'height': 900})
    close_workspace_navigation(page)
    audit('desktop list and full sidebar')
    page.set_viewport_size({'width': 390, 'height': 844})
    close_workspace_navigation(page)
    audit('mobile list and dock')
    page.locator('#workspaceNavToggle').click()
    expect(page.locator('#workspaceNavToggle')).to_have_attribute('aria-expanded', 'true')
    audit('mobile navigation drawer')
    close_workspace_navigation(page)
    open_task_editor(page)
    page.locator('#noDeadline').uncheck()
    reveal_task_field(page, '#taskTags')
    audit('complete task editor')
    page.locator('#cancelBtn').click()
    if page.locator('#draftDiscardPrompt').is_visible():
        page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    if page.locator('#captureShelf').is_visible():
        page.locator('#captureCloseBtn').click()
    open_settings(page, 'appearance')
    assert_native_control(page)
    audit('appearance and theme gallery')
    return_to_task_workspace(page)


def round_trip(page, url):
    clear_app_data(page, url)
    records = seed_tasks(page)
    before = stored(page)
    open_settings(page, 'appearance')
    assert_native_control(page)
    return_to_task_workspace(page)
    assert_accent(page, 'iris')
    axe_source = find_axe_source().read_text()
    violations = []
    for theme in ('light', 'dark', 'system'):
        with task_node_observation(page) as nodes:
            select_theme_preference(page, theme)
            assert_task_nodes(page, nodes)
        resolved = page.locator('html').get_attribute('data-theme')
        for accent in ('ocean', 'pine', 'iris', 'berry'):
            with task_node_observation(page) as nodes:
                select_accent_preference(page, accent)
                assert_task_nodes(page, nodes)
            assert_accent(page, accent)
            expect(page.locator('html')).to_have_attribute('data-theme', resolved)
            expect(page.locator('#themeToggleBtn')).to_have_value(theme)
            assert page.evaluate('localStorage.getItem("accent")') == accent
            assert stored(page) == before, 'Changing accent wrote task, revision, history or other IndexedDB configuration'
            if theme != 'system':
                audit_skin_surfaces(page, axe_source, accent, theme, violations)
                assert stored(page) == before, 'Inspecting a workspace skin changed IndexedDB data'
                page.reload()
                wait_for_app_ready(page)
                assert_accent(page, accent)
                expect(page.locator('html')).to_have_attribute('data-theme', resolved)
                assert stored(page) == before
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, 'berry')
    assert stored(page) == before and before['tasks'] == records
    assert not violations, f'{len(violations)} accent/theme task surfaces failed the original axe rules'
    print('Workspace themes passed: four native radio values, all eight light/dark skins across five actual surfaces, refresh and independent System preference preserve task nodes and IndexedDB', flush=True)


def keyboard_gallery(page, url):
    clear_app_data(page, url)
    seed_tasks(page)
    before = stored(page)
    enter_batch_mode(page)
    task_locator(page, 'Appearance preserved task A').locator('.task-select-checkbox').check()
    selected = page.locator('.task-select-checkbox:checked').evaluate_all('items => items.map(item => item.dataset.taskId)')
    open_settings(page, 'appearance')
    for width in (320, 390, 1280):
        page.set_viewport_size({'width': width, 'height': 900 if width > 779 else 844})
        assert_native_control(page)
        values = page.locator('input[name="workspaceTheme"]').evaluate_all('items => items.map(item => item.value)')
        checked = page.locator('input[name="workspaceTheme"]:checked')
        checked.click()
        expect(checked).to_be_focused()
        for key, direction in (('ArrowRight', 1), ('ArrowDown', 1), ('ArrowLeft', -1), ('ArrowUp', -1)):
            current = checked.get_attribute('value')
            expected = values[(values.index(current) + direction) % len(values)]
            checked.press(key)
            assert_accent(page, expected)
            checked = page.locator('input[name="workspaceTheme"]:checked')
            expect(checked).to_be_focused()
            assert page.evaluate('localStorage.getItem("accent")') == expected
            assert_focus_visible(page, f'input[name="workspaceTheme"][value="{expected}"]', f'{width}px native radio {key}')
            assert stored(page) == before, 'Native theme keys wrote IndexedDB data'
        value = checked.get_attribute('value')
        checked.press('Space')
        assert_accent(page, value)
        checked.press('Tab')
        assert not page.locator('input[name="workspaceTheme"]').evaluate_all('items => items.includes(document.activeElement)'), 'Native radio group added more than one Tab stop'
        page.keyboard.press('Shift+Tab')
        expect(checked).to_be_focused()
        settle_animations(page, f'{width}px workspace theme gallery')
        assert_layout(page, f'{width}px workspace theme gallery')
    return_to_task_workspace(page)
    assert page.locator('.task-select-checkbox:checked').evaluate_all('items => items.map(item => item.dataset.taskId)') == selected
    assert stored(page) == before, 'Choosing themes changed batch selection data or IndexedDB'
    page.locator('#exitBatchModeBtn').click()
    value = page.locator('html').get_attribute('data-accent')
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, value)
    assert stored(page) == before
    print('Workspace theme keyboard passed: native arrows/Space, exclusive checked state, one Tab stop, persisted choice and unchanged batch selection at 320/390/1280px', flush=True)


def completion_paint(control):
    return control.evaluate('''element => {
        const pixel = color => {
            const canvas=document.createElement('canvas'); canvas.width=canvas.height=1;
            const context=canvas.getContext('2d'); context.fillStyle=color; context.fillRect(0,0,1,1);
            return [...context.getImageData(0,0,1,1).data];
        };
        const surface=getComputedStyle(element,'::before'),icon=element.querySelector('svg'),use=icon?.querySelector('use');
        const iconStyle=icon?getComputedStyle(icon):null;
        return {checked:element.getAttribute('aria-pressed')==='true',background:pixel(surface.backgroundColor),
            marker:iconStyle?pixel(iconStyle.color):null,iconOpacity:iconStyle?.opacity,iconVisibility:iconStyle?.visibility,
            iconWidth:icon?.getBoundingClientRect().width,iconHeight:icon?.getBoundingClientRect().height,
            symbol:use?.getAttribute('href'),focusVisible:element.matches(':focus-visible')};
    }''')


def assert_checked_paint(label, unchecked, checked):
    observation = {'label': label, 'unchecked': unchecked, 'checked': checked,
                   'marker_contrast': color_contrast(checked['marker'], checked['background']),
                   'state_contrast': color_contrast(checked['background'], unchecked['background'])}
    print('Workspace control paint: ' + json.dumps(observation, ensure_ascii=False), flush=True)
    assert checked['checked'] and checked['marker'][3] == checked['background'][3] == 255, observation
    assert observation['marker_contrast'] >= 3, observation
    assert observation['state_contrast'] >= 3, observation


def control_interaction(page, control, interaction):
    if interaction == 'hover':
        control.hover()
    elif interaction == 'keyboard-focus':
        page.mouse.move(0, 0)
        control.focus()
        control.press('Tab')
        page.keyboard.press('Shift+Tab')
        expect(control).to_be_focused()
    else:
        page.locator('#searchInput').focus()
        page.mouse.move(0, 0)


def control_contrast(page, url):
    clear_app_data(page, url)
    records = seed_tasks(page)
    for accent in ('ocean', 'pine', 'iris', 'berry'):
        before_preference = stored(page)
        select_accent_preference(page, accent)
        assert stored(page) == before_preference
        audit_subtask_checkbox_visibility(page, f'{accent} full skin')
        assert get_task_records(page) == records, 'The real checked/unchecked subtask exercise changed task contents'
        for theme in ('light', 'dark'):
            select_theme_preference(page, theme)
            select_filter(page, 'all')
            enter_batch_mode(page)
            checkbox = task_locator(page, 'Appearance preserved task B').locator('.task-select-checkbox')
            control_interaction(page, checkbox, 'resting')
            settle_animations(page, f'{accent}/{theme} unchecked batch selection')
            unchecked = subtask_checkbox_paint(checkbox)
            expect(checkbox).not_to_be_checked()
            selection_before = stored(page)
            checkbox.focus()
            checkbox.press('Space')
            expect(checkbox).to_be_checked()
            assert stored(page) == selection_before, 'Selecting a batch checkbox wrote IndexedDB'
            for interaction in ('resting', 'hover', 'keyboard-focus'):
                control_interaction(page, checkbox, interaction)
                settle_animations(page, f'{accent}/{theme} checked batch {interaction}')
                assert_checked_paint(f'{accent}/{theme} batch {interaction}', unchecked, subtask_checkbox_paint(checkbox))
                if interaction == 'keyboard-focus':
                    assert_focus_visible(page, '.task-select-checkbox:checked', f'{accent}/{theme} selected batch control')
            checkbox.focus()
            checkbox.press('Space')
            expect(checkbox).not_to_be_checked()
            assert stored(page) == selection_before, 'Batch selection paint controls wrote IndexedDB'
            page.locator('#exitBatchModeBtn').click()
            control = task_locator(page, 'Appearance preserved task B').locator('[data-action="toggle"]')
            control_interaction(page, control, 'resting')
            settle_animations(page, f'{accent}/{theme} unchecked task')
            unchecked = completion_paint(control)
            control.click()
            expect(control).to_have_attribute('aria-pressed', 'true')
            for interaction in ('resting', 'hover', 'keyboard-focus'):
                control_interaction(page, control, interaction)
                settle_animations(page, f'{accent}/{theme} completed task {interaction}')
                paint = completion_paint(control)
                assert paint['symbol'] == '#icon-check' and float(paint['iconOpacity']) > 0 and paint['iconVisibility'] == 'visible'
                assert paint['iconWidth'] > 0 and paint['iconHeight'] > 0
                assert_checked_paint(f'{accent}/{theme} task completion {interaction}', unchecked, paint)
                if interaction == 'keyboard-focus':
                    assert_focus_visible(page, '.task-completion[aria-pressed="true"]', f'{accent}/{theme} completed task control')
            page.locator('#undoBtn').click()
            expect(page.locator('#undoBtn')).to_be_disabled()
            assert get_task_records(page) == records, 'Completion paint Undo did not restore exact task records'
    print('Workspace controls passed: actual subtask/batch/task checked state and marker contrast across all eight skins; real completion Undo preserves task records', flush=True)


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
                with task_node_observation(page) as nodes:
                    select_accent_preference(other, accent)
                    assert_event(page, watch, index, 'accent', accent)
                    assert_accent(page, accent)
                    expect(page.locator('html')).to_have_attribute('data-theme', 'light')
                    assert_draft(page, draft)
                    assert_task_nodes(page, nodes)
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
    expect(page.locator('input[name="workspaceTheme"]:checked')).to_be_enabled()
    return_to_task_workspace(page)
    print('Accent fallback passed: invalid saved values and genuine browser Storage errors leave the app usable without data changes', flush=True)


def chrome_sync(page, url):
    clear_app_data(page, url)
    seed_tasks(page)
    before = stored(page)
    for theme in ('light', 'dark'):
        select_theme_preference(page, theme)
        for accent in ('ocean', 'pine', 'iris', 'berry'):
            with task_node_observation(page) as nodes:
                select_accent_preference(page, accent)
                assert_accent(page, accent)
                chrome = assert_theme_chrome(page)
                assert_task_nodes(page, nodes)
            assert stored(page) == before, 'Native chrome synchronization changed IndexedDB data'
            print('Theme chrome: ' + json.dumps({'phase':'radio','accent':accent,'theme':theme,**chrome}, ensure_ascii=False), flush=True)
            page.reload()
            wait_for_app_ready(page)
            assert_accent(page, accent)
            expect(page.locator('html')).to_have_attribute('data-theme', theme)
            chrome = assert_theme_chrome(page)
            assert stored(page) == before, 'Refreshing a chrome preference changed IndexedDB data'
            print('Theme chrome: ' + json.dumps({'phase':'refresh','accent':accent,'theme':theme,**chrome}, ensure_ascii=False), flush=True)
    page.evaluate('localStorage.setItem("accent", "invalid-chrome-legacy-value")')
    page.reload()
    wait_for_app_ready(page)
    assert_accent(page, 'iris')
    expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
    chrome = assert_theme_chrome(page)
    print('Theme chrome: ' + json.dumps({'phase':'invalid-preference','accent':'iris','theme':'dark',**chrome}, ensure_ascii=False), flush=True)
    assert stored(page) == before
    other = page.context.new_page()
    watch = observe_accent_storage(page)
    try:
        other.goto(url)
        wait_for_app_ready(other)
        with task_node_observation(page) as nodes:
            select_accent_preference(other, 'ocean')
            assert_event(page, watch, 1, 'accent', 'ocean')
            assert_accent(page, 'ocean')
            chrome = assert_theme_chrome(page)
            assert_task_nodes(page, nodes)
        assert stored(page) == before, 'Cross-tab chrome synchronization changed IndexedDB data'
        print('Theme chrome: ' + json.dumps({'phase':'cross-tab','accent':'ocean','theme':'dark',**chrome}, ensure_ascii=False), flush=True)
    finally:
        watch.dispose()
        other.close()
    print('Theme chrome passed: eight radio/mode pairs and refreshes, invalid preference fallback, trusted cross-tab change, opaque CSS chrome equality and unchanged task data', flush=True)


CASES = {'roundtrip': round_trip, 'keyboard': keyboard_gallery, 'controls': control_contrast,
         'sync-draft': cross_tab_draft, 'fallback': invalid_and_unavailable_storage, 'chrome': chrome_sync}


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
