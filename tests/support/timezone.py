"""Shared timezone fixtures and assertions; no test entry point."""
from __future__ import annotations

def fixture(identity, name, instant, zone):
    return {'id': identity, 'name': name, 'description': 'Synthetic timezone regression',
            'dueAt': instant, 'dueDate': instant, 'dueTimeZone': zone,
            'reminderOffset': -1, 'reminderRepeat': -1, 'repeatType': 'none',
            'completed': False, 'archived': False, 'subtasks': [],
            'createdAt': '2026-01-01T00:00:00.000Z', 'order': identity * 1000}
