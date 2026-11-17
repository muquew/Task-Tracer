"""Render bounded CI outcomes and source-bound failure locations without reading arbitrary paths."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Mapping
from types import CodeType
import uuid

from scripts.project_layout import REPO_ROOT


BROWSERS = ('chromium', 'firefox', 'webkit')
REPORT_STATES = frozenset(('initializing', 'running', 'passed', 'failed', 'interrupted', 'error'))
MAX_REPORT = 2_000_000
MAX_LOG = 1024 * 1024
MAX_SOURCE = 512 * 1024
HASH = re.compile(r'[0-9a-f]{64}\Z')
PROGRAM_ID = re.compile(r'[a-z][a-z0-9_]{0,79}\.py\Z')
SOURCE_PART = re.compile(r'[a-z_][a-z0-9_]{0,95}\Z')
SOURCE_NAME = re.compile(r'[a-z_][a-z0-9_]{0,95}\.py\Z')
TRACE_FRAME = re.compile(r'  File "([^"\r\n]{1,512})", line ([1-9][0-9]{0,6}), in ([A-Za-z_][A-Za-z0-9_]{0,127}|<module>)\Z')
TRACE_EXCEPTION = re.compile(r'([A-Za-z_][A-Za-z0-9_.]{0,127})(?::[^\r\n]*)?\Z')
TRACE_CLASSES = frozenset(('AssertionError', 'TimeoutError', 'Error', 'ValueError',
    'TypeError', 'RuntimeError', 'KeyError', 'OSError', 'PermissionError',
    'FileNotFoundError', 'ImportError', 'ModuleNotFoundError', 'AttributeError',
    'IndexError', 'SyntaxError', 'SystemExit'))


@dataclass(frozen=True)
class Summary:
    status: str
    console: tuple[str, ...]
    markdown: str
    exit_code: int


def _safe_read(root_fd: int, parts: tuple[str, ...], limit: int) -> bytes:
    """Walk from an existing repository descriptor, never through links or special files."""
    if not parts or any(not part or part in ('.', '..') or any(char in part for char in ('/', '\\', '\x00'))
                        for part in parts):
        raise ValueError('Unsafe file components')
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 <= info.st_size <= limit:
                raise ValueError('Unsafe file metadata')
            with os.fdopen(file_fd, 'rb', closefd=False) as stream:
                data = stream.read(limit + 1)
            if len(data) != info.st_size or len(data) > limit:
                raise ValueError('File changed or exceeded its bound')
            return data
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def _registry_snapshot() -> tuple[tuple[str, ...], tuple[str, ...], dict[str, str], str]:
    """Bind the fixed registry's executed API to its source bytes, bypassing stale bytecode."""
    root_fd = os.open(REPO_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        data = _safe_read(root_fd, ('tests', 'registry.py'), MAX_SOURCE)
    finally:
        os.close(root_fd)
    module = {'__name__': 'tests.registry', '__package__': 'tests', '__file__': str(REPO_ROOT / 'tests/registry.py')}
    exec(compile(data, module['__file__'], 'exec'), module)
    checks, programs, paths = tuple(module['CHECKS']), tuple(module['PROGRAMS']), dict(module['PROGRAM_PATHS'])
    for identifiers in (checks, programs):
        if not (1 <= len(identifiers) <= 256 and len(set(identifiers)) == len(identifiers)
                and all(isinstance(name, str) and PROGRAM_ID.fullmatch(name) for name in identifiers)):
            raise ValueError('Invalid test registry')
    if not set(programs).issubset(checks) or any(_source_parts(paths.get(name)) is None for name in checks):
        raise ValueError('Invalid test program paths')
    return checks, programs, paths, hashlib.sha256(data).hexdigest()


def _source_parts(name: object) -> tuple[str, ...] | None:
    if not isinstance(name, str) or not name or '\\' in name:
        return None
    relative = PurePosixPath(name)
    parts = relative.parts
    if (relative.is_absolute() or relative.as_posix() != name or not 2 <= len(parts) <= 8
            or parts[0] not in ('scripts', 'tests') or not SOURCE_NAME.fullmatch(parts[-1])
            or any(not SOURCE_PART.fullmatch(part) for part in parts[:-1])):
        return None
    return parts


CHECKS, PROGRAMS, PROGRAM_PATHS, REGISTRY_SHA256 = _registry_snapshot()


def _expected_path(root: Path, path: Path, expected: str) -> tuple[str, ...]:
    target = Path(path)
    if target not in (Path(expected), root / expected):
        raise ValueError('Unexpected CI report path')
    return tuple(PurePosixPath(expected).parts)


def _load_report(root: Path, path: Path, expected: str) -> tuple[dict, str]:
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        data = _safe_read(root_fd, _expected_path(root, path, expected), MAX_REPORT)
        report = json.loads(data)
        if not isinstance(report, dict):
            raise ValueError('Expected an object')
        status = report.get('status')
        return report, status if isinstance(status, str) and status in REPORT_STATES else 'invalid_report'
    except FileNotFoundError:
        return {}, 'missing_report'
    except (OSError, ValueError, TypeError, RecursionError):
        return {}, 'invalid_report'
    finally:
        os.close(root_fd)


def _identity_valid(value: object) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get('sha256'), str) or not HASH.fullmatch(value['sha256']):
        return False
    files = value.get('files')
    if not isinstance(files, dict) or not 1 <= len(files) <= 8192:
        return False
    for name, digest in files.items():
        if not isinstance(name, str) or not name or any(char in name for char in ('\\', '\x00', ':', '\r', '\n')):
            return False
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name or name == '.':
            return False
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            return False
    try:
        serialized = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    except UnicodeError:
        return False
    return hashlib.sha256(serialized).hexdigest() == value['sha256']


