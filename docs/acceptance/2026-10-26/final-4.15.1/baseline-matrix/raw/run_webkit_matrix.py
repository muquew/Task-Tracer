from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import subprocess, os, json, time, sys, hashlib

ROOT = Path('/workspace/task-tracer-final-baseline')
OUT = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix')
sys.path.insert(0, str(ROOT / 'tools'))
from check import source_identity, verification_identity

def capture():
    return {'source': source_identity(), 'verification': verification_identity(), 'vcs_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(), 'vcs_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode()}

def matrix(engine):
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', XDG_CACHE_HOME='/workspace/.cache', PLAYWRIGHT_BROWSERS_PATH='/workspace/.cache/ms-playwright', PYTHONUNBUFFERED='1')
    env.pop('TASK_TRACER_PRODUCTION_HEADERS', None)
    if engine == 'chromium':
        env['TASK_TRACER_BROWSER_EXECUTABLE'] = '/usr/bin/chromium'
    else:
        env.pop('TASK_TRACER_BROWSER_EXECUTABLE', None)
        if engine == 'webkit':
            env['LD_LIBRARY_PATH'] = '/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu'
            env['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'
    folder = OUT / engine
    folder.mkdir(parents=True, exist_ok=True)
    command = ['python', 'tools/browser_matrix.py', '--browser', engine, '--group', 'all', '--keep-going', '--report', str(folder / 'native-report.json')]
    before = capture()
    (folder / 'inputs-before.json').write_text(json.dumps(before, indent=2) + '\n')
    at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    (folder / 'command.json').write_text(json.dumps({'command': command, 'cwd': str(ROOT), 'at': at, 'environment': {'PYTHONDONTWRITEBYTECODE': '1', 'XDG_CACHE_HOME': env['XDG_CACHE_HOME'], 'PLAYWRIGHT_BROWSERS_PATH': env['PLAYWRIGHT_BROWSERS_PATH'], 'PYTHONUNBUFFERED': '1', 'TASK_TRACER_BROWSER_EXECUTABLE': env.get('TASK_TRACER_BROWSER_EXECUTABLE'), 'TASK_TRACER_PRODUCTION_HEADERS': env.get('TASK_TRACER_PRODUCTION_HEADERS'), 'LD_LIBRARY_PATH': env.get('LD_LIBRARY_PATH'), 'PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS': env.get('PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS')}, 'http_scope': 'Original native handlers and motion; no global CSP override or wrapper.'}, indent=2) + '\n')
    with (folder / 'stdout.log').open('wb') as so, (folder / 'stderr.log').open('wb') as se:
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=so, stderr=se, start_new_session=True)
        (folder / 'worker.json').write_text(json.dumps({'pid': proc.pid, 'process_group': proc.pid, 'started_at': at}, indent=2) + '\n')
        code = proc.wait()
    after = capture()
    (folder / 'inputs-after.json').write_text(json.dumps(after, indent=2) + '\n')
    outcome = {'engine': engine, 'command': command, 'started_at': at, 'finished_at': datetime.now(timezone.utc).isoformat(), 'duration_seconds': round(time.monotonic() - started, 3), 'exit_code': code, 'source_and_tools_unchanged': before['source'] == after['source'] and before['verification'] == after['verification'], 'worker_returned': True}
    (folder / 'run-summary.json').write_text(json.dumps(outcome, indent=2) + '\n')
    return outcome

engines = sys.argv[1:] or ['webkit']
before_all = capture()
(OUT / 'webkit-inputs-initial.json').write_text(json.dumps(before_all, indent=2) + '\n')
with ThreadPoolExecutor(max_workers=2) as pool:
    pending = {pool.submit(matrix, engine): engine for engine in engines}
    results = []
    for item in as_completed(pending):
        result = item.result()
        results.append(result)
        print(json.dumps(result), flush=True)
(OUT / ('orchestration-' + '-'.join(engines) + '.json')).write_text(json.dumps({'results': results, 'max_engine_workers': 2, 'inputs_after': capture()}, indent=2) + '\n')
print('Native matrix orchestration completed.', flush=True)
