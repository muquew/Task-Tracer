#!/usr/bin/env python3
"""Verify appearance preferences through native controls and real browser events.

Uses fresh browser contexts and synthetic tasks. Media emulation covers browser
color-scheme changes; this does not exercise a physical OS, IME, or mobile device.
Failures retain screenshots, a trace, and real browser errors in a unique /tmp
directory (or under --artifacts-dir). No application functions are invoked.
"""

from __future__ import annotations

from smoke_playwright import open_task_editor, reveal_task_field

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import traceback
from typing import Any, Callable, Iterator
import uuid

from playwright.sync_api import BrowserContext, JSHandle, Page, expect, sync_playwright

from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, get_task_records,
    local_server, select_theme_preference, wait_for_app_ready,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
THEME_SELECT = 'select#themeToggleBtn[data-native-select]'
INLINE_EDITOR = '#subtaskListPreview .subtask-edit-input'
DESKTOP = {'width': 1280, 'height': 800}
MOBILE = {'width': 390, 'height': 844}


def source_identity() -> dict[str, str]:
    return {
        name: hashlib.sha256((REPO_ROOT / name).read_bytes()).hexdigest()
        for name in ('index.html', 'tools/smoke_playwright.py',
                     'tools/appearance_preferences_playwright.py')
    }


def snapshot_source(run_dir: Path, identity: dict[str, str]) -> None:
    for name, expected_digest in identity.items():
        content = (REPO_ROOT / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_digest, (
            'Source changed while capturing the input snapshot', name,
        )
        destination = run_dir / 'source-snapshot' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def assert_appearance(page: Page, preference: str, resolved: str) -> None:
    expect(page.locator(THEME_SELECT)).to_have_value(preference)
    expect(page.locator('html')).to_have_attribute('data-theme', resolved)


def emulate_os(page: Page, color_scheme: str) -> None:
    """Wait for the real media event even when a manual theme should stay put."""
    watch = page.evaluate_handle(
        """() => {
            const media = matchMedia('(prefers-color-scheme: dark)');
            const watch = { media, initial: media.matches, events: [] };
            watch.listener = event => watch.events.push(event.matches);
            media.addEventListener('change', watch.listener);
            return watch;
        }"""
    )
    try:
        changed = watch.evaluate('(watch) => watch.initial') != (color_scheme == 'dark')
        page.emulate_media(color_scheme=color_scheme)
        if changed:
            page.wait_for_function('(watch) => watch.events.length > 0', arg=watch)
    finally:
        watch.evaluate('(watch) => watch.media.removeEventListener("change", watch.listener)')
        watch.dispose()


def select_preference(page: Page, preference: str) -> None:
    """Use the actual native select, opening the navigation when it is hidden."""
    select = page.locator(THEME_SELECT)
    expect(select).to_have_count(1)
    toggle = page.locator('#workspaceNavToggle')
    was_open = toggle.get_attribute('aria-expanded') == 'true'
    select_theme_preference(page, preference)
    if not was_open and toggle.get_attribute('aria-expanded') == 'true':
        toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'false')


def assert_native_controls(page: Page) -> str:
    expect(page.locator(THEME_SELECT)).to_have_count(1)
    values = page.locator(f'{THEME_SELECT} option').evaluate_all(
        '(options) => options.map(option => option.value)'
    )
    assert set(values) == {'light', 'dark', 'system'} and len(values) == 3, values
    language = page.locator('select#languageSelect[data-native-select]')
    expect(language).to_have_count(1)
    return language.input_value()


def fresh_preference(page: Page, url: str, os_theme: str) -> None:
    page.emulate_media(color_scheme=os_theme)
    clear_app_data(page, url)
    assert_native_controls(page)
    assert_appearance(page, 'system', os_theme)
    opposite = 'dark' if os_theme == 'light' else 'light'
    emulate_os(page, opposite)
    assert_appearance(page, 'system', opposite)
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    assert_appearance(page, 'system', opposite)
    assert get_task_records(page) == [], 'A fresh appearance preference created tasks'