def _registry_bound(root_fd: int, report: dict) -> bool:
    verification = report.get('verification')
    if not _identity_valid(verification):
        return False
    data = _safe_read(root_fd, ('tests', 'registry.py'), MAX_SOURCE)
    digest = hashlib.sha256(data).hexdigest()
    return digest == verification['files'].get('tests/registry.py') == REGISTRY_SHA256


def _inputs_consistent(root: Path, report: dict) -> bool:
    if report.get('integrity_errors') != []:
        return False
    for name in ('source', 'verification'):
        if (report.get(f'{name}_unchanged') is not True or not _identity_valid(report.get(name))
                or report.get(f'{name}_final') != report[name]):
            return False
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _registry_bound(root_fd, report)
    except (OSError, ValueError, TypeError):
        return False
    finally:
        os.close(root_fd)


def _signature_lines(report: dict) -> list[str]:
    lines = ['', '| Input identity | Initial SHA-256 | Final SHA-256 | Unchanged |',
             '| --- | --- | --- | --- |']
    for name in ('source', 'verification'):
        initial, final = report.get(name), report.get(f'{name}_final')
        before = f'`{initial["sha256"]}`' if _identity_valid(initial) else 'unavailable'
        after = f'`{final["sha256"]}`' if _identity_valid(final) else 'unavailable'
        unchanged = report.get(f'{name}_unchanged')
        state = 'yes' if unchanged is True else 'no' if unchanged is False else 'unknown'
        lines.append(f'| {name} | {before} | {after} | {state} |')
    return lines


def _code(value: object) -> bool:
    return type(value) is int and -255 <= value <= 255


def _duration(value: object) -> bool:
    return type(value) in (int, float) and 0 <= value <= 86400 and math.isfinite(value)


