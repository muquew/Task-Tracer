"""Production-only 4.8.6 checked-subtask visibility acceptance.

Preparation is inert. Execute with --start only after the parent confirms deployment.
The repository and its frozen verification inputs are read, never modified.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

sys.dont_write_bytecode = True
ROOT = Path('/workspace/Task-Tracer')
SITE = 'https://todo.muquew.com/'
FREEZE_PATH = Path('/tmp/task-tracer-4.8.6-freeze.json')
OUTPUT_ROOT = ROOT / 'docs/acceptance/2026-10-25/production-visibility-4.8.6'
EXECUTABLE = Path('/usr/bin/chromium')
sys.path.insert(0, str(ROOT / 'tools'))

from accessibility_i18n_audit import audit_subtask_checkbox_visibility
from check import atomic_report, source_identity, verification_identity
from smoke_playwright import add_task, get_task_records, task_locator, wait_for_app_ready
from upgrade_playwright import app_version
from playwright.sync_api import expect, sync_playwright


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Tee:
    def __init__(self, console, logfile):
        self.console, self.logfile = console, logfile

    def write(self, value):
        self.console.write(value)
        self.logfile.write(value)
        return len(value)

    def flush(self):
        self.console.flush()
        self.logfile.flush()


def verify(freeze: dict) -> None:
    assert source_identity() == freeze['source'], 'Frozen source bytes changed'
    assert verification_identity() == freeze['verification'], 'Frozen verification inputs changed'


def record_final_identity(state: dict, freeze: dict) -> None:
    state['source_final'] = source_identity()
    state['verification_final'] = verification_identity()
    state['source_unchanged'] = state['source'] == state['source_final'] == freeze['source']
    state['verification_unchanged'] = state['verification'] == state['verification_final'] == freeze['verification']
    if not state['source_unchanged'] or not state['verification_unchanged']:
        state.update(status='failed', passed=False)
        state['error'] = state.get('error') or 'Frozen source or verification inputs changed'


def context_audit(playwright, viewport: dict, directory: Path, freeze: dict, run_id: str) -> dict:
    label = f"chromium-{viewport['width']}"
    state = {
        'schema_version': 1, 'run_id': run_id, 'label': label,
        'status': 'initializing', 'completed': False, 'passed': False,
        'started_at': now(), 'finished_at': None, 'site': SITE,
        'engine': 'chromium', 'browser_version': None, 'loaded_app_version': None,
        'viewport': viewport, 'fresh_synthetic_context': True,
        'persistent_profile': False, 'storage_state_supplied': False,
        'proxy_source': 'HTTPS_PROXY', 'proxy_inherited': True,
        'ignore_https_errors': False, 'bypass_csp': False,
        'source': source_identity(), 'verification': verification_identity(),
        'source_final': None, 'verification_final': None,
        'source_unchanged': False, 'verification_unchanged': False,
        'page_errors': [], 'console_errors': [], 'request_failures': [],
        'observations': [], 'online_html': None, 'checks': [],
        'context_closed': False, 'browser_closed': False,
        'error': None, 'traceback': None,
    }
    directory.mkdir(parents=False, exist_ok=False)
    path = directory / 'result.json'
    atomic_report(path, state)
    browser = context = page = None
    started = time.monotonic()
    try:
        verify(freeze)
        proxy = os.environ.get('HTTPS_PROXY')
        assert proxy, 'HTTPS_PROXY is required; direct network fallback is forbidden'
        assert EXECUTABLE.is_file(), 'System Chromium executable is missing'
        state['status'] = 'running'
        atomic_report(path, state)
        browser = playwright.chromium.launch(
            executable_path=str(EXECUTABLE), headless=True, timeout=30000,
            proxy={'server': proxy, 'bypass': '127.0.0.1,localhost'})
        state['browser_version'] = browser.version
        assert browser.version.split('.')[0] == '154', f'Expected system Chromium 154, got {browser.version}'
        context = browser.new_context(
            locale='en-US', viewport=viewport, reduced_motion='reduce',
            ignore_https_errors=False, bypass_csp=False, service_workers='allow')
        page = context.new_page()
        page.on('pageerror', lambda error: state['page_errors'].append(str(error)))
        page.on('console', lambda message: state['console_errors'].append(message.text) if message.type == 'error' else None)
        page.on('requestfailed', lambda request: state['request_failures'].append({'url': request.url, 'failure': request.failure}))
        response = page.goto(SITE, wait_until='domcontentloaded', timeout=45000)
        assert response is not None, 'Navigation returned no HTML response'
        body = response.body()
        (directory / 'online-index.html').write_bytes(body)
        state['online_html'] = {
            'url': response.url, 'status': response.status,
            'from_service_worker': response.from_service_worker,
            'bytes': len(body), 'sha256': sha256(body),
            'expected_sha256': freeze['source']['files']['index.html'],
            'headers': {name: response.headers[name] for name in (
                'content-type', 'content-security-policy', 'cache-control', 'etag',
                'x-vercel-cache', 'x-vercel-id') if name in response.headers},
        }
        atomic_report(path, state)
        assert response.status == 200 and response.url == SITE, state['online_html']
        assert not response.from_service_worker, 'Fresh context unexpectedly used a service-worker response'
        assert sha256(body) == freeze['source']['files']['index.html'], 'Production HTML differs from the frozen 4.8.6 source'
        wait_for_app_ready(page)
        state['loaded_app_version'] = app_version(page)
        assert state['loaded_app_version'] == freeze['app_version'] == '4.8.6'
        expect(page.locator('.task-item')).to_have_count(0)
        assert get_task_records(page) == [], 'Fresh synthetic context contains existing task records'
        state['checks'].append('Fresh HTTPS network response SHA and loaded application version match frozen 4.8.6')
        task_name = f'PROD-VISIBILITY {label} {run_id}'
        add_task(page, task_name, no_deadline=True, project='Production Acceptance',
                 tags=['synthetic', 'visibility'], subtasks=['Verify checked-state visibility'])
        expect(page.locator('.task-item')).to_have_count(1)
        expect(task_locator(page, task_name).locator('.subtask-checkbox')).to_have_count(1)
        audit_subtask_checkbox_visibility(page, label, state['observations'], directory)
        expected_states = {(theme, interaction) for theme in ('light', 'dark')
                           for interaction in ('resting', 'hover', 'keyboard-focus')}
        observed_states = {(item['theme'], item['interaction']) for item in state['observations']}
        assert len(state['observations']) == 6 and observed_states == expected_states
        records = get_task_records(page)
        assert len(records) == 1 and records[0]['name'] == task_name
        assert len(records[0]['subtasks']) == 1 and records[0]['subtasks'][0]['completed'] is False
        expect(task_locator(page, task_name).locator('.subtask-checkbox')).not_to_be_checked()
        assert not state['page_errors'], state['page_errors']
        assert not state['console_errors'], state['console_errors']
        state['checks'].append('Original add_task and visibility audit: light/dark, resting/hover/keyboard focus, native checkbox semantics, Space completion and reversal, mark/fill and state contrast >= 3:1')
        state['final_records'] = records
        state.update(status='passed', passed=True)
        print(json.dumps({'context': label, 'status': 'passed', 'browser_version': browser.version,
                          'app_version': state['loaded_app_version'], 'observations': len(state['observations'])}, ensure_ascii=False), flush=True)
    except BaseException as error:
        state.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        print(state['traceback'], flush=True)
        if page is not None:
            try:
                page.screenshot(path=directory / 'failure.png', full_page=True, timeout=5000)
                state['failure_screenshot'] = 'failure.png'
            except BaseException as capture_error:
                state['failure_screenshot_error'] = repr(capture_error)
    finally:
        for name, resource in (('context', context), ('browser', browser)):
            if resource is not None:
                try:
                    resource.close()
                    state[f'{name}_closed'] = True
                except BaseException as close_error:
                    state.update(status='failed', passed=False)
                    state[f'{name}_close_error'] = repr(close_error)
                    state['error'] = state['error'] or f'{name} cleanup failed'
        record_final_identity(state, freeze)
        state.update(completed=True, finished_at=now(), duration_seconds=round(time.monotonic() - started, 3))
        atomic_report(path, state)
    return state


def run(output: Path, freeze: dict, freeze_raw: bytes, run_id: str) -> int:
    planned = [{'width': 1280, 'height': 800}, {'width': 390, 'height': 844}]
    report = {
        'schema_version': 1, 'run_id': run_id, 'site': SITE, 'app_version': '4.8.6',
        'started_at': now(), 'finished_at': None,
        'status': 'initializing', 'completed': False, 'passed': False,
        'freeze_path': str(FREEZE_PATH), 'freeze_sha256': sha256(freeze_raw),
        'observed_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source': source_identity(), 'verification': verification_identity(),
        'source_final': None, 'verification_final': None,
        'source_unchanged': False, 'verification_unchanged': False,
        'planned': planned, 'checks': [], 'current': None, 'unexecuted': planned[:],
        'stdout_file': 'runner-output.log', 'inventory_file': 'evidence-sha256.json',
        'error': None,
        'scope': 'Actual HTTPS production HTML, original synthetic task helper and original checked-subtask visibility regression; 2 fresh Chromium contexts, 12 light/dark interaction observations and screenshots.',
        'inspection': {
            'performed_by_runner': False,
            'required_representatives': [f'chromium-{width}/{name}.png' for width in (1280, 390)
                                         for name in ('light-resting', 'dark-keyboard-focus')],
            'note': 'After completion, a human/agent must actually view these four images and record a separate inspection. The other eight screenshots are automated assertion evidence only.',
        },
        'limitations': [
            'Cloud Linux Chromium at desktop/narrow viewports is not acceptance on physical mobile devices or Safari/iOS.',
            'This focused run covers the changed checked-subtask visual state, not a full WCAG or full 58-program suite rerun.',
            'The unchanged unchecked-border contrast is outside this focused patch and is not claimed compliant.',
        ],
    }
    path = output / 'report.json'
    atomic_report(path, report)
    print('EVIDENCE_DIRECTORY=' + str(output), flush=True)
    try:
        assert freeze['app_version'] == '4.8.6'
        verify(freeze)
        with sync_playwright() as playwright:
            for viewport in planned:
                verify(freeze)
                report.update(status='running', current=viewport)
                atomic_report(path, report)
                directory = output / f"chromium-{viewport['width']}"
                result = context_audit(playwright, viewport, directory, freeze, run_id)
                report['checks'].append(result)
                report['unexecuted'] = planned[len(report['checks']):]
                atomic_report(path, report)
                if not result['passed']:
                    raise RuntimeError(f'First failure preserved in {directory / "result.json"}')
        assert len(report['checks']) == 2
        assert sum(len(item['observations']) for item in report['checks']) == 12
        verify(freeze)
        assert FREEZE_PATH.read_bytes() == freeze_raw, 'Freeze manifest changed during run'
        report.update(status='passed', passed=True)
    except BaseException as error:
        report.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        print(report['traceback'], flush=True)
    finally:
        record_final_identity(report, freeze)
        if FREEZE_PATH.read_bytes() != freeze_raw:
            report.update(status='failed', passed=False, error=report['error'] or 'Freeze manifest changed during run')
        report.update(completed=True, current=None, finished_at=now())
        atomic_report(path, report)
        print(json.dumps({'report': str(path), 'status': report['status'], 'passed': report['passed'],
                          'contexts': len(report['checks']),
                          'observations': sum(len(item['observations']) for item in report['checks']),
                          'source_unchanged': report['source_unchanged'],
                          'verification_unchanged': report['verification_unchanged']}, ensure_ascii=False), flush=True)
    return 0 if report['passed'] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true', help='Execute only after the parent confirms 4.8.6 deployment')
    args = parser.parse_args()
    if not args.start:
        parser.error('Preparation is inert; --start is required after deployment confirmation')
    freeze_raw = FREEZE_PATH.read_bytes()
    freeze = json.loads(freeze_raw)
    run_id = str(uuid.uuid4())
    output = OUTPUT_ROOT / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / 'runner.py').write_bytes(Path(__file__).read_bytes())
    (output / 'freeze.json').write_bytes(freeze_raw)
    with (output / 'runner-output.log').open('x', encoding='utf-8', buffering=1) as stream:
        with redirect_stdout(Tee(sys.stdout, stream)), redirect_stderr(Tee(sys.stderr, stream)):
            code = run(output, freeze, freeze_raw, run_id)
    inventory = {}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            raw = path.read_bytes()
            inventory[path.relative_to(output).as_posix()] = {'bytes': len(raw), 'sha256': sha256(raw)}
    atomic_report(output / 'evidence-sha256.json', inventory)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