def legacy_preference(page: Page, url: str, preference: str) -> None:
    opposite = 'dark' if preference == 'light' else 'light'
    page.emulate_media(color_scheme=opposite)
    clear_app_data(page, url)
    # Prepare an actual legacy profile value, then let normal startup consume it.
    page.evaluate('(value) => localStorage.setItem("theme", value)', preference)
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    assert_appearance(page, preference, preference)
    emulate_os(page, preference)
    assert_appearance(page, preference, preference)
    emulate_os(page, opposite)
    assert_appearance(page, preference, preference)
    page.reload(wait_until='domcontentloaded')
    wait_for_app_ready(page)
    assert_appearance(page, preference, preference)


def preference_round_trip(page: Page, url: str, mobile: bool = False) -> None:
    page.set_viewport_size(MOBILE if mobile else DESKTOP)
    page.emulate_media(color_scheme='dark')
    clear_app_data(page, url)
    language = assert_native_controls(page)
    for preference, os_theme, resolved in (
        ('light', 'dark', 'light'),
        ('light', 'light', 'light'),
        ('light', 'dark', 'light'),
        ('dark', 'light', 'dark'),
        ('dark', 'dark', 'dark'),
        ('dark', 'light', 'dark'),
        ('system', 'light', 'light'),
        ('system', 'dark', 'dark'),
        ('system', 'light', 'light'),
    ):
        if page.locator(THEME_SELECT).input_value() != preference:
            select_preference(page, preference)
        emulate_os(page, os_theme)
        assert_appearance(page, preference, resolved)
        expect(page.locator('#languageSelect')).to_have_value(language)
        page.reload(wait_until='domcontentloaded')
        wait_for_app_ready(page)
        assert_appearance(page, preference, resolved)
        expect(page.locator('#languageSelect')).to_have_value(language)
    assert get_task_records(page) == [], 'Changing appearance created tasks'


def seed_tasks(page: Page) -> list[dict[str, Any]]:
    add_task(page, 'Appearance preserved task A', description='Saved description A',
             no_deadline=True, project='Appearance fixture', tags=['synthetic'],
             subtasks=['Saved child A', 'Saved child B'])
    add_task(page, 'Appearance preserved task B', description='Saved description B',
             no_deadline=True)
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#taskList .task-item')).to_have_count(2)
    return get_task_records(page)


def observe_task_nodes(page: Page) -> JSHandle:
    """Observe visible DOM identity, without consulting application state."""
    return page.evaluate_handle(
        """() => {
            const list = document.querySelector('#taskList');
            const nodes = Array.from(list.querySelectorAll('.task-item, .task-item *'));
            const changes = [];
            const observer = new MutationObserver(records => {
                records.forEach(record => changes.push({
                    target: record.target.nodeName,
                    added: record.addedNodes.length,
                    removed: record.removedNodes.length,
                }));
            });
            observer.observe(list, { childList: true, subtree: true });
            return { list, nodes, changes, observer };
        }"""
    )


def assert_task_nodes(page: Page, observation: JSHandle) -> None:
    state = page.evaluate(
        """watch => ({
            sameList: watch.list.isConnected && watch.list === document.querySelector('#taskList'),
            sameNodes: watch.nodes.every(node => node.isConnected && watch.list.contains(node)),
            changes: watch.changes,
        })""", observation,
    )
    assert state['sameList'] and state['sameNodes'] and not state['changes'], (
        'Appearance change rebuilt or mutated saved task nodes', state,
    )


@contextlib.contextmanager
def task_node_observation(page: Page) -> Iterator[JSHandle]:
    observation = observe_task_nodes(page)
    try:
        yield observation
    finally:
        observation.evaluate('(watch) => watch.observer.disconnect()')
        observation.dispose()


def open_unsaved_draft(page: Page) -> None:
    open_task_editor(page)
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#taskName').fill('Unsaved appearance draft 中文 e\u0301')
    page.locator('#taskDesc').fill('Unsaved description line one.\nSecond line stays selected.')
    page.locator('#taskProject').fill('Unsaved project')
    reveal_task_field(page, '#taskTags').fill('draft, appearance')
    page.locator('#noDeadline').check()
    for text in ('Draft child to edit', 'Second unsaved child'):
        page.locator('#subtaskInput').fill(text)
        page.locator('#addSubtaskBtn').click()
    page.locator('#subtaskInput').fill('Pending child input, not added')
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(2)


