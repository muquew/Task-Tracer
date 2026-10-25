#!/usr/bin/env python3
"""Exercise check-report lifecycle using isolated subprocesses and local files only."""
from __future__ import annotations

import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools' / 'check.py'
MOCK = r'''from pathlib import Path
import json,os,time
root=Path(__file__).resolve().parents[1]
control=root/'control'
name=Path(__file__).name
plan=json.loads((control/'plan.json').read_text())
operation=plan.get('mutations',{}).get(name)
if operation:
    kind,action=operation.split('-',1)
    target=root/{'source':'index.html','verification':'tools/nested/unused.py','workflow':'.github/workflows/checks.yml'}[kind]
    original=control/(kind+'-original')
    if action=='restore': target.write_bytes(original.read_bytes())
    elif action=='delete': target.unlink()
    else: target.write_bytes(target.read_bytes()+b'\nSYNTHETIC_INPUT_CHANGE\n')
marker=control/(name+'.entered.json')
temporary=marker.with_suffix('.tmp')
temporary.write_text(json.dumps({'pid':os.getpid()}))
temporary.replace(marker)
while name in plan.get('block',[]) and not (control/(name+'.release')).exists():
    time.sleep(0.01)
time.sleep(plan.get('delay',0))
raise SystemExit(plan.get('exit_codes',{}).get(name,0))
'''
FIELDS = {
    'schema_version', 'run_id', 'status', 'started_at', 'updated_at', 'finished_at',
    'planned_checks', 'current_check', 'source', 'verification', 'source_final',
    'verification_final', 'source_unchanged', 'verification_unchanged',
    'integrity_errors', 'error', 'completed', 'passed', 'checks',
}


def static_checks(source: str) -> list[str]:
    candidates = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts \
                and all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in node.elts):
            values = [item.value for item in node.elts]
            if 'validate_static.py' in values:
                candidates.append(values)
    assert len(candidates) == 1, 'The runner must expose one literal static-check plan'
    return candidates[0]


def stamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert parsed.utcoffset() is not None
    return parsed