def _ownership(source: bytes) -> dict[int, str]:
    tree = ast.parse(source)
    ownership = {node.lineno: '<module>' for node in ast.walk(tree) if hasattr(node, 'lineno')}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            for number in ownership:
                if node.body[0].lineno <= number <= node.end_lineno:
                    ownership[number] = node.name
    executable = {}

    def collect(code: CodeType) -> None:
        for _, _, number in code.co_lines():
            if number is not None:
                executable.setdefault(number, set()).add(code.co_name)
        for value in code.co_consts:
            if isinstance(value, CodeType):
                collect(value)

    collect(compile(tree, '<verified-ci-source>', 'exec'))
    return {number: owner for number, owner in ownership.items() if owner in executable.get(number, ())}


def get_safe_trace(root: Path, report_path: Path, report: dict, check: dict) -> dict | None:
    """Return only a signed repository location and fixed exception class, never log messages."""
    root = Path(root).resolve(strict=True)
    root_fd = None
    try:
        engine = check.get('browser')
        if engine not in BROWSERS or report.get('schema_version') != 1:
            return None
        expected = f'dist/browser-matrix-{engine}.json'
        report_parts = _expected_path(root, report_path, expected)
        run_id = report.get('run_id')
        parsed_id = uuid.UUID(run_id)
        if parsed_id.version != 4 or str(parsed_id) != run_id:
            return None
        log_root = f'browser-matrix-{engine}-logs'
        if report.get('log_directory') != f'{log_root}/{run_id}':
            return None
        if (check not in report.get('checks', []) or check.get('status') != 'failed'
                or not _code(check.get('exit_code')) or not check['exit_code']):
            return None
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        if json.loads(_safe_read(root_fd, report_parts, MAX_LOG)) != report or not _registry_bound(root_fd, report):
            return None
        program = check.get('program')
        if not isinstance(program, str) or program not in PROGRAMS:
            return None
        log = check.get('log')
        filename = f'{engine}-{program[:-3]}.log'
        if (not isinstance(log, dict) or log.get('relative_path') != f'{log_root}/{run_id}/{filename}'
                or type(log.get('bytes')) is not int or not 0 <= log['bytes'] <= MAX_LOG
                or not isinstance(log.get('sha256'), str) or not HASH.fullmatch(log['sha256'])):
            return None
        data = _safe_read(root_fd, ('dist', log_root, run_id, filename), MAX_LOG)
        if len(data) != log['bytes'] or hashlib.sha256(data).hexdigest() != log['sha256']:
            return None
        lines = data.decode('utf-8').splitlines()
        starts = [i for i, line in enumerate(lines) if line == 'Traceback (most recent call last):']
        if not starts:
            return None
        candidate, owners = None, {}
        verification = report['verification']['files']
        prefix = root.as_posix() + '/'
        for line in lines[starts[-1] + 1:]:
            match = TRACE_FRAME.fullmatch(line)
            if match:
                raw_path, number, function = match.groups()
                name = raw_path[len(prefix):] if raw_path.startswith(prefix) else raw_path
                parts = _source_parts(name)
                if parts is None or name not in verification:
                    continue
                if name not in owners:
                    source = _safe_read(root_fd, parts, MAX_SOURCE)
                    if hashlib.sha256(source).hexdigest() != verification[name]:
                        return None
                    owners[name] = _ownership(source)
                number = int(number)
                if owners[name].get(number) == function:
                    candidate = {'path': name, 'basename': parts[-1], 'line': number, 'function': function}
                continue
            if line and not line[0].isspace():
                exception = TRACE_EXCEPTION.fullmatch(line)
                kind = exception.group(1).rsplit('.', 1)[-1] if exception else None
                if kind not in TRACE_CLASSES or candidate is None:
                    return None
                return {**candidate, 'exception_class': kind}
        return None
    except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError, UnicodeError):
        return None
    finally:
        if root_fd is not None:
            os.close(root_fd)


