"""Shared repeat delete fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.storage import config

def expected_deletion(before, deleted, predecessor, successor):
    expected = []
    for task in before:
        if task['id'] in deleted:
            continue
        change = {}
        if task['id'] == predecessor:
            change['nextRepeatTaskId'] = successor
        if task['id'] == successor:
            change['repeatCreatedFrom'] = predecessor
        expected.append({**task, **change})
    return expected

def assert_checkpoint(before, after):
    previous, current = config(before), config(after)
    assert current['taskRevision'] == previous['taskRevision'] + 1
    assert current['recoveryHistory'][0]['tasks'] == before['tasks'], \
        'Delete checkpoint did not preserve exact pre-delete links and task fields'
    assert {key: value for key, value in current.items() if key not in {'taskRevision', 'recoveryHistory'}} == \
           {key: value for key, value in previous.items() if key not in {'taskRevision', 'recoveryHistory'}}, \
        'Deletion changed unrelated configuration or backup metadata'
