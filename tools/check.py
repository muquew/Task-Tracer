#!/usr/bin/env python3
"""Run release checks with atomic reports bound to source and verification inputs."""
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

REPO_ROOT = Path(__file__).resolve().parents[1]


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def atomic_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def identity_file(name: str) -> Path:
    if not isinstance(name, str) or not name or any(char in name for char in ('\\', '\x00', ':')):
        raise ValueError(f'Unsafe identity input: {name!r}')
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name or name == '.':
        raise ValueError(f'Unsafe identity input: {name!r}')
    path = REPO_ROOT
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'Identity input must not be a symbolic link: {name}')
    if not path.is_file():
        raise ValueError(f'Missing identity input: {name}')
    return path


def identity(names: list[str]) -> dict:
    files = {name: hashlib.sha256(identity_file(name).read_bytes()).hexdigest()
             for name in sorted(set(names))}
    serialized = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return {'files': files, 'sha256': hashlib.sha256(serialized).hexdigest()}


def source_identity() -> dict:
    module = ast.parse(identity_file('tools/build_release.py').read_text(encoding='utf-8'))
    assignments = [node.value for node in module.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'DISTRIBUTION_SOURCES'
                           for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError('Expected one literal DISTRIBUTION_SOURCES release contract')
    try:
        sources = ast.literal_eval(assignments[0])
    except (ValueError, TypeError, SyntaxError) as error:
        raise ValueError('DISTRIBUTION_SOURCES must be a literal mapping') from error
    if not isinstance(sources, dict) or not sources or not all(isinstance(name, str) for name in sources.values()):
        raise ValueError('DISTRIBUTION_SOURCES must name the required release source files')
    return identity(list(sources.values()))


def verification_identity() -> dict:
    names = [path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / 'tools').rglob('*.py')]
    workflows = REPO_ROOT / '.github' / 'workflows'
    names.extend(path.relative_to(REPO_ROOT).as_posix() for suffix in ('*.yml', '*.yaml')
                 for path in workflows.glob(suffix))
    names.extend(('package.json', 'package-lock.json', 'requirements-dev.txt'))
    return identity(names)


class RunInterrupted(BaseException):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f'Interrupted by {signal.Signals(signum).name}')


def stop_child(child: subprocess.Popen | None) -> None:
    if child is None:
        return
    try:
        if os.name == 'posix':
            os.killpg(child.pid, signal.SIGTERM)
        elif child.poll() is None:
            child.terminate()
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == 'posix':
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
        except ProcessLookupError:
            pass
        child.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static-only", action="store_true",
        help="Run static consistency and date semantics without browser dependencies.",
    )
    parser.add_argument('--report', type=Path, help='Write machine-readable program outcomes, including failures')
    parser.add_argument('--keep-going', action='store_true', help='Run remaining programs after a failure and still return a failing exit code')
    args = parser.parse_args()
    checks = ["validate_static.py", "date_semantics_test.py", "security_policy.py",
              "release_payload_test.py", "release_versions_test.py", "check_runner_test.py", "static_syntax_test.py"]
    if not args.static_only:
        checks.extend([
            "verify_deployment_test.py",
            "smoke_playwright.py",
            "appearance_preferences_playwright.py",
            "craft_accent_playwright.py",
            "settings_navigation_playwright.py",
            "recovery_playwright.py",
            "recovery_management_playwright.py",
            "undo_concurrency_playwright.py",
            "batch_selection_playwright.py",
            "craft_batch_project_playwright.py",
            "csv_playwright.py",
            "backup_freshness_playwright.py",
            "backup_reminder_priority_playwright.py",
            "reminder_concurrency_playwright.py",
            "import_reference_playwright.py",
            "saved_views_playwright.py",
            "views_delete_playwright.py",
            "project_scope_playwright.py",
            "onboarding_playwright.py",
            "help_playwright.py",
            "ime_input_playwright.py",
            "task_draft_playwright.py",
            "imported_text_edit_playwright.py",
            "imported_reminder_edit_playwright.py",
            "quick_add_recovery_playwright.py",
            "quick_add_date_playwright.py",
            "direct_capture_playwright.py",
            "context_creation_playwright.py",
            "dialog_lifecycle_playwright.py",
            "views_portability_playwright.py",
            "import_preview_concurrency_playwright.py",
            "queued_write_concurrency_playwright.py",
            "import_read_lifecycle_playwright.py",
            "craft_import_summary_playwright.py",
            "import_conflicts_playwright.py",
            "storage_lifecycle_playwright.py",
            "storage_health_playwright.py",
            "upgrade_playwright.py",
            "service_worker_update_playwright.py",
            "manual_update_playwright.py",
            "security_playwright.py",
            "timezone_playwright.py",
            "dst_wall_time_playwright.py",
            "foreign_wall_time_playwright.py",
            "recurrence_timezone_playwright.py",
            "repeat_lineage_playwright.py",
            "repeat_delete_playwright.py",
            "repeat_merge_playwright.py",
            "workspace_failure_playwright.py",
            "time_refresh_playwright.py",
            "stats_scope_playwright.py",
            "craft_stats_focus_playwright.py",
            "performance_playwright.py",
            "calendar_performance_playwright.py",
            "calendar_navigation_playwright.py",
            "calendar_timezone_playwright.py",
            "workspace_roundtrip_playwright.py",
            "compatibility_playwright.py",
            "accessibility_i18n_audit.py",
            "release_playwright.py",
        ])
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
            child = subprocess.Popen([sys.executable, str(REPO_ROOT / 'tools' / check)],
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