def select_draft_text(page: Page, selector: str) -> None:
    field = page.locator(selector)
    field.focus()
    expect(field).to_be_focused()
    field.press('Home')
    for _ in range(4):
        field.press('Shift+ArrowRight')
    selection = field.evaluate('(el) => [el.selectionStart, el.selectionEnd]')
    assert selection[1] > selection[0], ('Fixture did not select actual text', selection)


def capture_draft(page: Page) -> JSHandle:
    return page.evaluate_handle(
        """() => {
            const form = document.querySelector('#taskForm');
            const fields = Array.from(form.querySelectorAll('input,textarea,select'));
            const active = document.activeElement;
            const snapshot = () => ({
                values: fields.map(el => ({
                    id: el.id, className: el.className, value: el.value,
                    checked: el.checked, disabled: el.disabled,
                })),
                children: Array.from(form.querySelectorAll('.subtask-preview-item')).map(el =>
                    el.querySelector('input')?.value ?? el.querySelector('.subtask-preview-text')?.textContent),
                activeIsOriginal: document.activeElement === active,
                selection: [active.selectionStart, active.selectionEnd, active.selectionDirection],
            });
            return { form, fields, active, snapshot, baseline: snapshot() };
        }"""
    )


def assert_draft(page: Page, draft: JSHandle) -> None:
    state = page.evaluate(
        """draft => ({
            sameForm: draft.form.isConnected && draft.form === document.querySelector('#taskForm'),
            sameFields: draft.fields.length === draft.form.querySelectorAll('input,textarea,select').length &&
                draft.fields.every(el => el.isConnected && draft.form.contains(el)),
            expected: draft.baseline,
            actual: draft.snapshot(),
        })""", draft,
    )
    expect(page.locator('#taskModal')).to_be_visible()
    assert state['sameForm'] and state['sameFields'], ('Appearance change replaced draft controls', state)
    assert state['actual'] == state['expected'], ('Appearance change altered the unsaved draft/focus/selection', state)


def assert_preserved(page: Page, draft: JSHandle, nodes: JSHandle,
                     records: list[dict[str, Any]]) -> None:
    assert_draft(page, draft)
    assert_task_nodes(page, nodes)
    assert get_task_records(page) == records, 'Appearance change altered saved task records'


def begin_inline_edit(page: Page) -> None:
    page.locator('#subtaskListPreview .subtask-preview-text').first.focus()
    page.keyboard.press('Enter')
    expect(page.locator(INLINE_EDITOR)).to_be_visible()
    page.locator(INLINE_EDITOR).fill('Inline child text still being edited 中文')


def save_preserved_draft(page: Page, records: list[dict[str, Any]]) -> None:
    """Prove the retained visible draft can still be saved through the normal UI."""
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    saved = get_task_records(page)
    existing_ids = {record['id'] for record in records}
    assert [record for record in saved if record['id'] in existing_ids] == records, (
        'Saving the retained draft altered an existing task', saved,
    )
    added = [record for record in saved if record['id'] not in existing_ids]
    assert len(added) == 1, ('Retained draft did not save exactly once', added)
    task = added[0]
    assert task['name'] == 'Unsaved appearance draft 中文 e\u0301', task
    assert task['description'] == 'Unsaved description line one.\nSecond line stays selected.', task
    assert task['project'] == 'Unsaved project' and task['tags'] == ['draft', 'appearance'], task
    assert [child['text'] for child in task['subtasks']] == [
        'Inline child text still being edited 中文', 'Second unsaved child',
    ], task


def draft_os_changes(page: Page, url: str) -> None:
    page.emulate_media(color_scheme='light')
    clear_app_data(page, url)
    select_preference(page, 'system')
    records = seed_tasks(page)
    open_unsaved_draft(page)
    for selector, os_theme in (('#taskName', 'dark'), ('#taskDesc', 'light'),
                               (INLINE_EDITOR, 'dark')):
        if selector == INLINE_EDITOR:
            begin_inline_edit(page)
        select_draft_text(page, selector)
        draft = capture_draft(page)
        try:
            # Opening a form may normally refresh the list. Observe only after
            # that setup, retaining every strict check across the theme change.
            with task_node_observation(page) as nodes:
                emulate_os(page, os_theme)
                assert_appearance(page, 'system', os_theme)
                assert_preserved(page, draft, nodes, records)
        finally:
            draft.dispose()
    save_preserved_draft(page, records)


