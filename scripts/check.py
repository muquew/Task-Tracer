"""Run the explicit release-check registry with atomic input-bound reports."""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from scripts.project_layout import REPO_ROOT
from scripts.runner_support import timestamp, atomic_report, source_identity, verification_identity, RunInterrupted, stop_child
from tests.registry import STATIC_CHECKS, CHECKS, program_module

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static-only", action="store_true",
        help="Run static consistency and date semantics without browser dependencies.",
    )
    parser.add_argument('--report', type=Path, help='Write machine-readable program outcomes, including failures')
    parser.add_argument('--keep-going', action='store_true', help='Run remaining programs after a failure and still return a failing exit code')
    args = parser.parse_args()
    checks = list(STATIC_CHECKS if args.static_only else CHECKS)
    child_env = os.environ.copy()
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    report = {'schema_version': 2, 'run_id': str(uuid.uuid4()), 'status': 'initializing',
              'started_at': timestamp(), 'updated_at': None, 'finished_at': None,
              'planned_checks': checks, 'current_check': None,
              'source': None, 'verification': None, 'source_final': None, 'verification_final': None,
              'source_unchanged': None, 'verification_unchanged': None, 'integrity_errors': [],
              'error': None, 'completed': False, 'passed': False, 'checks': []}
    child = None
    first_failure = 0
    previous_handlers = {}

    def publish() -> None:
        report['updated_at'] = timestamp()
        if args.report:
            atomic_report(args.report, report)

    def verify_inputs() -> None:
        for label, capture in (('source', source_identity), ('verification', verification_identity)):
            try:
                current = capture()
            except Exception as error:
                report[f'{label}_final'] = None
                report[f'{label}_unchanged'] = False
                message = f'{label.capitalize()} identity could not be verified: {error}'
                if message not in report['integrity_errors']:
                    report['integrity_errors'].append(message)
                continue
            report[f'{label}_final'] = current
            unchanged = current == report[label]
            report[f'{label}_unchanged'] = report[f'{label}_unchanged'] is not False and unchanged
            message = f'{label.capitalize()} inputs changed during this run'
            if not unchanged and message not in report['integrity_errors']:
                report['integrity_errors'].append(message)

    def finish(status: str, error: str | None = None) -> None:
        report['status'] = status
        report['error'] = error
        report['finished_at'] = timestamp()
        publish()

    def interrupted(signum: int, _frame) -> None:
        raise RunInterrupted(signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, interrupted)
        publish()
        report['source'] = source_identity()
        report['verification'] = verification_identity()
        report['source_final'] = report['source']
        report['verification_final'] = report['verification']
        report['source_unchanged'] = report['verification_unchanged'] = True
        report['status'] = 'running'
        publish()
        for check in checks:
            print(f"Running {check}", flush=True)
            report['current_check'] = {'program': check, 'started_at': timestamp()}
            publish()
            started = time.perf_counter()
            child = subprocess.Popen([sys.executable, '-m', program_module(check)],
                                     cwd=REPO_ROOT, env=child_env, start_new_session=os.name == 'posix')
            exit_code = child.wait()
            child = None
            report['checks'].append({'program': check, 'exit_code': exit_code,
                                     'duration_seconds': round(time.perf_counter() - started, 3)})
            report['current_check'] = None
            verify_inputs()
            publish()
            if exit_code:
                first_failure = first_failure or (exit_code if exit_code > 0 else 1)
                if not args.keep_going:
                    break
        verify_inputs()
        report['completed'] = len(report['checks']) == len(checks)
        report['passed'] = report['completed'] and not first_failure and not report['integrity_errors']
        finish('passed' if report['passed'] else 'failed',
               '; '.join(report['integrity_errors']) if report['integrity_errors'] else None)
        if first_failure:
            print(f"{sum(item['exit_code'] != 0 for item in report['checks'])} of {len(checks)} check programs failed", file=sys.stderr, flush=True)
            return first_failure
        if report['integrity_errors']:
            print(report['error'], file=sys.stderr, flush=True)
            return 1
        print(f"All {len(checks)} check programs passed", flush=True)
        return 0
    except RunInterrupted as error:
        for signum in previous_handlers:
            signal.signal(signum, signal.SIG_IGN)
        stop_child(child)
        report['completed'] = report['passed'] = False
        try:
            if report['source'] is not None and report['verification'] is not None:
                verify_inputs()
        except Exception as integrity_error:
            report['integrity_errors'].append(str(integrity_error))
        finish('interrupted', str(error))
        print(str(error), file=sys.stderr, flush=True)
        return 128 + error.signum
    except Exception as error:
        stop_child(child)
        report['passed'] = False
        finish('error', str(error))
        print(f'Check runner error: {error}', file=sys.stderr, flush=True)
        return 1
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
