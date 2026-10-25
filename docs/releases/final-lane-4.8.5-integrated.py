from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from check import atomic_report, source_identity, verification_identity, stop_child

freeze = json.loads(Path('/tmp/task-tracer-4.8.5-freeze-4.json').read_text())
state_path = Path('/tmp/task-tracer-4.8.5-integrated-lane.json')
assert not state_path.exists(), 'A prior final-lane result exists; preserve it before a new run.'
steps = [
    ('workspace-10000', ['tools/workspace_roundtrip_playwright.py', '--size', '10000', '--subtasks', '6', '--full-views', '--output', '/tmp/task-tracer-4.8.5-workspace-10000-integrated.json'], '/tmp/task-tracer-4.8.5-workspace-10000-integrated.log'),
    ('storage-10000', ['tools/workspace_failure_playwright.py', '--size', '10000', '--subtasks', '6', '--output', '/tmp/task-tracer-4.8.5-storage-10000-integrated.json'], '/tmp/task-tracer-4.8.5-storage-10000-integrated.log'),
    ('actual-4.8.4-upgrade', ['tools/upgrade_playwright.py', '--baseline-archive', 'dist/task-tracer-4.8.4.zip'], '/tmp/task-tracer-upgrade-4.8.4-to-4.8.5.log'),
    ('complete-58', ['tools/check.py', '--keep-going', '--report', 'dist/check-results-4.8.5.json'], '/tmp/task-tracer-4.8.5-check-integrated.log'),
]
env = os.environ.copy()
env.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1', 'TASK_TRACER_BROWSER_EXECUTABLE': '/usr/bin/chromium'})
state = {'status': 'initializing', 'passed': False, 'started_at': datetime.now(timezone.utc).isoformat(), 'current': None, 'steps': [], 'freeze': '/tmp/task-tracer-4.8.5-freeze-4.json', 'error': None}
child = None

def publish():
    atomic_report(state_path, state)

def verify():
    assert source_identity() == freeze['source'], 'Frozen source changed'
    assert verification_identity() == freeze['verification'], 'Frozen verification inputs changed'

def interrupted(signum, frame):
    raise KeyboardInterrupt(f'Signal {signum}')

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, interrupted)
publish()
try:
    verify()
    for name, args, logfile in steps:
        verify()
        assert not Path(logfile).exists(), f'Refusing to overwrite prior log: {logfile}'
        state['status'] = 'running'; state['current'] = name; publish()
        print(f'Starting final lane: {name}', flush=True)
        started = datetime.now(timezone.utc).isoformat()
        with Path(logfile).open('x') as output:
            child = subprocess.Popen([sys.executable, *args], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            code = child.wait()
            child = None
        verify()
        state['steps'].append({'name': name, 'arguments': args, 'log': logfile, 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(), 'exit_code': code})
        publish()
        print(f'Finished final lane: {name}, exit={code}', flush=True)
        if code:
            raise RuntimeError(f'{name} failed with exit {code}; original report/log preserved')
    state['status'] = 'passed'; state['passed'] = True
except BaseException as error:
    if child is not None:
        stop_child(child)
    state['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
    state['error'] = f'{type(error).__name__}: {error}'
    raise
finally:
    state['finished_at'] = datetime.now(timezone.utc).isoformat()
    if state['passed']:
        state['current'] = None
    publish()
