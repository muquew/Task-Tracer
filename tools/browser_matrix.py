#!/usr/bin/env python3
"""Run the explicit cross-browser workflow registry with retained, atomic evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from check import (
    REPO_ROOT, RunInterrupted, atomic_report, source_identity, stop_child,
    timestamp, verification_identity,
)


BROWSERS = ('chromium', 'firefox', 'webkit')
PROGRAMS = (
    'compatibility_playwright.py',
    'appearance_preferences_playwright.py',
    'settings_navigation_playwright.py',
    'csv_playwright.py',
    'backup_freshness_playwright.py',
    'backup_reminder_priority_playwright.py',
    'project_scope_playwright.py',
    'task_draft_playwright.py',
    'quick_add_recovery_playwright.py',
    'quick_add_date_playwright.py',
    'imported_text_edit_playwright.py',
    'imported_reminder_edit_playwright.py',
    'repeat_lineage_playwright.py',
    'repeat_delete_playwright.py',
    'repeat_merge_playwright.py',
    'dialog_lifecycle_playwright.py',
    'onboarding_playwright.py',
    'help_playwright.py',
    'ime_input_playwright.py',
    'batch_selection_playwright.py',
    'workspace_failure_playwright.py',
    'calendar_performance_playwright.py',
    'calendar_navigation_playwright.py',
    'calendar_timezone_playwright.py',
    'recovery_management_playwright.py',
    'views_portability_playwright.py',
    'views_delete_playwright.py',
    'timezone_playwright.py',
    'dst_wall_time_playwright.py',
    'foreign_wall_time_playwright.py',
    'recurrence_timezone_playwright.py',
    'time_refresh_playwright.py',
    'stats_scope_playwright.py',
)
GROUPS = {
    'core': ('compatibility_playwright.py',),
    'appearance': ('appearance_preferences_playwright.py', 'settings_navigation_playwright.py'),
    'capture': (
        'task_draft_playwright.py', 'quick_add_recovery_playwright.py',
        'quick_add_date_playwright.py', 'imported_text_edit_playwright.py',
        'imported_reminder_edit_playwright.py', 'dialog_lifecycle_playwright.py',
        'onboarding_playwright.py', 'help_playwright.py', 'ime_input_playwright.py',
    ),
    'data': (
        'csv_playwright.py', 'backup_freshness_playwright.py',
        'backup_reminder_priority_playwright.py', 'project_scope_playwright.py',
        'repeat_lineage_playwright.py', 'repeat_delete_playwright.py',
        'repeat_merge_playwright.py',
        'batch_selection_playwright.py', 'recovery_management_playwright.py',
        'workspace_failure_playwright.py',
        'views_portability_playwright.py', 'views_delete_playwright.py',
    ),
    'calendar': (
        'calendar_performance_playwright.py', 'calendar_navigation_playwright.py',
        'calendar_timezone_playwright.py',
    ),
    'dates': (
        'timezone_playwright.py', 'dst_wall_time_playwright.py',
        'foreign_wall_time_playwright.py', 'recurrence_timezone_playwright.py',
        'time_refresh_playwright.py', 'stats_scope_playwright.py',
    ),
    'all': PROGRAMS,
}
CORE_VIEWPORTS = [{'width': 1280, 'height': 800}, {'width': 390, 'height': 844}]


def probe_browser(engine: str) -> int:
    from playwright.sync_api import sync_playwright
    from smoke_playwright import browser_launch_options

    with sync_playwright() as playwright:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        options['timeout'] = 30000
        browser = getattr(playwright, engine).launch(**options)
        try:
            print(json.dumps({'browser': engine, 'version': browser.version}), flush=True)
        finally:
            browser.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='append', choices=(*BROWSERS, 'all'),
                        help='Repeat to select engines; default: all three')
    parser.add_argument('--group', action='append', choices=tuple(GROUPS),
                        help='Repeat to include groups; default: all registered programs')
    parser.add_argument('--program', action='append', choices=PROGRAMS,
                        help='Include a registered program; selections are unioned with groups')
    parser.add_argument('--report', type=Path, default=REPO_ROOT / 'dist/browser-matrix.json')
    parser.add_argument('--keep-going', action='store_true',
                        help='Continue after failed programs or an unavailable engine')
    parser.add_argument('--list', action='store_true', help='List selected scope without running browsers')
    parser.add_argument('--probe-browser', choices=BROWSERS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.probe_browser:
        return probe_browser(args.probe_browser)

    browsers = list(dict.fromkeys(engine for value in (args.browser or ['all'])
                                 for engine in (BROWSERS if value == 'all' else (value,))))
    selected = set(args.program or [])
    for group in args.group or ([] if args.program else ['all']):
        selected.update(GROUPS[group])
    programs = [program for program in PROGRAMS if program in selected]
    planned = [{'browser': browser, 'program': program} for browser in browsers for program in programs]
    scope = {
        'browsers': browsers, 'programs': programs, 'registry_program_count': len(PROGRAMS),
        'all_registered_programs': programs == list(PROGRAMS),
        'all_engines': set(browsers) == set(BROWSERS),
        'core_program': 'compatibility_playwright.py', 'core_viewports': CORE_VIEWPORTS,
        'other_program_viewports': 'Defined by each program; not all special-purpose programs exercise both core viewports.',
        'device_scope': 'Linux desktop browser engines and synthetic viewports; not real mobile devices or Safari/iOS.',
        'coverage_exceptions': [
            {'browser': browser, 'program': program, 'case': 'Live device-timezone override',
             'status': 'not_run', 'reason': 'Requires Chromium CDP; this engine runs the program\'s fixed-zone cases.'}
            for browser in browsers if browser != 'chromium'
            for program in ('timezone_playwright.py', 'calendar_timezone_playwright.py') if program in programs
        ],
    }
    if args.list:
        print(json.dumps({'scope': scope, 'planned_checks': planned}, indent=2))
        return 0

    run_id = str(uuid.uuid4())
    report_path = args.report.resolve()
    log_dir = report_path.parent / f'{report_path.stem}-logs' / run_id
    report = {
        'schema_version': 1, 'run_id': run_id, 'status': 'initializing',
        'started_at': timestamp(), 'updated_at': None, 'finished_at': None,
        'scope': scope, 'planned_checks': planned, 'current_check': None,
        'log_directory': log_dir.relative_to(report_path.parent).as_posix(),
        'browsers': {engine: {'status': 'not_run', 'version': None} for engine in browsers},
        'source': None, 'verification': None, 'source_final': None, 'verification_final': None,
        'source_unchanged': None, 'verification_unchanged': None, 'integrity_errors': [],
        'checks': [], 'unexecuted_checks': planned.copy(),
        'error': None, 'completed': False, 'passed': False,
    }
    child = None
    previous_handlers = {}
    first_failure = 0
    child_env = os.environ.copy()
    child_env['PYTHONDONTWRITEBYTECODE'] = '1'
    child_env['PYTHONUNBUFFERED'] = '1'

    def publish() -> None:
        completed = {(item['browser'], item['program']) for item in report['checks']}
        report['unexecuted_checks'] = [item for item in planned
                                       if (item['browser'], item['program']) not in completed]
        report['updated_at'] = timestamp()
        atomic_report(report_path, report)

    def verify_inputs() -> None:
        for label, capture in (('source', source_identity), ('verification', verification_identity)):
            try:
                current = capture()
            except Exception as error:
                report[f'{label}_final'] = None
                report[f'{label}_unchanged'] = False
                message = f'{label.capitalize()} identity could not be verified: {error}'
            else:
                report[f'{label}_final'] = current
                unchanged = current == report[label]
                report[f'{label}_unchanged'] = report[f'{label}_unchanged'] is not False and unchanged
                message = None if unchanged else f'{label.capitalize()} inputs changed during this run'
            if message and message not in report['integrity_errors']:
                report['integrity_errors'].append(message)

    def finish(status: str, error: str | None = None) -> None:
        report['status'] = status
        report['error'] = error
        report['finished_at'] = timestamp()
        publish()

    def interrupted(signum: int, _frame) -> None:
        raise RunInterrupted(signum)

    def execute(command: list[str], path: Path) -> dict:
        nonlocal child
        started_at = timestamp()
        started = time.perf_counter()
        with path.open('wb') as output:
            child = subprocess.Popen(command, cwd=REPO_ROOT, env=child_env,
                                     stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=os.name == 'posix')
            exit_code = child.wait()
            child = None
        data = path.read_bytes()
        return {'exit_code': exit_code, 'started_at': started_at, 'finished_at': timestamp(),
                'duration_seconds': round(time.perf_counter() - started, 3),
                'log': {'path': str(path), 'relative_path': path.relative_to(report_path.parent).as_posix(),
                        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}}

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, interrupted)
        publish()
        report['source'] = source_identity()
        report['verification'] = verification_identity()
        report['source_final'] = report['source']
        report['verification_final'] = report['verification']
        report['source_unchanged'] = report['verification_unchanged'] = True
        log_dir.mkdir(parents=True, exist_ok=False)
        report['status'] = 'running'
        publish()

        for browser in browsers:
            path = log_dir / f'{browser}-probe.log'
            report['current_check'] = {'browser': browser, 'program': None, 'kind': 'browser_probe',
                                       'started_at': timestamp(), 'log': str(path)}
            report['browsers'][browser]['status'] = 'running'
            publish()
            outcome = execute([sys.executable, str(Path(__file__).resolve()), '--probe-browser', browser], path)
            version = None
            if outcome['exit_code'] == 0:
                for line in path.read_text(errors='replace').splitlines():
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (isinstance(value, dict) and value.get('browser') == browser
                            and isinstance(value.get('version'), str) and value['version']):
                        version = value['version']
            available = outcome['exit_code'] == 0 and version is not None
            report['browsers'][browser] = {
                'status': 'passed' if available else 'failed', 'version': version,
                'version_source': 'Actual probe using the same Playwright launcher and options as the registered programs',
                **outcome,
            }
            report['current_check'] = None
            verify_inputs()
            publish()
            if not available:
                first_failure = first_failure or (outcome['exit_code'] if outcome['exit_code'] > 0 else 1)
                print(f'{browser}: browser probe failed; its workflow programs were not run ({path})', flush=True)
                if not args.keep_going:
                    break
                continue

            print(f'{browser} {version}: starting {len(programs)} registered programs', flush=True)
            for program in programs:
                path = log_dir / f'{browser}-{Path(program).stem}.log'
                print(f'Running {browser}: {program}', flush=True)
                report['current_check'] = {'browser': browser, 'program': program, 'kind': 'program',
                                           'started_at': timestamp(), 'log': str(path)}
                publish()
                outcome = execute([sys.executable, str(REPO_ROOT / 'tools' / program), '--browser', browser], path)
                report['checks'].append({'browser': browser, 'version': version, 'program': program,
                                         'status': 'passed' if outcome['exit_code'] == 0 else 'failed', **outcome})
                report['current_check'] = None
                verify_inputs()
                publish()
                print(f'{browser}: {program} exited {outcome["exit_code"]} in {outcome["duration_seconds"]:.3f}s ({path})', flush=True)
                if outcome['exit_code']:
                    first_failure = first_failure or (outcome['exit_code'] if outcome['exit_code'] > 0 else 1)
                    if not args.keep_going:
                        break
            if first_failure and not args.keep_going:
                break

        verify_inputs()
        report['completed'] = len(report['checks']) == len(planned)
        report['passed'] = report['completed'] and not first_failure and not report['integrity_errors']
        finish('passed' if report['passed'] else 'failed',
               '; '.join(report['integrity_errors']) if report['integrity_errors'] else None)
        return first_failure or (0 if report['passed'] else 1)
    except RunInterrupted as error:
        for signum in previous_handlers:
            signal.signal(signum, signal.SIG_IGN)
        stop_child(child)
        report['completed'] = report['passed'] = False
        if report['source'] is not None and report['verification'] is not None:
            verify_inputs()
        finish('interrupted', str(error))
        print(str(error), file=sys.stderr, flush=True)
        return 128 + error.signum
    except Exception as error:
        stop_child(child)
        report['passed'] = False
        if report['source'] is not None and report['verification'] is not None:
            verify_inputs()
        finish('error', str(error))
        print(f'Browser matrix error: {error}', file=sys.stderr, flush=True)
        return 1
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


if __name__ == '__main__':
    raise SystemExit(main())