def observe_storage(page: Page) -> JSHandle:
    return page.evaluate_handle(
        """() => {
            const events = [];
            window.addEventListener('storage', event => {
                if (event.storageArea === localStorage && event.key === 'theme') {
                    events.push({ key: event.key, newValue: event.newValue,
                        oldValue: event.oldValue, isTrusted: event.isTrusted, url: event.url });
                }
            });
            return { events };
        }"""
    )


def assert_real_storage(page: Page, watch: JSHandle, count: int, preference: str) -> None:
    page.wait_for_function('(watch) => watch.events.length >= ' + str(count), arg=watch)
    events = watch.evaluate('(watch) => watch.events')
    assert len(events) == count, ('Unexpected duplicate preference storage events', events)
    assert events[-1]['isTrusted'] and events[-1]['newValue'] == preference, events


def draft_storage_sync(page: Page, url: str) -> None:
    page.emulate_media(color_scheme='light')
    clear_app_data(page, url)
    select_preference(page, 'system')
    records = seed_tasks(page)
    other = page.context.new_page()
    other.emulate_media(color_scheme='dark')
    other.goto(url, wait_until='domcontentloaded')
    wait_for_app_ready(other)
    assert_appearance(page, 'system', 'light')
    assert_appearance(other, 'system', 'dark')
    expect(other.locator('#taskList .task-item')).to_have_count(2)
    # Verify the other direction before keeping a form open in the first page.
    reverse_storage = observe_storage(other)
    try:
        with task_node_observation(page) as receiver_nodes, task_node_observation(other) as sender_nodes:
            for count, preference in enumerate(('light', 'system'), start=1):
                select_preference(page, preference)
                assert_real_storage(other, reverse_storage, count, preference)
                assert_appearance(page, preference, 'light')
                assert_appearance(other, preference, 'light' if preference == 'light' else 'dark')
                assert_task_nodes(page, receiver_nodes)
                assert_task_nodes(other, sender_nodes)
    finally:
        reverse_storage.dispose()
    storage = observe_storage(page)
    open_unsaved_draft(page)
    try:
        for index, (selector, preference, receiver_theme, sender_theme) in enumerate((
            ('#taskName', 'dark', 'dark', 'dark'),
            ('#taskDesc', 'light', 'light', 'light'),
            (INLINE_EDITOR, 'system', 'light', 'dark'),
        ), start=1):
            if selector == INLINE_EDITOR:
                begin_inline_edit(page)
            select_draft_text(page, selector)
            draft = capture_draft(page)
            try:
                with task_node_observation(page) as receiver_nodes, task_node_observation(other) as sender_nodes:
                    select_preference(other, preference)
                    assert_real_storage(page, storage, index, preference)
                    assert_appearance(page, preference, receiver_theme)
                    assert_appearance(other, preference, sender_theme)
                    assert_preserved(page, draft, receiver_nodes, records)
                    assert_task_nodes(other, sender_nodes)
                    assert get_task_records(other) == records, 'Sender preference changed saved records'
            finally:
                draft.dispose()
        # After a synchronized system preference, each page still follows its own OS.
        draft = capture_draft(page)
        try:
            with task_node_observation(page) as receiver_nodes:
                with task_node_observation(other) as sender_nodes:
                    emulate_os(page, 'dark')
                    emulate_os(other, 'light')
                    assert_appearance(page, 'system', 'dark')
                    assert_appearance(other, 'system', 'light')
                    assert_preserved(page, draft, receiver_nodes, records)
                    assert_task_nodes(other, sender_nodes)
                other.reload(wait_until='domcontentloaded')
                wait_for_app_ready(other)
                assert_appearance(other, 'system', 'light')
                assert_preserved(page, draft, receiver_nodes, records)
        finally:
            draft.dispose()
        save_preserved_draft(page, records)
    finally:
        storage.dispose()
        other.close()


