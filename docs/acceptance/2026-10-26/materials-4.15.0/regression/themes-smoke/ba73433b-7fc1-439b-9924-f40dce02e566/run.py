#!/usr/bin/env python3
"""Sequential original programs, immutable runtime/tool snapshots, fresh native report."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path('/workspace/Task-Tracer')
OUT = Path(os.environ['TASK_TRACER_MATERIALS_REGRESSION_OUT'])
EXPECTED_INDEX = os.environ['TASK_TRACER_EXPECTED_INDEX_SHA256']
RUNTIME = ('index.html', 'sw.js', 'manifest.json', 'resources/en.json', 'resources/zh-CN.json')
BOOTSTRAP_SOURCE = ROOT / 'docs/acceptance/2026-10-25/themes-4.13.0/protection/csp_wait_bootstrap.py'
WRAPPER_SOURCE = Path('/tmp/task_tracer_materials_csp_wrapper_20261026.py')

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def take():
    names = list(RUNTIME) + ['vercel.json', 'node_modules/axe-core/axe.min.js']
    names += [str(path.relative_to(ROOT)) for path in sorted((ROOT / 'tools').glob('*.py'))]
    return {name: (ROOT / name).read_bytes() for name in names}

def snapshot(folder, data, executed):
    names = sorted(set(RUNTIME) | set(executed) | {'vercel.json', 'node_modules/axe-core/axe.min.js'})
    manifest = {}
    for name in names:
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[name])
        manifest[name] = {'sha256': sha(data[name]), 'bytes': len(data[name])}
    save(folder / 'snapshot-manifest.json', manifest)
    return manifest

assert OUT.is_dir()
assert not (OUT / 'report.json').exists(), 'Never overwrite a prior run'
assert sha((ROOT / 'index.html').read_bytes()) == EXPECTED_INDEX, 'Unexpected frozen index'
assert sha((ROOT / 'tools/appearance_preferences_playwright.py').read_bytes()) == '1b2fefa04bef90a9fc3323eaf1e2c99a12c99c4641cb110cb9e8bc50dcbf9555', 'Unexpected helper identity'
shutil.copy2(BOOTSTRAP_SOURCE, OUT / 'csp_wait_bootstrap.py')
shutil.copy2(WRAPPER_SOURCE, OUT / 'csp_server_wrapper.py')
shutil.copy2(Path(__file__), OUT / 'run.py')
report = {'status': 'running', 'completed': False, 'passed': False, 'started_at_utc': now(),
          'expected_index_sha256': EXPECTED_INDEX, 'browser_requested': 'chromium',
          'source_or_tools_modified_by_runner': False,
          'scope': ['original craft_accent_playwright.py --case all (six original cases)'],
          'prior_smoke_not_rerun': 'Root scoped this final rerun to craft only; prior 3aa smoke pass remains historical',
          'header_method': 'Original ProductionHeaderHandler selected before original local_server construction; exact class asserted externally',
          'wait_adapter': 'Verbatim existing expression-to-function predicate bootstrap; original timeouts and assertions unchanged',
          'runs': []}
save(OUT / 'report.json', report)
env = dict(os.environ)
env.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1',
            'TASK_TRACER_BROWSER_EXECUTABLE': '/usr/bin/chromium',
            'TASK_TRACER_PRODUCTION_HEADERS': '1', 'XDG_CACHE_HOME': '/workspace/.cache',
            'PLAYWRIGHT_BROWSERS_PATH': '/workspace/.cache/ms-playwright'})
env.pop('TASK_TRACER_URL', None)
initial = take()
for name, arguments in [('craft_accent_playwright.py', ['--case', 'all'])]:
    case = OUT / name.removesuffix('.py')
    case.mkdir()
    before = take()
    assert sha(before['index.html']) == EXPECTED_INDEX
    argv = [sys.executable, '-u', str(OUT / 'csp_server_wrapper.py'), str(case / 'observer.json'),
            str(OUT / 'csp_wait_bootstrap.py'), str(ROOT / 'tools' / name), *arguments]
    result = {'program': name, 'argv': argv, 'cwd': str(ROOT), 'status': 'running', 'completed': False,
              'passed': False, 'started_at_utc': now(), 'environment_overrides': {k: env[k] for k in
                ('PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED', 'TASK_TRACER_BROWSER_EXECUTABLE',
                 'TASK_TRACER_PRODUCTION_HEADERS', 'XDG_CACHE_HOME', 'PLAYWRIGHT_BROWSERS_PATH')}}
    save(case / 'result.json', result)
    print(json.dumps({'event': 'START', 'program': name, 'at': result['started_at_utc'], 'out': str(case)}), flush=True)
    timer = time.monotonic()
    with (case / 'stdout.log').open('w') as stdout, (case / 'stderr.log').open('w') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                 start_new_session=True)
        result['worker_pid'] = child.pid
        save(case / 'result.json', result)
        try:
            code = child.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            # Outer safety cap only; original UI/axe/animation timeouts unchanged.
            import signal
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)
            code = 124
    elapsed = time.monotonic() - timer
    after = take()
    observed = json.loads((case / 'observer.json').read_text()) if (case / 'observer.json').exists() else {}
    executed = observed.get('executed_tools', [])
    before_manifest = snapshot(case / 'inputs-before', before, executed)
    after_manifest = snapshot(case / 'inputs-after', after, executed)
    changes = [key for key in before_manifest if before_manifest[key] != after_manifest[key]]
    all_tool_changes = [key for key in before if key.startswith('tools/') and before[key] != after[key]]
    config = json.loads(before['vercel.json'])
    csp = next(header['value'] for route in config['headers'] if route['source'] == '/(.*)'
               for header in route['headers'] if header['key'].lower() == 'content-security-policy')
    documents = observed.get('documents', [])
    csp_exact = bool(documents) and all(item['content-security-policy'] == csp for item in documents)
    server_exact = bool(observed.get('servers')) and all(item['handler'] == 'security_playwright.ProductionHeaderHandler' for item in observed['servers'])
    cleanup = not any(observed.get('browser_connected_after_final_cleanup', [True]))
    observation_complete = not observed.get('observer_errors', [True]) and observed.get('context_count', 0) > 0 and observed.get('context_count') == observed.get('contexts_closed')
    passed = code == 0 and not changes and not all_tool_changes and csp_exact and server_exact and cleanup and observation_complete
    result.update({'status': 'passed' if passed else 'failed', 'completed': True, 'passed': passed,
        'exit_code': code, 'duration_seconds': round(elapsed, 3), 'finished_at_utc': now(),
        'runtime_files': list(RUNTIME), 'executed_tools': executed, 'changed_snapshot_inputs': changes,
        'changed_repository_tool_files': all_tool_changes, 'documents_count': len(documents),
        'document_csp_exact': csp_exact, 'server_handler_exact': server_exact,
        'browser_cleanup_confirmed': cleanup, 'observer_and_context_cleanup_confirmed': observation_complete, 'index_before': sha(before['index.html']),
        'index_after': sha(after['index.html']), 'stdout': str(case / 'stdout.log'), 'stderr': str(case / 'stderr.log')})
    save(case / 'result.json', result)
    report['runs'].append(result)
    save(OUT / 'report.json', report)
    print(json.dumps({'event': 'END', 'program': name, 'passed': passed, 'exit': code,
                      'seconds': result['duration_seconds'], 'csp_exact': csp_exact, 'inputs_changed': changes,
                      'out': str(case)}), flush=True)
    if not passed:
        print((case / 'stderr.log').read_text()[-9000:], flush=True)
        # Preserve a genuine failure and continue the independent original smoke.
final = take()
report.update({'status': 'passed' if all(run['passed'] for run in report['runs']) else 'failed',
               'completed': True, 'passed': all(run['passed'] for run in report['runs']),
               'finished_at_utc': now(), 'runtime_start_end_identical': all(initial[key] == final[key] for key in RUNTIME),
               'runtime_final_sha256': {key: sha(final[key]) for key in RUNTIME},
               'all_repository_tools_start_end_identical': all(initial[key] == final[key] for key in initial if key.startswith('tools/'))})
save(OUT / 'report.json', report)
files = {str(path.relative_to(OUT)): {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
         for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'evidence-sha256.json'}
save(OUT / 'evidence-sha256.json', {'file_count': len(files), 'files': files})
print(json.dumps({'event': 'COMPLETE', 'passed': report['passed'], 'report': str(OUT / 'report.json')}), flush=True)
sys.exit(0 if report['passed'] else 1)