def _summarize(root: Path, report_path: Path, engine: str | None) -> Summary:
    root = Path(root).resolve(strict=True)
    programs = PROGRAMS if engine else CHECKS
    expected = f'dist/browser-matrix-{engine}.json' if engine else 'dist/check-results.json'
    report, status = _load_report(root, report_path, expected)
    checks = report.get('checks', [])
    shape_valid = isinstance(checks, list) and len(checks) <= 256
    checks = checks if shape_valid else []
    expected_plan = [{'browser': engine, 'program': name} for name in programs] if engine else list(programs)
    full_scope = report.get('planned_checks') == expected_plan
    schema = 1 if engine else 2
    if engine:
        scope = report.get('scope')
        full_scope = (full_scope and isinstance(scope, dict) and scope.get('browsers') == [engine]
                      and scope.get('programs') == list(programs)
                      and scope.get('registry_program_count') == len(programs)
                      and scope.get('all_registered_programs') is True)
    shape_valid = (shape_valid and all(isinstance(item, dict) and isinstance(item.get('program'), str)
                    and item['program'] in programs and (not engine or item.get('browser') == engine)
                    for item in checks))
    if shape_valid:
        shape_valid = len({item['program'] for item in checks}) == len(checks)
    signatures_valid = all(report.get(key) is None or _identity_valid(report[key])
                           for key in ('source', 'verification', 'source_final', 'verification_final'))
    rows = []
    for program in programs:
        matches = [item for item in checks if isinstance(item, dict) and item.get('program') == program
                   and (not engine or item.get('browser') == engine)]
        item = matches[0] if len(matches) == 1 else None
        code = item.get('exit_code') if item else None
        duration = item.get('duration_seconds') if item else None
        state = 'not_run' if not matches else 'invalid'
        if (item and _code(code) and _duration(duration)
                and (not engine or item.get('status') == ('passed' if code == 0 else 'failed'))):
            state = 'passed' if code == 0 else 'failed'
        rows.append((program, state, code if _code(code) else None,
                     f'{duration:.3f}' if _duration(duration) else 'unknown', item))
    counts = {name: sum(row[1] == name for row in rows) for name in ('passed', 'failed', 'not_run', 'invalid')}
    inputs_consistent = _inputs_consistent(root, report)
    all_passed = (shape_valid and full_scope and len(checks) == len(programs)
                  and counts['passed'] == len(programs) and report.get('completed') is True
                  and report.get('passed') is True and inputs_consistent)
    if status == 'passed' and not all_passed:
        status = 'incomplete'
    if report and (not shape_valid or not full_scope or not signatures_valid or report.get('schema_version') != schema):
        status = 'invalid_report'
    label = f'matrix browser={engine}' if engine else 'checks'
    header = (f'{label} status={status} passed={counts["passed"]} failed={counts["failed"]} '
              f'not_run={counts["not_run"]} invalid={counts["invalid"]} planned={len(programs)}')
    console = [header]
    title = f'Browser program outcomes: {engine}' if engine else 'Check program outcomes'
    lines = [f'## {title}', '', header, '', '| Program | Status | Exit | Duration seconds |',
             '| --- | --- | ---: | ---: |']
    traces = []
    for program, state, code, duration, item in rows:
        code_text = str(code) if code is not None else 'unknown'
        console.append(f'{program} status={state} exit={code_text} duration={duration}')
        lines.append(f'| `{program}` | {state} | {code_text} | {duration} |')
        if state == 'failed':
            trace = get_safe_trace(root, report_path, report, item) if engine else None
            detail = ''
            if trace is not None:
                location = f'{trace["path"]}:{trace["line"]}:{trace["function"]}'
                detail = f' location={location} exception={trace["exception_class"]}'
                traces.append(f'- `{location}` · `{trace["exception_class"]}`')
            console.append(f'::error::{program} exit={code}{detail}')
    if traces:
        lines.extend(['', 'Safe failure locations:', *traces])
    lines.extend(_signature_lines(report))
    if report and not inputs_consistent:
        console.append(f'::error::{label} input_integrity=unverified_or_changed')
        lines.extend(['', 'Input integrity: unverified or changed.'])
    if status != 'passed':
        console.append(f'::error::{label} status={status}')
    return Summary(status, tuple(console), '\n'.join(lines) + '\n', 0 if status == 'passed' else 1)