CASES: dict[str, Callable[[Page, str], None]] = {
    'fresh-light': lambda page, url: fresh_preference(page, url, 'light'),
    'fresh-dark': lambda page, url: fresh_preference(page, url, 'dark'),
    'legacy-light': lambda page, url: legacy_preference(page, url, 'light'),
    'legacy-dark': lambda page, url: legacy_preference(page, url, 'dark'),
    'preferences-desktop': preference_round_trip,
    'preferences-mobile': lambda page, url: preference_round_trip(page, url, mobile=True),
    'draft-os-change': draft_os_changes,
    'draft-storage-sync': draft_storage_sync,
}


def collect_browser_errors(context: BrowserContext, errors: list[dict[str, Any]]) -> None:
    def attach(page: Page) -> None:
        label = f'page-{len(context.pages)}'
        page.on('pageerror', lambda error: errors.append(
            {'page': label, 'kind': 'pageerror', 'message': str(error), 'stack': error.stack}))
        page.on('console', lambda message: errors.append(
            {'page': label, 'kind': 'consoleerror', 'message': message.text,
             'location': message.location}) if message.type == 'error' else None)
    context.on('page', attach)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--artifacts-dir', type=Path,
                        help='Parent for a unique run directory; default: /tmp')
    args = parser.parse_args()
    if args.artifacts_dir:
        run_dir = args.artifacts_dir / f'appearance-{args.browser}-{uuid.uuid4()}'
        run_dir.mkdir(parents=True)
    else:
        run_dir = Path(tempfile.mkdtemp(prefix=f'task-tracer-appearance-{args.browser}-'))
    report: dict[str, Any] = {
        'browser_engine': args.browser, 'started_at': datetime.now(timezone.utc).isoformat(),
        'source': source_identity(), 'cases': [], 'passed': False,
        'source_snapshot': 'source-snapshot',
        'scope': 'Fresh contexts, synthetic tasks, real storage events, emulated browser color schemes; '
                 'not a physical OS, IME, mobile device, or Safari/iOS test.',
    }
    selected = CASES if args.case == 'all' else {args.case: CASES[args.case]}
    try:
        snapshot_source(run_dir, report['source'])
        with local_server() as url, sync_playwright() as playwright:
            options = browser_launch_options() if args.browser == 'chromium' else {'headless': True}
            browser = getattr(playwright, args.browser).launch(**options)
            report['browser_version'] = browser.version
            try:
                for name, operation in selected.items():
                    context = browser.new_context(viewport=DESKTOP, reduced_motion='reduce')
                    errors: list[dict[str, Any]] = []
                    result: dict[str, Any] = {'name': name, 'passed': False, 'browser_errors': errors}
                    report['cases'].append(result)
                    collect_browser_errors(context, errors)
                    context.tracing.start(screenshots=True, snapshots=True)
                    try:
                        page = context.new_page()
                        operation(page, url)
                        assert not errors, ('Real browser errors were raised', errors)
                        result['passed'] = True
                        print(f'Appearance preferences passed: {name}; browser={args.browser}', flush=True)
                    except Exception:
                        result['error'] = traceback.format_exc()
                        for index, page in enumerate(context.pages, start=1):
                            try:
                                page.screenshot(path=str(run_dir / f'{name}-page-{index}.png'), full_page=True)
                            except Exception as error:
                                result.setdefault('artifact_errors', []).append(str(error))
                        context.tracing.stop(path=str(run_dir / f'{name}-trace.zip'))
                        raise
                    finally:
                        if result['passed']:
                            context.tracing.stop()
                        context.close()
            finally:
                browser.close()
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        try:
            report['source_final'] = source_identity()
            report['source_unchanged'] = report['source_final'] == report['source']
            if not report['source_unchanged']:
                report['passed'] = False
                report.setdefault('error', 'Application or test source changed during the run')
        except Exception:
            report['source_unchanged'] = False
            report['passed'] = False
            report.setdefault('error', traceback.format_exc())
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (run_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'browser_engine': args.browser, 'passed': report['passed'],
                      'cases': len(report['cases']), 'report': str(run_dir / 'report.json')}), flush=True)
    if not report['passed']:
        print(report['error'], flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
