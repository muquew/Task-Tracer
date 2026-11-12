#!/usr/bin/env python3
"""Verify keyboard bypass and native controls under browser forced-colors media.

Uses two fresh synthetic profiles and the deployed CSP. Forced-colors coverage
is browser emulation, not a Windows, screen-reader, or physical-device claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from playwright.sync_api import Error, expect, sync_playwright

from check import source_identity
from recovery_management_playwright import stored
from settings_navigation_playwright import primary_entries, production_server
from smoke_playwright import browser_launch_options, reveal_task_field, wait_for_app_ready


ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ('settingsAppearance', 'settingsData', 'settingsExperience',
            'settingsCleanup', 'settingsHelp')
SCREENS = ('today', 'tasks', 'projects', 'review')


def outline_state(control, expected):
    # :has(:focus-visible) can invalidate its painted outline on the next frame,
    # even after focus has synchronously moved. Wait for the real visual state.
    handle = control.element_handle()
    try:
        control.page.wait_for_function("""({node, expected}) => {
            const style = getComputedStyle(node);
            const visible = parseFloat(style.outlineWidth) >= 2 && style.outlineStyle !== 'none';
            if (expected === 'unselected') return style.outlineStyle === 'none' || parseFloat(style.outlineWidth) === 0;
            return visible && (expected === 'focused'
                ? parseFloat(style.outlineOffset) > 0 : parseFloat(style.outlineOffset) < 0);
        }""", arg={'node': handle, 'expected': expected}, timeout=10000)
    finally:
        handle.dispose()
    return control.evaluate("""node => {
        const style = getComputedStyle(node);
        return {width:parseFloat(style.outlineWidth), style:style.outlineStyle,
            offset:parseFloat(style.outlineOffset)};
    }""")


def assert_reachable_focus(page):
    focused = page.locator(':focus')
    expect(focused).to_be_visible()
    assert focused.evaluate("""node => !node.closest('[hidden],[inert],[aria-hidden="true"]')"""), \
        'Keyboard navigation entered an inactive page'


def skip_to_content(page, *, first_tab=False, populated=False):
    link = page.locator('.workspace-skip-link')
    if first_tab:
        expect(link).not_to_be_in_viewport()
        page.keyboard.press('Tab')
    else:
        link.focus()
    expect(link).to_be_focused()
    expect(link).to_be_in_viewport(ratio=1)
    page.keyboard.press('Enter')
    expect(page.locator('#mainContent')).to_be_focused()
    expect(link).not_to_be_in_viewport()
    if populated:
        page.keyboard.press('Tab')
        assert_reachable_focus(page)
        assert page.locator(':focus').evaluate('node => Boolean(node.closest("#mainContent"))'), \
            'Tab after bypassing navigation did not enter the active content'


def forced_colors(page, engine):
    try:
        page.emulate_media(forced_colors='active')
    except Error as error:
        if engine != 'webkit' or 'support' not in str(error).lower():
            raise
        print('WebKit does not support forced-colors emulation; native keyboard checks continue', flush=True)
        return False
    active = page.evaluate('() => matchMedia("(forced-colors: active)").matches')
    if not active:
        assert engine == 'webkit', f'{engine}: requested forced-colors media was not applied'
        print('WebKit did not apply forced-colors media; native keyboard checks continue', flush=True)
    return active


def create_with_native_controls(page, name, forced):
    assert stored(page)['tasks'] == [], 'Fresh profile contains tasks before user creation'
    page.locator('#openModalBtn').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#taskName')).to_be_focused()
    checkbox = page.locator('#noDeadline')
    expect(checkbox).to_be_checked()
    if forced:
        style = checkbox.evaluate('node => ({appearance:getComputedStyle(node).appearance, image:getComputedStyle(node).backgroundImage})')
        assert style == {'appearance': 'auto', 'image': 'none'}, \
            f'Forced colors left the checked native control dependent on a custom check image: {style}'
    checkbox.focus()
    page.keyboard.press('Space')
    expect(checkbox).not_to_be_checked()
    expect(page.locator('#dueDate')).to_be_enabled()
    page.keyboard.press('Space')
    expect(checkbox).to_be_checked()
    expect(page.locator('#dueDate')).to_be_disabled()
    page.locator('#taskName').fill(name)
    page.locator('#taskDesc').fill('Exact description retained through inclusive navigation.')
    page.locator('#taskProject').fill('Inclusive workspace')
    page.locator('#submitBtn').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#taskModal')).to_be_hidden()
    message = page.locator('#notificationText')
    expect(message).to_have_attribute('aria-live', 'polite')
    expect(message).to_have_attribute('aria-atomic', 'true')
    parent = page.locator('#notification')
    assert parent.get_attribute('aria-live') in (None, 'off'), 'Toast actions inherited an active parent live region'
    assert parent.get_attribute('role') not in ('status', 'alert', 'log'), 'Toast actions inherited an implicit live role'
    for selector in ('#notificationUndoBtn', '#workspaceNotificationClose'):
        expect(parent.locator(selector)).to_have_count(1)
        expect(message.locator(selector)).to_have_count(0)
    saved = stored(page)
    assert len(saved['tasks']) == 1, 'Keyboard save created zero or duplicate tasks'
    task = saved['tasks'][0]
    assert task['name'] == name and task['description'] == 'Exact description retained through inclusive navigation.'
    assert task['project'] == 'Inclusive workspace' and task.get('dueAt') is None
    return saved


def activate_settings(page):
    toggle = page.locator('#workspaceNavToggle')
    entry = page.locator('#workspaceSettingsBtn')
    if not entry.is_visible():
        toggle.focus()
        page.keyboard.press('Enter')
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        # Opening navigation moves focus on the next animation frame. Wait for
        # that real focus handoff before choosing a different destination.
        page.wait_for_function("""() => {
            const sidebar = document.getElementById('workspaceSidebar');
            return !sidebar.hidden && !sidebar.inert && sidebar.contains(document.activeElement);
        }""")
    entry.focus()
    expect(entry).to_be_focused()
    page.keyboard.press('Enter')
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'settings')


def check_settings_and_theme(page, baseline, forced):
    activate_settings(page)
    selected = page.locator('.settings-section-navigation [aria-selected="true"]')
    selected.focus()
    page.keyboard.press('Home')
    forward = 'ArrowRight' if page.viewport_size['width'] <= 1000 else 'ArrowDown'
    for index, section in enumerate(SECTIONS):
        tab = page.locator(f'[data-settings-section="{section}"]')
        expect(tab).to_be_focused()
        expect(tab).to_have_attribute('aria-selected', 'true')
        expect(page.locator(f'#{section}')).to_be_visible()
        expect(page.locator('main h1:visible')).to_have_count(1)
        expect(page.locator('#settingsTitle')).to_have_text(tab.inner_text())
        assert stored(page) == baseline, f'Keyboard settings navigation wrote stored data: {section}'
        skip_to_content(page, populated=True)
        if not tab.evaluate('node => node === document.activeElement'):
            # Firefox exposes overflowing tablists as native keyboard scroll stops.
            assert page.locator(':focus').evaluate("""node =>
                node.matches('.settings-section-navigation[role="tablist"]')
                && node.scrollWidth > node.clientWidth"""), \
                'Bypass moved to an unexpected control before the settings tabs'
            page.keyboard.press('Tab')
        expect(tab).to_be_focused()
        if index < len(SECTIONS) - 1:
            page.keyboard.press(forward)
    page.keyboard.press('Home')
    expect(page.locator('#tab-settingsAppearance')).to_be_focused()
    checked = page.locator('input[name="workspaceTheme"]:checked')
    expect(checked).to_have_value('iris')
    checked.focus()
    # Native Tab arrival selects keyboard focus indication in every engine;
    # programmatic focus can intentionally retain a previous pointer modality.
    page.keyboard.press('Tab')
    page.keyboard.press('Shift+Tab')
    expect(checked).to_be_focused()
    page.keyboard.press('ArrowRight')
    chosen = page.locator('#workspaceTheme-ocean')
    expect(chosen).to_be_checked()
    expect(chosen).to_be_focused()
    expect(page.locator('input[name="workspaceTheme"]:checked')).to_have_count(1)
    expect(page.locator('html')).to_have_attribute('data-accent', 'ocean')
    assert page.evaluate('() => localStorage.getItem("accent")') == 'ocean'
    hit = chosen.evaluate("""node => {
        const rect = node.getBoundingClientRect();
        const label = node.closest('label').getBoundingClientRect();
        return rect.width >= 44 && rect.height >= 44
            && Math.abs(rect.width-label.width) <= 2 && Math.abs(rect.height-label.height) <= 2
            && document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2) === node;
    }""")
    assert hit, 'Native theme input no longer covers the clickable theme tile'
    if forced:
        tile = chosen.locator('xpath=..')
        focused = outline_state(tile, 'focused')
        assert focused['width'] >= 2 and focused['style'] != 'none' and focused['offset'] > 0, \
            f'Forced colors hid the focused theme outside the selection indication: {focused}'
        page.locator('#tab-settingsAppearance').focus()
        expect(page.locator('#tab-settingsAppearance')).to_be_focused()
        expect(chosen).not_to_be_focused()
        selected = outline_state(tile, 'selected')
        unselected = outline_state(page.locator('#workspaceTheme-iris').locator('xpath=..'), 'unselected')
        assert selected['width'] >= 2 and selected['style'] != 'none' and selected['offset'] < 0, \
            f'Forced colors removed the persistent selected-theme indication after blur: {selected}'
        assert unselected['style'] == 'none' or unselected['width'] == 0, \
            f'Forced colors falsely outlined an unselected, unfocused theme: {unselected}'
    assert stored(page) == baseline, 'Changing appearance altered tasks or saved configuration'


def cancel_without_writes(page, baseline, forced):
    page.locator('#openModalBtn').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#taskName')).to_be_focused()
    page.locator('#taskName').fill('Discard this unsaved inclusive-navigation draft')
    page.locator('#noDeadline').uncheck()
    expect(page.locator('#dueDate')).to_be_enabled()
    reveal_task_field(page, '#repeatType').select_option('weekly-days')
    monday = page.locator('#repeatWeekday1')
    monday.uncheck()
    page.locator('#repeatWeekday2').uncheck()
    monday.focus()
    page.keyboard.press('Tab')
    page.keyboard.press('Shift+Tab')
    expect(monday).to_be_focused()
    page.keyboard.press('Space')
    expect(monday).to_be_checked()
    expect(monday).to_be_focused()
    if forced:
        focused = outline_state(page.locator('#repeatWeekday1 + span'), 'focused')
        assert focused['width'] >= 2 and focused['style'] != 'none' and focused['offset'] > 0, \
            f'Forced colors hid keyboard focus outside the selected weekday: {focused}'
    # Blur the checkbox so a focus ring cannot masquerade as selected feedback.
    page.locator('#taskName').focus()
    expect(monday).not_to_be_focused()
    page.locator('#repeatWeekdaysRow').scroll_into_view_if_needed()
    if forced:
        selected = outline_state(page.locator('#repeatWeekday1 + span'), 'selected')
        unselected = outline_state(page.locator('#repeatWeekday2 + span'), 'unselected')
        assert selected['width'] >= 2 and selected['style'] != 'none' and selected['offset'] < 0, \
            f'Forced colors hid the selected weekday after keyboard focus moved: {selected}, {unselected}'
        assert unselected['style'] == 'none' or unselected['width'] == 0, \
            f'Forced colors falsely outlined an unselected, unfocused weekday: {unselected}'
    assert stored(page) == baseline, 'Editing an unsaved repeat rule changed stored data'
    page.locator('#cancelBtn').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#taskName')).to_have_value('Discard this unsaved inclusive-navigation draft')
    expect(page.locator('#repeatType')).to_have_value('weekly-days')
    expect(monday).to_be_checked()
    page.locator('#cancelBtn').focus()
    page.keyboard.press('Enter')
    page.locator('#draftDiscardBtn').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#taskModal')).to_be_hidden()
    assert stored(page) == baseline, 'Discarding an unsaved keyboard draft changed stored tasks or configuration'


def exercise(browser, url, engine, width, language):
    context = browser.new_context(viewport={'width': width, 'height': 900 if width > 779 else 844},
                                  locale='en-US' if language == 'en' else 'zh-CN',
                                  timezone_id='Asia/Shanghai', reduced_motion='reduce')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(url, wait_until='domcontentloaded')
        wait_for_app_ready(page)
        expect(page.locator('html')).to_have_attribute('lang', language)
        translations = json.loads((ROOT / 'resources' / f'{language}.json').read_text())
        expect(page.locator('.workspace-skip-link')).to_have_text(translations['workspace']['skipToContent'])
        before = stored(page)
        skip_to_content(page, first_tab=True)
        assert stored(page) == before, 'Using the skip link wrote stored data'
        forced = forced_colors(page, engine)
        baseline = create_with_native_controls(page, f'Inclusive navigation {width} {language}', forced)
        # A real navigation strips the skip-link fragment and resets native Tab order.
        page.goto(url, wait_until='domcontentloaded')
        wait_for_app_ready(page)
        assert stored(page) == baseline, 'Reloading changed the task saved with native controls'
        skip_to_content(page, first_tab=True, populated=True)
        for screen, selector in zip(SCREENS, primary_entries(page)):
            page.locator(selector).focus()
            page.keyboard.press('Enter')
            expect(page.locator('body')).to_have_attribute('data-workspace-screen', screen)
            expect(page.locator('main h1:visible')).to_have_count(1)
            assert page.locator('main h1:visible').inner_text().strip()
            assert_reachable_focus(page)
            skip_to_content(page, populated=True)
            assert stored(page) == baseline, f'Keyboard primary navigation wrote stored data: {screen}'
        check_settings_and_theme(page, baseline, forced)
        cancel_without_writes(page, baseline, forced)
        page.reload(wait_until='domcontentloaded')
        wait_for_app_ready(page)
        expect(page.locator('html')).to_have_attribute('data-accent', 'ocean')
        assert page.evaluate('() => localStorage.getItem("accent")') == 'ocean'
        assert stored(page) == baseline, 'Reload changed saved tasks or configuration after keyboard navigation'
        assert not errors, errors
        print(f'{engine}: {width}px {language} keyboard bypass, four pages, five settings, native save/cancel and theme persistence passed; forced-colors={forced}', flush=True)
    except Exception:
        output = Path(tempfile.mkdtemp(prefix=f'task-tracer-inclusive-{engine}-{width}-'))
        page.screenshot(path=str(output / 'failure.png'), full_page=True)
        (output / 'page-errors.json').write_text(json.dumps(errors, indent=2))
        print(f'Inclusive navigation failure evidence: {output}', flush=True)
        raise
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    args = parser.parse_args()
    expect.set_options(timeout=10000)
    identity = source_identity()
    with production_server() as url, sync_playwright() as playwright:
        browser = getattr(playwright, args.browser).launch(**(browser_launch_options() if args.browser == 'chromium' else {'headless': True}))
        try:
            print(f'Inclusive navigation on {args.browser} {browser.version}; source={identity["sha256"]}; forced-colors is browser emulation only', flush=True)
            for width, language in ((1280, 'en'), (390, 'zh-CN')):
                exercise(browser, url, args.browser, width, language)
        finally:
            browser.close()
    assert source_identity() == identity, 'Application source changed during inclusive navigation checks'
    print('Inclusive navigation checks passed with unchanged application source', flush=True)


if __name__ == '__main__':
    main()
