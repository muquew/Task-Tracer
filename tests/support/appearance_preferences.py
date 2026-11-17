"""Shared appearance preferences fixtures and assertions; no test entry point."""
from __future__ import annotations
import contextlib
from tests.support.browser import open_task_editor, reveal_task_field
from typing import Any, Iterator
from playwright.sync_api import JSHandle, Page, expect
from tests.support.browser import add_task, get_task_records

INLINE_EDITOR = '#subtaskListPreview .subtask-edit-input'

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
    reveal_task_field(page, '#subtaskInput')
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
        'Pending child input, not added',
    ], task