def summarize_checks(root: Path = REPO_ROOT, report_path: Path = Path('dist/check-results.json')) -> Summary:
    return _summarize(root, report_path, None)


def summarize_browser(root: Path, engine: str, report_path: Path | None = None) -> Summary:
    if engine not in BROWSERS:
        raise ValueError('Unsupported browser engine')
    return _summarize(root, report_path or Path(f'dist/browser-matrix-{engine}.json'), engine)


def _outcome(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, '')
    return value if value in ('success', 'failure', 'cancelled', 'skipped') else 'not_run'


def summarize_artifacts(env: Mapping[str, str]) -> Summary:
    build, initial, retry, diagnostic = (_outcome(env, name) for name in
        ('BUILD_OUTCOME', 'DISTRIBUTION_OUTCOME', 'DISTRIBUTION_RETRY_OUTCOME', 'DIAGNOSTIC_OUTCOME'))
    delivered = initial == 'success' or retry == 'success'
    console = []
    if diagnostic in ('failure', 'cancelled'):
        console.append('::warning::Diagnostic artifact upload failed; check outcomes remain in the job summary and original logs.')
    if initial == 'failure' and retry == 'success':
        console.append('::notice::Verified distribution upload recovered on its single retry.')
    failed = build == 'success' and not delivered
    if failed:
        console.append('::error::Verified distribution artifact was not delivered.')
    lines = ['## Artifact delivery', '', '| Step | Outcome |', '| --- | --- |',
             f'| Verified build | {build} |', f'| Distribution upload | {initial} |',
             f'| Distribution retry | {retry} |', f'| Diagnostic upload | {diagnostic} |']
    return Summary('failed' if failed else 'reported', tuple(console), '\n'.join(lines) + '\n', int(failed))


def summarize_browser_artifact(env: Mapping[str, str]) -> Summary:
    outcome = _outcome(env, 'ARTIFACT_OUTCOME')
    engine = env.get('BROWSER_ENGINE')
    engine = engine if engine in BROWSERS else 'unknown'
    console = ()
    if outcome in ('failure', 'cancelled'):
        console = ('::warning::Browser diagnostic artifact upload failed; full program outcomes remain in the job summary and original logs.',)
    markdown = f'\n## Browser artifact delivery\n\nBrowser: {engine}. Diagnostic upload: {outcome}.\n'
    return Summary('reported', console, markdown, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    checks = commands.add_parser('checks', help='Summarize the full release-check registry')
    checks.add_argument('--report', type=Path, default=Path('dist/check-results.json'))
    browser = commands.add_parser('browser', help='Summarize one complete browser registry')
    browser.add_argument('--browser', choices=BROWSERS, required=True)
    browser.add_argument('--report', type=Path)
    commands.add_parser('artifacts', help='Summarize verified distribution delivery')
    commands.add_parser('browser-artifact', help='Summarize browser diagnostic delivery')
    args = parser.parse_args(argv)
    if args.command == 'checks':
        summary = summarize_checks(REPO_ROOT, args.report)
    elif args.command == 'browser':
        summary = summarize_browser(REPO_ROOT, args.browser, args.report)
    elif args.command == 'artifacts':
        summary = summarize_artifacts(os.environ)
    else:
        summary = summarize_browser_artifact(os.environ)
    for line in summary.console:
        print(line)
    target = os.environ.get('GITHUB_STEP_SUMMARY')
    if target:
        with open(target, 'a', encoding='utf-8') as stream:
            stream.write(summary.markdown)
    return summary.exit_code


if __name__ == '__main__':
    raise SystemExit(main())
