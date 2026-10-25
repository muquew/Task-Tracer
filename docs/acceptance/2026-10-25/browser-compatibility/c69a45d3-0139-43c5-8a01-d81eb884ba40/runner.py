"""Run unchanged compatibility programs sequentially against the accepted candidate."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import uuid
from zoneinfo import ZoneInfo

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from check import atomic_report, source_identity, verification_identity


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def probe(engine):
    from playwright.sync_api import sync_playwright
    from smoke_playwright import browser_launch_options
    with sync_playwright() as p:
        options = browser_launch_options() if engine == 'chromium' else {'headless': True}
        browser = getattr(p, engine).launch(timeout=30000, **options)
        try:
            print(json.dumps({'engine': engine, 'version': browser.version}), flush=True)
        finally:
            browser.close()
    return 0


def main():
    run_id = str(uuid.uuid4())
    out = ROOT / 'docs/acceptance/2026-10-25/browser-compatibility' / run_id
    out.mkdir(parents=True, exist_ok=False)
    (out / 'runner.py').write_bytes(Path(__file__).read_bytes())
    report = {'schema_version': 1, 'run_id': run_id, 'started_at': now(),
              'started_at_beijing': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='milliseconds'),
              'finished_at': None, 'status': 'initializing', 'completed': False, 'passed': False,
              'source': None, 'source_final': None, 'source_unchanged': False,
              'verification': None, 'verification_final': None, 'verification_unchanged': False,
              'planned_engines': ['chromium', 'firefox', 'webkit'],
              'viewports': [{'width': 1280, 'height': 800}, {'width': 390, 'height': 844}],
              'program': 'tools/compatibility_playwright.py',
              'program_sha256': hashlib.sha256((ROOT / 'tools/compatibility_playwright.py').read_bytes()).hexdigest(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'checks': [], 'current': None, 'error': None, 'traceback': None,
              'scope': 'Three unmodified original CLI executions, one per actual engine; each program runs both declared viewports with fresh persistent synthetic profiles. Runtime probe processes finish before the core program starts.',
              'limitations': ['Cloud Linux engines and narrow viewports are not real Safari/iPhone, OS installation, device restart, real IME, assistive technology or system-notification acceptance.', 'This core acceptance is not a rerun of all 31 specialized matrix programs or the complete 58-check suite.']}
    report_path = out / 'report.json'
    atomic_report(report_path, report)
    print('EVIDENCE_DIRECTORY=' + str(out), flush=True)
    failure = None
    freeze = json.loads((ROOT / 'docs/releases/inputs-4.8.5.json').read_text())['input_capture']['freeze']
    def verify():
        assert source_identity() == freeze['source'], 'Source differs from accepted freeze'
        assert verification_identity() == freeze['verification'], 'Verification inputs differ from accepted freeze'
    try:
        report['source'] = source_identity()
        report['verification'] = verification_identity()
        verify()
        report['status'] = 'running'
        atomic_report(report_path, report)
        for engine in report['planned_engines']:
            verify()
            env = os.environ.copy()
            env.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1',
                        'XDG_CACHE_HOME': '/workspace/.cache',
                        'PLAYWRIGHT_BROWSERS_PATH': '/workspace/.cache/ms-playwright',
                        'TASK_TRACER_BROWSER_EXECUTABLE': '/usr/bin/chromium'})
            if engine == 'webkit':
                env['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'
            report['current'] = {'engine': engine, 'phase': 'version_probe', 'started_at': now()}
            atomic_report(report_path, report)
            with (out / f'{engine}-version-probe.log').open('x') as log:
                probe_code = subprocess.call([sys.executable, str(Path(__file__)), '--probe', engine], cwd=ROOT, env=env,
                                             stdout=log, stderr=subprocess.STDOUT)
            assert probe_code == 0, f'{engine} actual browser launch/version probe failed; preserved log'
            probe_records = [json.loads(line) for line in (out / f'{engine}-version-probe.log').read_text().splitlines() if line.startswith('{')]
            assert len(probe_records) == 1 and probe_records[0]['engine'] == engine
            version = probe_records[0]['version']
            report['current'] = {'engine': engine, 'phase': 'original_compatibility', 'started_at': now()}
            atomic_report(report_path, report)
            start = time.perf_counter()
            log_name = f'{engine}-original-output.log'
            with (out / log_name).open('x') as log:
                code = subprocess.call([sys.executable, 'tools/compatibility_playwright.py', '--browser', engine],
                                       cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            output = (out / log_name).read_text()
            entry = {'engine': engine, 'actual_version': version, 'version_probe_exit_code': probe_code,
                     'original_arguments': ['tools/compatibility_playwright.py', '--browser', engine],
                     'exit_code': code, 'duration_seconds': round(time.perf_counter() - start, 3),
                     'stdout_stderr': log_name, 'passed': False,
                     'viewport_markers': {str(width): f'{engine} {width}px: starting' in output for width in (1280, 390)},
                     'completion_marker': f'{engine}: desktop/mobile critical flows and offline reload passed' in output}
            report['checks'].append(entry)
            atomic_report(report_path, report)
            assert code == 0, f'{engine} original compatibility failed; preserved log'
            assert all(entry['viewport_markers'].values()) and entry['completion_marker'], f'{engine} did not complete both viewport scopes'
            printed_versions = re.findall(rf'^{re.escape(engine)}: ([0-9]+(?:\.[0-9]+)*)$', output, re.M)
            assert printed_versions == [version, version], f'{engine} probe/program versions differ: {printed_versions!r}'
            verify()
            entry['passed'] = True
            atomic_report(report_path, report)
            print(f'{engine}: original two-viewports PASS; version={version}; seconds={entry["duration_seconds"]}', flush=True)
        report['passed'] = True
        report['status'] = 'passed'
    except BaseException as exc:
        failure = exc
        report['status'] = 'failed'
        report['passed'] = False
        report['error'] = repr(exc)
        report['traceback'] = traceback.format_exc()
        print(report['traceback'], flush=True)
    finally:
        report['source_final'] = source_identity()
        report['verification_final'] = verification_identity()
        report['source_unchanged'] = report['source'] == report['source_final'] == freeze['source']
        report['verification_unchanged'] = report['verification'] == report['verification_final'] == freeze['verification']
        if not report['source_unchanged'] or not report['verification_unchanged']:
            report['status'] = 'failed'
            report['passed'] = False
            report['error'] = report['error'] or 'Frozen inputs changed'
        report['completed'] = True
        report['finished_at'] = now()
        report['current'] = None
        atomic_report(report_path, report)
        inventory = {}
        for item in sorted(out.rglob('*')):
            if item.is_file():
                raw = item.read_bytes()
                inventory[item.relative_to(out).as_posix()] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        (out / 'evidence-sha256.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print('FINAL_STATUS=' + report['status'], flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--probe':
        raise SystemExit(probe(sys.argv[2]))
    raise SystemExit(main())
