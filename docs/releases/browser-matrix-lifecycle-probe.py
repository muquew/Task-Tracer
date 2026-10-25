from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path('/workspace/Task-Tracer')
RESULTS = []


def fixture(folder: Path, mode: str):
    tools = folder / 'tools'
    tools.mkdir()
    for name in ('browser_matrix.py', 'check.py'):
        shutil.copyfile(ROOT / 'tools' / name, tools / name)
    (tools / 'build_release.py').write_text("DISTRIBUTION_SOURCES = {'index.html': 'index.html'}\n")
    (folder / 'index.html').write_text('<title>Isolated lifecycle fixture only</title>')
    for name in ('package.json', 'package-lock.json'):
        (folder / name).write_text('{}\n')
    (folder / 'requirements-dev.txt').write_text('')
    (tools / 'smoke_playwright.py').write_text('def browser_launch_options():\n    return {}\n')
    playwright = tools / 'playwright'
    playwright.mkdir()
    (playwright / '__init__.py').write_text('')
    (playwright / 'sync_api.py').write_text('''
class Browser:
    version = 'fixture-version-not-browser-evidence'
    def close(self): pass
class Launcher:
    def launch(self, **options): return Browser()
class Playwright:
    chromium = firefox = webkit = Launcher()
    def __enter__(self): return self
    def __exit__(self, *args): pass
def sync_playwright(): return Playwright()
''')
    if mode == 'nonzero':
        (tools / 'compatibility_playwright.py').write_text("print('isolated program exit 7', flush=True)\nraise SystemExit(7)\n")
        (tools / 'csv_playwright.py').write_text("print('isolated program exit 9', flush=True)\nraise SystemExit(9)\n")
    else:
        (tools / 'compatibility_playwright.py').write_text('''
import json, os, subprocess, sys, time
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(45)'])
Path(os.environ['MATRIX_FIXTURE_PID_FILE']).write_text(json.dumps({'program': os.getpid(), 'descendant': child.pid}))
print('isolated real subprocess tree is ready', flush=True)
time.sleep(45)
''')
    report = folder / 'report.json'
    report.write_text(json.dumps({'run_id': 'old-success', 'status': 'passed', 'completed': True, 'passed': True}))
    return tools, report


def live(pid: int):
    try:
        status = Path(f'/proc/{pid}/stat').read_text().split()
        return status[2] != 'Z'
    except FileNotFoundError:
        return False


with tempfile.TemporaryDirectory(prefix='task-tracer-matrix-lifecycle-') as folder_name:
    base = Path(folder_name)
    failure = base / 'nonzero'
    failure.mkdir()
    tools, report = fixture(failure, 'nonzero')
    proc = subprocess.run([sys.executable, str(tools / 'browser_matrix.py'), '--browser', 'chromium',
                           '--program', 'compatibility_playwright.py', '--program', 'csv_playwright.py',
                           '--keep-going', '--report', str(report)], capture_output=True, text=True,
                          timeout=15, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    data = json.loads(report.read_text())
    assert proc.returncode == 7, proc
    assert data['run_id'] != 'old-success'
    assert data['status'] == 'failed' and data['completed'] and not data['passed']
    assert [item['exit_code'] for item in data['checks']] == [7, 9]
    assert not data['unexecuted_checks'] and data['source_unchanged'] and data['verification_unchanged']
    RESULTS.append({'case': 'actual child exit 7/9, keep-going and old success replaced', 'passed': True})

    for signum in (signal.SIGINT, signal.SIGTERM):
        folder = base / signum.name
        folder.mkdir()
        tools, report = fixture(folder, 'block')
        pid_file = folder / 'pids.json'
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'MATRIX_FIXTURE_PID_FILE': str(pid_file)}
        proc = subprocess.Popen([sys.executable, str(tools / 'browser_matrix.py'), '--browser', 'chromium',
                                 '--program', 'compatibility_playwright.py', '--report', str(report)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        pids = None
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if pid_file.exists():
                    try:
                        pids = json.loads(pid_file.read_text())
                        data = json.loads(report.read_text())
                    except json.JSONDecodeError:
                        time.sleep(.01)
                        continue
                    if data.get('current_check', {}).get('program') == 'compatibility_playwright.py':
                        break
                if proc.poll() is not None:
                    raise AssertionError(proc.communicate())
                time.sleep(.01)
            else:
                raise AssertionError('Real subprocess fixture did not start')
            assert data['run_id'] != 'old-success'
            assert data['status'] == 'running' and not data['completed'] and not data['passed']
            assert all(live(pid) for pid in pids.values())
            proc.send_signal(signum)
            stdout, stderr = proc.communicate(timeout=10)
            assert proc.returncode == 128 + signum, (proc.returncode, stdout, stderr)
            data = json.loads(report.read_text())
            assert data['status'] == 'interrupted' and not data['completed'] and not data['passed']
            assert len(data['unexecuted_checks']) == 1 and not data['checks']
            assert data['source_unchanged'] and data['verification_unchanged']
            deadline = time.monotonic() + 3
            while any(live(pid) for pid in pids.values()) and time.monotonic() < deadline:
                time.sleep(.01)
            assert not any(live(pid) for pid in pids.values()), pids
            RESULTS.append({'case': f'{signum.name}: exit {128 + signum}, incomplete report and real descendant group cleaned', 'passed': True})
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)
            if pids:
                for pid in pids.values():
                    if live(pid):
                        os.kill(pid, signal.SIGKILL)

    broken = base / 'initialization-error'
    broken.mkdir()
    tools, report = fixture(broken, 'nonzero')
    (tools / 'build_release.py').unlink()
    proc = subprocess.run([sys.executable, str(tools / 'browser_matrix.py'), '--browser', 'chromium',
                           '--group', 'core', '--report', str(report)], capture_output=True, text=True,
                          timeout=10, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    data = json.loads(report.read_text())
    assert proc.returncode == 1
    assert data['run_id'] != 'old-success' and data['status'] == 'error'
    assert not data['passed'] and not data['completed'] and data['error']
    RESULTS.append({'case': 'initialization error replaces old successful report', 'passed': True})

result = {'scope': 'Isolated stdlib driver lifecycle fixtures; fake engine probe is not browser/application evidence',
          'passed': True, 'cases': RESULTS}
Path('/tmp/task-tracer-matrix-lifecycle-probe.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
