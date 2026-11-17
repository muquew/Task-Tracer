#!/usr/bin/env python3
"""Exercise check-report lifecycle using isolated subprocesses and local files only."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from tests.registry import PROGRAM_PATHS, STATIC_CHECKS
from tests.support.paths import REPO_ROOT


ROOT = REPO_ROOT
RUNNER = ROOT / 'scripts' / 'check.py'
MOCK = r'''from pathlib import Path
import json,os,time
from scripts.project_layout import REPO_ROOT as root
control=root/'control'
name=Path(__file__).name
plan=json.loads((control/'plan.json').read_text())
operation=plan.get('mutations',{}).get(name)
if operation:
    kind,action=operation.split('-',1)
    target=root/{'source':'src/index.html','verification':'tests/support/nested/unused.py','workflow':'.github/workflows/checks.yml','deployment':'vercel.json'}[kind]
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
        for name in ('scripts/__init__.py', 'scripts/runner_support.py', 'scripts/project_layout.py',
                     'tests/__init__.py', 'tests/registry.py'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        (self.root / 'scripts' / 'check.py').write_text(source)
        for name in planned:
            target = self.root / PROGRAM_PATHS[name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(MOCK)
            current = target.parent
            while current != self.root:
                (current / '__init__.py').touch(exist_ok=True)
                current = current.parent
        nested = self.root / 'tests' / 'support' / 'nested'
        nested.mkdir(parents=True)
        (nested / 'unused.py').write_text('# synthetic quality input\n')
        (nested / '验证.py').write_text('# synthetic Unicode identity path\n')
        workflows = self.root / '.github' / 'workflows'
        workflows.mkdir(parents=True)
        (workflows / 'checks.yml').write_text('name: Synthetic checks\n')
        (workflows / 'quality.yaml').write_text('name: Synthetic quality\n')
        (self.root / 'src').mkdir()
        (self.root / 'src/index.html').write_text('SYNTHETIC_SOURCE_ORIGINAL\n')
        (self.root / 'config').mkdir()
        (self.root / 'config/site-files.json').write_text(json.dumps({
            'schema_version': 1, 'application': {'src/index.html': 'index.html'}, 'downloads': {},
        }) + '\n')
        (self.root / 'package.json').write_text('{"version":"1.0.0"}\n')
        (self.root / 'package-lock.json').write_text('{"version":"1.0.0"}\n')
        (self.root / 'vercel.json').write_text('{"headers":[]}\n')
        (self.root / 'requirements-dev.txt').write_text('# no dependencies in this fixture\n')
        self.original_source = (self.root / 'src/index.html').read_bytes()
        self.original_verification = (nested / 'unused.py').read_bytes()
        (self.control / 'source-original').write_bytes(self.original_source)
        (self.control / 'verification-original').write_bytes(self.original_verification)
        (self.control / 'workflow-original').write_bytes((workflows / 'checks.yml').read_bytes())
        (self.control / 'deployment-original').write_bytes((self.root / 'vercel.json').read_bytes())
        self.report = self.base / 'report.json'
        self.planned = planned
        self.processes = []

    def start(self, plan=None, keep_going=False):
        for marker in self.control.glob('*.entered.json'):
            marker.unlink()
        (self.control / 'plan.json').write_text(json.dumps(plan or {}))
        arguments = [sys.executable, '-m', 'scripts.check', '--static-only', '--report', str(self.report)]
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
        expected_source = {name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                           for name in ('src/index.html', 'config/site-files.json')}
        assert value['source']['files'] == expected_source
        names = {path.relative_to(self.root).as_posix()
                 for folder in ('scripts', 'tests', 'src', 'config')
                 for path in (self.root / folder).rglob('*')
                 if path.is_file() and path.suffix in {'.py', '.js', '.mjs', '.json', '.html', '.css'}
                 and '__pycache__' not in path.parts}
        names |= {'package.json', 'package-lock.json', 'requirements-dev.txt', 'vercel.json'}
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
        directory = Path(f'/proc/{pid}/cwd')
        if directory.exists() and directory.resolve() != self.root.resolve():
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
    (fixture.root / 'src/index.html').write_text('SYNTHETIC_NEW_SOURCE_BEFORE_FIRST_CHECK\n')
    process = fixture.start({'block': [fixture.planned[0]]})
    pid = fixture.entered(process)
    running = fixture.read()
    assert running['run_id'] != previous['run_id']
    assert running['status'] == 'running' and not running['completed'] and not running['passed']
    assert running['current_check']['program'] == fixture.planned[0]
    assert running['source']['files']['src/index.html'] == hashlib.sha256((fixture.root / 'src/index.html').read_bytes()).hexdigest()
    assert running['source'] != previous['source'] and running['verification'] != previous['verification']
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
    if kind == 'source':
        assert result['verification_unchanged'] is False, 'Source inputs also belong to the verification identity'
    else:
        assert result['source_unchanged'] is True, 'Test-only changes must preserve the product source identity'
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
        target = fixture.root / 'tests' / 'audit' / f'probe_{index:03d}.py'
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
    (fixture.root / 'config/site-files.json').write_text(json.dumps({
        'schema_version': 1, 'application': {}, 'downloads': {},
    }))
    result = fixture.finish(fixture.start(), 1)
    assert result['run_id'] != previous['run_id']
    assert result['status'] == 'error' and not result['completed'] and not result['passed']
    assert result['checks'] == [] and result['current_check'] is None
    assert result['finished_at'] is not None and 'application' in result['error']
    assert not list(fixture.control.glob('*.entered.json'))
    print('Check runner passed: missing site-file contract replaces old success with an initialization error')


def check_verification_symlink(fixture):
    previous = fixture.success()
    outside = fixture.base / 'outside-verification'
    outside.mkdir()
    (outside / 'hidden.py').write_text('# synthetic external verification input\n')
    (fixture.root / 'tests/support/linked').symlink_to(outside, target_is_directory=True)
    result = fixture.finish(fixture.start(), 1)
    assert result['run_id'] != previous['run_id']
    assert result['status'] == 'error' and not result['completed'] and not result['passed']
    assert result['checks'] == [] and result['current_check'] is None
    assert result['finished_at'] is not None
    assert 'symbolic link: tests/support/linked' in result['error'], result['error']
    assert not list(fixture.control.glob('*.entered.json'))
    print('Check runner passed: an external verification directory cannot be silently omitted from a successful identity')


def check_ci_report_safety(base):
    from scripts import ci_report as ci

    private_text = 'SYNTHETIC_PRIVATE_TRACE'
    source = f'def main():\n    raise AssertionError("{private_text}")\n\nmain()\n'.encode()
    registry = (ROOT / 'tests/registry.py').read_bytes()

    def digest(data):
        return hashlib.sha256(data).hexdigest()

    def identity(files):
        serialized = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        return {'files': files, 'sha256': digest(serialized)}

    class ReportFixture:
        def __init__(self, label):
            self.root = base / label
            self.root.mkdir()
            self.program = ci.PROGRAMS[0]
            self.name = ci.PROGRAM_PATHS[self.program]
            self.source = self.root / self.name
            self.source.parent.mkdir(parents=True)
            self.source.write_bytes(source)
            (self.root / 'tests/registry.py').write_bytes(registry)
            (self.root / 'src').mkdir()
            html = b'SYNTHETIC_CI_SOURCE\n'
            (self.root / 'src/index.html').write_bytes(html)
            self.report_path = Path('dist/browser-matrix-chromium.json')
            run_id = str(uuid.uuid4())
            log_root = f'browser-matrix-chromium-logs/{run_id}'
            self.log_path = Path('dist') / log_root / f'chromium-{self.program[:-3]}.log'
            checks = [{'browser': 'chromium', 'program': program, 'status': 'passed',
                       'exit_code': 0, 'duration_seconds': 0.01} for program in ci.PROGRAMS]
            self.check = checks[0]
            self.check.update(status='failed', exit_code=1)
            self.report = {
                'schema_version': 1, 'run_id': run_id, 'status': 'failed',
                'log_directory': log_root, 'completed': True, 'passed': False,
                'planned_checks': [{'browser': 'chromium', 'program': program} for program in ci.PROGRAMS],
                'scope': {'browsers': ['chromium'], 'programs': list(ci.PROGRAMS),
                          'registry_program_count': len(ci.PROGRAMS), 'all_registered_programs': True},
                'source': identity({'src/index.html': digest(html)}),
                'verification': identity({'tests/registry.py': digest(registry), self.name: digest(source)}),
                'source_unchanged': True, 'verification_unchanged': True, 'integrity_errors': [], 'checks': checks,
            }
            for name in ('source', 'verification'):
                self.report[f'{name}_final'] = deepcopy(self.report[name])
            process = subprocess.run([sys.executable, '-B', str(self.source)], cwd=self.root,
                                     capture_output=True)
            assert process.returncode == 1 and b'Traceback (most recent call last):' in process.stderr
            self.write_log(process.stderr)

        def save(self):
            path = self.root / self.report_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.report) + '\n')

        def write_log(self, data):
            data = data.encode() if isinstance(data, str) else data
            path = self.root / self.log_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.check['log'] = {'relative_path': self.log_path.relative_to('dist').as_posix(),
                                 'bytes': len(data), 'sha256': digest(data)}
            self.save()

        def frame(self, line, owner, path=None):
            self.write_log(f'Traceback (most recent call last):\n'
                           f'  File "{path or self.name}", line {line}, in {owner}\n'
                           f'AssertionError: {private_text}\n')

        def sign(self, name, value):
            files = dict(self.report['verification']['files'])
            files[name] = value
            self.report['verification'] = identity(files)
            self.report['verification_final'] = deepcopy(self.report['verification'])
            self.save()

        def link(self, path):
            outside = base / f'{self.root.name}-outside'
            path.rename(outside)
            path.symlink_to(outside, target_is_directory=outside.is_dir())

        def trace(self, path=None):
            return ci.get_safe_trace(self.root, path or self.report_path, self.report, self.check)

    fixture = ReportFixture('ci-valid')
    expected = {'path': fixture.name, 'basename': Path(fixture.name).name, 'line': 2,
                'function': 'main', 'exception_class': 'AssertionError'}
    assert fixture.trace() == expected, 'A real, signed Python traceback must expose its bounded source location'
    summary = ci.summarize_browser(fixture.root, 'chromium')
    rendered = '\n'.join(summary.console) + summary.markdown
    assert summary.status == 'failed' and summary.exit_code == 1
    assert f'location={fixture.name}:2:main exception=AssertionError' in rendered
    assert private_text not in rendered, 'CI summaries must not expose raw traceback messages or source text'
    for name in ('source', 'verification'):
        assert fixture.report[name]['sha256'] in summary.markdown

    common = {key: deepcopy(fixture.report[key]) for key in (
        'source', 'verification', 'source_final', 'verification_final',
        'source_unchanged', 'verification_unchanged', 'integrity_errors')}
    checks_report = {**common, 'schema_version': 2, 'status': 'passed', 'completed': True, 'passed': True,
                     'planned_checks': list(ci.CHECKS),
                     'checks': [{'program': program, 'exit_code': 0, 'duration_seconds': 0.01} for program in ci.CHECKS]}
    checks_path = fixture.root / 'dist/check-results.json'
    checks_path.write_text(json.dumps(checks_report))
    assert ci.summarize_checks(fixture.root).exit_code == 0
    checks_report['planned_checks'] = list(ci.CHECKS[:-1])
    checks_path.write_text(json.dumps(checks_report))
    summary = ci.summarize_checks(fixture.root)
    assert summary.status == 'invalid_report' and summary.exit_code == 1
    assert all(f'{program} status=' in '\n'.join(summary.console) for program in ci.CHECKS)

    fixture.report.update(status='passed', passed=True)
    fixture.report['checks'][0].update(status='passed', exit_code=0)
    fixture.save()
    assert ci.summarize_browser(fixture.root, 'chromium').exit_code == 0
    original = deepcopy(fixture.report)
    for label in ('partial-scope', 'changed-input', 'invalid-envelope', 'unknown-program'):
        fixture.report = deepcopy(original)
        if label == 'partial-scope':
            fixture.report['planned_checks'] = fixture.report['planned_checks'][:1]
            fixture.report['scope']['programs'] = list(ci.PROGRAMS[:1])
            fixture.report['checks'] = fixture.report['checks'][:1]
        elif label == 'changed-input':
            fixture.report['source_unchanged'] = False
        elif label == 'invalid-envelope':
            fixture.report['source']['sha256'] = '0' * 64
            fixture.report['source_final'] = deepcopy(fixture.report['source'])
        else:
            fixture.report['checks'][0]['program'] = '../unregistered.py'
        fixture.report.update(status='passed', passed=True)
        fixture.save()
        summary = ci.summarize_browser(fixture.root, 'chromium')
        assert summary.exit_code == 1, label
        assert summary.status == ('incomplete' if label == 'changed-input' else 'invalid_report'), (label, summary.status)
        rendered = '\n'.join(summary.console) + summary.markdown
        assert all(f'{program} status=' in rendered for program in ci.PROGRAMS), label
        assert '../unregistered.py' not in rendered and private_text not in rendered, label

    attacks = (
        ('source-traversal', lambda f: f.frame(2, 'main', f'tests/browser/../browser/{f.program}')),
        ('report-traversal', lambda f: None),
        ('log-traversal', lambda f: (f.check['log'].update(relative_path='../private.log'), f.save())),
        ('source-symlink', lambda f: f.link(f.source)),
        ('log-directory-symlink', lambda f: f.link((f.root / f.log_path).parent)),
        ('report-symlink', lambda f: f.link(f.root / f.report_path)),
        ('forged-source-hash', lambda f: f.sign(f.name, '0' * 64)),
        ('forged-registry', lambda f: ((f.root / 'tests/registry.py').write_bytes(registry + b'\n'),
                                     f.sign('tests/registry.py', digest(registry + b'\n')))),
        ('forged-owner', lambda f: f.frame(2, 'invented_owner')),
        ('non-ast-line', lambda f: f.frame(3, 'main')),
        ('report-object-mismatch', lambda f: f.report.update(unwritten=True)),
    )
    for label, mutate in attacks:
        fixture = ReportFixture(f'ci-{label}')
        mutate(fixture)
        path = Path('dist/../dist/browser-matrix-chromium.json') if label == 'report-traversal' else None
        assert fixture.trace(path) is None, f'Unsafe CI trace accepted: {label}'

    for label, implementation in (
        ('lambda', b'def main():\n    call = lambda: (\n        1 / 0\n    )\n    call()\n'),
        ('genexpr', b'def main():\n    values = (\n        1 / value\n        for value in [0]\n    )\n    next(values)\n'),
    ):
        fixture = ReportFixture(f'ci-owner-{label}')
        fixture.source.write_bytes(implementation)
        fixture.sign(fixture.name, digest(implementation))
        fixture.frame(3, 'main')
        assert fixture.trace() is None, f'A {label} executable line must not be attributed to its enclosing function'
    print('CI reports passed: full fixed registries, input identities, private-safe real trace, bounded paths and AST/compiled frame ownership')


def run():
    source = RUNNER.read_text()
    planned = list(STATIC_CHECKS)
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
            check_changes(fixture('deployment-change'), 'verification', 'change', 'deployment')
            check_exit_codes(fixture('exit-codes'))
            check_atomic_reports(fixture('atomic-reports'))
            check_initialization_error(fixture('initialization'))
            check_verification_symlink(fixture('verification-symlink'))
            check_ci_report_safety(base)
        finally:
            for value in fixtures:
                value.cleanup()
    print(f'Check runner lifecycle passed with {len(planned)} static mock programs; no network, Git or browser required')


if __name__ == '__main__':
    run()