def assert_identity(value):
    if value is None:
        return
    assert set(value) == {'files', 'sha256'}
    assert isinstance(value['files'], dict) and value['files']
    for name, digest in value['files'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert isinstance(digest, str) and len(digest) == 64 and set(digest) <= set('0123456789abcdef')
    serialized = json.dumps(value['files'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    assert value['sha256'] == hashlib.sha256(serialized).hexdigest()


def assert_report(value, planned):
    assert FIELDS <= set(value)
    assert value['schema_version'] == 2
    assert str(uuid.UUID(value['run_id'])) == value['run_id']
    assert value['status'] in {'initializing', 'running', 'passed', 'failed', 'interrupted', 'error'}
    assert value['planned_checks'] == planned
    assert stamp(value['updated_at']) >= stamp(value['started_at'])
    if value['finished_at'] is not None:
        assert stamp(value['finished_at']) >= stamp(value['started_at'])
    assert isinstance(value['completed'], bool) and isinstance(value['passed'], bool)
    for key in ('source', 'verification', 'source_final', 'verification_final'):
        assert_identity(value[key])
    for key in ('source_unchanged', 'verification_unchanged'):
        assert value[key] is None or isinstance(value[key], bool)
    assert isinstance(value['integrity_errors'], list) and all(isinstance(item, str) for item in value['integrity_errors'])
    assert value['error'] is None or isinstance(value['error'], str)
    current = value['current_check']
    if current is not None:
        assert set(current) == {'program', 'started_at'} and current['program'] in planned
        assert stamp(current['started_at']) >= stamp(value['started_at'])
    assert [item['program'] for item in value['checks']] == planned[:len(value['checks'])]
    for item in value['checks']:
        assert set(item) == {'program', 'exit_code', 'duration_seconds'}
        assert isinstance(item['exit_code'], int)
        assert isinstance(item['duration_seconds'], (int, float)) and item['duration_seconds'] >= 0
    if value['completed']:
        assert len(value['checks']) == len(planned)
    if value['passed']:
        assert value['status'] == 'passed' and value['completed']
        assert all(item['exit_code'] == 0 for item in value['checks'])
        assert value['source_unchanged'] is True and value['verification_unchanged'] is True


def live(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    status = Path(f'/proc/{pid}/stat')
    if status.is_file() and status.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
        return False
    return True


class Fixture:
    def __init__(self, base, label, source, planned):
        self.base = base / label
        self.root = self.base / 'repository'
        self.control = self.root / 'control'
        self.control.mkdir(parents=True)
        (self.root / 'tools' / 'nested').mkdir(parents=True)
        (self.root / 'tools' / 'check.py').write_text(source)
        for name in planned:
            (self.root / 'tools' / name).write_text(MOCK)
        (self.root / 'tools' / 'build_release.py').write_text("DISTRIBUTION_SOURCES = {'index.html': 'index.html'}\n")
        (self.root / 'tools' / 'nested' / 'unused.py').write_text('# synthetic quality input\n')
        (self.root / 'tools' / 'nested' / '验证.py').write_text('# synthetic Unicode identity path\n')
        workflows = self.root / '.github' / 'workflows'
        workflows.mkdir(parents=True)
        (workflows / 'checks.yml').write_text('name: Synthetic checks\n')
        (workflows / 'quality.yaml').write_text('name: Synthetic quality\n')
        (self.root / 'index.html').write_text('SYNTHETIC_SOURCE_ORIGINAL\n')
        (self.root / 'package.json').write_text('{"version":"1.0.0"}\n')
        (self.root / 'package-lock.json').write_text('{"version":"1.0.0"}\n')
        (self.root / 'requirements-dev.txt').write_text('# no dependencies in this fixture\n')
        self.original_source = (self.root / 'index.html').read_bytes()
        self.original_verification = (self.root / 'tools' / 'nested' / 'unused.py').read_bytes()
        (self.control / 'source-original').write_bytes(self.original_source)
        (self.control / 'verification-original').write_bytes(self.original_verification)
        (self.control / 'workflow-original').write_bytes((workflows / 'checks.yml').read_bytes())
        self.report = self.base / 'report.json'
        self.planned = planned
        self.processes = []

    def start(self, plan=None, keep_going=False):
        for marker in self.control.glob('*.entered.json'):
            marker.unlink()
        (self.control / 'plan.json').write_text(json.dumps(plan or {}))
        arguments = [sys.executable, str(self.root / 'tools' / 'check.py'), '--static-only', '--report', str(self.report)]
        if keep_going:
            arguments.append('--keep-going')
        process = subprocess.Popen(arguments, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=os.name == 'posix')
        self.processes.append(process)
        return process

    def finish(self, process, code):
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == code, f'Expected exit {code}, got {process.returncode}:\n{stdout}\n{stderr}'
        result = self.read()
        return result

    def read(self):
        value = json.loads(self.report.read_text())
        assert_report(value, self.planned)
        return value

    def entered(self, process):
        marker = self.control / (self.planned[0] + '.entered.json')
        deadline = time.monotonic() + 10
        while not marker.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(f'First checker never started:\n{stdout}\n{stderr}')
            if time.monotonic() > deadline:
                raise AssertionError('First checker did not reach its controlled wait')
            time.sleep(0.005)
        return json.loads(marker.read_text())['pid']

    def success(self):
        value = self.finish(self.start(), 0)
        assert value['status'] == 'passed' and value['completed'] and value['passed']
        expected_source = {'index.html': hashlib.sha256((self.root / 'index.html').read_bytes()).hexdigest()}
        assert value['source']['files'] == expected_source
        names = {path.relative_to(self.root).as_posix() for path in (self.root / 'tools').rglob('*.py')}
        names |= {'package.json', 'package-lock.json', 'requirements-dev.txt'}
        names |= {path.relative_to(self.root).as_posix() for pattern in ('*.yml', '*.yaml')
                  for path in (self.root / '.github' / 'workflows').glob(pattern)}
        assert set(value['verification']['files']) == names
        assert value['source'] == value['source_final']
        assert value['verification'] == value['verification_final']
        assert value['finished_at'] is not None and value['current_check'] is None
        return value

    def stop_checker(self, pid):
        if not live(pid):
            return
        commandline = Path(f'/proc/{pid}/cmdline')
        if commandline.is_file() and str(self.root).encode() not in commandline.read_bytes():
            return
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def cleanup(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
        if os.name == 'posix':
            for marker in self.control.glob('*.entered.json'):
                self.stop_checker(json.loads(marker.read_text())['pid'])
        for process in self.processes:
            process.communicate(timeout=10)


def check_signals(fixture, signum):
    previous = fixture.success()
    (fixture.root / 'index.html').write_text('SYNTHETIC_NEW_SOURCE_BEFORE_FIRST_CHECK\n')
    process = fixture.start({'block': [fixture.planned[0]]})
    pid = fixture.entered(process)
    running = fixture.read()
    assert running['run_id'] != previous['run_id']
    assert running['status'] == 'running' and not running['completed'] and not running['passed']
    assert running['current_check']['program'] == fixture.planned[0]
    assert running['source']['files']['index.html'] == hashlib.sha256((fixture.root / 'index.html').read_bytes()).hexdigest()
    assert running['source'] != previous['source'] and running['verification'] == previous['verification']
    assert live(pid), 'The controlled checker was not actually running'
    process.send_signal(signum)
    if signum == signal.SIGKILL:
        process.wait(timeout=10)
        assert process.returncode == -signal.SIGKILL
        after = fixture.read()
        assert after['run_id'] == running['run_id'] and after['status'] == 'running'
        assert not after['completed'] and not after['passed'] and after['finished_at'] is None
        fixture.stop_checker(pid)
        process.communicate(timeout=10)
    else:
        after = fixture.finish(process, 128 + signum)
        assert after['status'] == 'interrupted' and not after['completed'] and not after['passed']
        assert after['finished_at'] is not None and after['error']
        deadline = time.monotonic() + 3
        while live(pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not live(pid), 'The interrupted runner left its checker running'
    print(f'Check runner passed: {signal.Signals(signum).name} cannot leave the previous successful report')


def check_changes(fixture, kind, action, mutation_kind=None):
    target = mutation_kind or kind
    mutations = {fixture.planned[0]: f'{target}-{action}'}
    if action == 'transient':
        mutations[fixture.planned[1]] = f'{target}-restore'
    result = fixture.finish(fixture.start({'mutations': mutations}), 1)
    assert result['status'] == 'failed' and result['completed'] and not result['passed']
    assert len(result['checks']) == len(fixture.planned) and all(item['exit_code'] == 0 for item in result['checks'])
    assert result[f'{kind}_unchanged'] is False
    other = 'verification' if kind == 'source' else 'source'
    assert result[f'{other}_unchanged'] is True
    assert result['integrity_errors'] and result['error']
    if action == 'transient':
        assert result[kind] == result[f'{kind}_final'], 'The restored input should match its initial bytes'
    print(f'Check runner passed: {target} {action} prevents a false successful result')


def check_exit_codes(fixture):
    plan = {'exit_codes': {fixture.planned[0]: 7, fixture.planned[1]: 9}}
    fast = fixture.finish(fixture.start(plan), 7)
    assert fast['status'] == 'failed' and not fast['completed'] and not fast['passed']
    assert [item['exit_code'] for item in fast['checks']] == [7]
    collected = fixture.finish(fixture.start(plan, keep_going=True), 7)
    assert collected['status'] == 'failed' and collected['completed'] and not collected['passed']
    assert [item['exit_code'] for item in collected['checks']] == [7, 9] + [0] * (len(fixture.planned) - 2)
    assert collected['source_unchanged'] is True and collected['verification_unchanged'] is True
    print('Check runner passed: fail-fast and keep-going preserve the first failing exit code')


def check_atomic_reports(fixture):
    for index in range(128):
        target = fixture.root / 'tools' / 'audit' / f'probe_{index:03d}.py'
        target.parent.mkdir(exist_ok=True)
        target.write_text('# controlled identity input\n')
    fixture.success()
    stopped = threading.Event()
    errors = []
    samples = []

    def read_continuously():
        while not stopped.is_set():
            try:
                value = fixture.read()
                samples.append((value['run_id'], value['status']))
            except Exception as error:
                errors.append(repr(error))
                return
            time.sleep(0.001)

    reader = threading.Thread(target=read_continuously)
    reader.start()
    try:
        for _ in range(2):
            process = fixture.start({'delay': 0.02})
            result = fixture.finish(process, 0)
            assert result['status'] == 'passed'
    finally:
        stopped.set()
        reader.join(timeout=5)
    assert not reader.is_alive() and not errors, errors
    assert len(samples) > 10 and len({run_id for run_id, _ in samples}) >= 2
    assert any(status == 'running' for _, status in samples)
    print('Check runner passed: concurrent readers see complete JSON throughout repeated atomic report replacements')


def check_initialization_error(fixture):
    previous = fixture.success()
    (fixture.root / 'tools' / 'build_release.py').write_text('NO_RELEASE_CONTRACT = {}\n')
    result = fixture.finish(fixture.start(), 1)
    assert result['run_id'] != previous['run_id']
    assert result['status'] == 'error' and not result['completed'] and not result['passed']
    assert result['checks'] == [] and result['current_check'] is None
    assert result['finished_at'] is not None and 'DISTRIBUTION_SOURCES' in result['error']
    assert not list(fixture.control.glob('*.entered.json'))
    print('Check runner passed: missing release contract replaces old success with an initialization error')


def run():
    source = RUNNER.read_text()
    planned = static_checks(source)
    with tempfile.TemporaryDirectory(prefix='task-tracer-check-runner-') as folder:
        base = Path(folder)
        fixtures = []

        def fixture(label):
            value = Fixture(base, label, source, planned)
            fixtures.append(value)
            return value

        try:
            if os.name == 'posix':
                for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
                    check_signals(fixture(f'signal-{signum}'), signum)
            else:
                print('Check runner signal cases skipped: POSIX subprocess signals are unsupported on this platform')
            for kind, action in (('source', 'change'), ('verification', 'change'),
                                 ('source', 'transient'), ('verification', 'transient'), ('source', 'delete')):
                check_changes(fixture(f'{kind}-{action}'), kind, action)
            check_changes(fixture('workflow-change'), 'verification', 'change', 'workflow')
            check_exit_codes(fixture('exit-codes'))
            check_atomic_reports(fixture('atomic-reports'))
            check_initialization_error(fixture('initialization'))
        finally:
            for value in fixtures:
                value.cleanup()
    print(f'Check runner lifecycle passed with {len(planned)} static mock programs; no network, Git or browser required')


if __name__ == '__main__':
    run()
