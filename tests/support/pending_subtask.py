"""Shared pending subtask fixtures and assertions; no test entry point."""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import Page
from tests.support.browser import get_task_records, wait_for_app_ready

def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def by_id(records):
    return {record['id']: record for record in records}

def check_subtasks(task, expected_texts) -> None:
    children = task['subtasks']
    assert [child['text'] for child in children] == expected_texts, children
    identifiers = [child['id'] for child in children]
    assert all(identifier is not None for identifier in identifiers), children
    assert len(set(identifiers)) == len(identifiers), 'Subtask identifiers collided'

def only_added(page: Page, before, name, expected_texts):
    after = get_task_records(page)
    original = by_id(before)
    assert {item['id']: item for item in after if item['id'] in original} == original, 'Creating a task changed an existing record'
    added = [item for item in after if item['id'] not in original]
    assert len(after) == len(before) + 1 and len(added) == 1, 'One submission created zero or duplicate tasks'
    task = added[0]
    assert task['name'] == name, task
    check_subtasks(task, expected_texts)
    assert all(child['completed'] is False for child in task['subtasks']), task
    return task

def persisted_after_reload(page: Page) -> None:
    expected = get_task_records(page)
    page.reload()
    wait_for_app_ready(page)
    assert get_task_records(page) == expected, 'Reload changed the committed task data'
