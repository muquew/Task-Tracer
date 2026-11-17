"""Shared import preview concurrency fixtures and assertions; no test entry point."""
from __future__ import annotations
from datetime import datetime
from tests.support.browser import get_task_records

def assert_reminder_metadata_only(page, before, reminder_name, delivery_started):
    after = get_task_records(page)
    previous = {task['id']: task for task in before}
    current = {task['id']: task for task in after}
    assert len(after) == len(before) and set(current) == set(previous), \
        'Reminder delivery added or removed task records'
    pending = [task for task in before if task['name'] == reminder_name]
    assert len(pending) == 1, 'The pending reminder fixture must identify exactly one task'
    reminder_id = pending[0]['id']
    metadata = {'lastReminderAt', 'snoozedUntil'}
    for task_id, old in previous.items():
        task = current[task_id]
        if task_id != reminder_id:
            assert task == old, 'Reminder delivery changed an unrelated task'
            continue
        assert {key: value for key, value in task.items() if key not in metadata} == \
               {key: value for key, value in old.items() if key not in metadata}, \
            'Reminder delivery overwrote task content or another non-reminder field'
        assert task.get('snoozedUntil') is None, 'Delivered reminder did not clear its prior snooze'
        delivered = task.get('lastReminderAt')
        assert isinstance(delivered, str) and delivered != old.get('lastReminderAt'), \
            'The pending reminder did not persist a new delivery timestamp'
        timestamp = datetime.fromisoformat(delivered.replace('Z', '+00:00'))
        assert timestamp.tzinfo is not None, 'Reminder delivery timestamp must include its timezone'
        delivered_ms = round(timestamp.timestamp() * 1000)
        observed_ms = page.evaluate('Date.now()')
        assert delivery_started <= delivered_ms <= observed_ms, \
            'Reminder delivery timestamp is outside the actual completion interval'
    return after
