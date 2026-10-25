from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import subprocess, os, json, time, sys, hashlib

ROOT = Path('/workspace/Task-Tracer')
OUT = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/final-matrix-v3')
sys.path.insert(0, str(ROOT / 'tools'))
from check import source_identity, verification_identity
EXPECTED_INDEX, EXPECTED_SOURCE, EXPECTED_VERIFICATION = sys.argv[1:4]
assert len(sys.argv) == 4, 'Provide final frozen index/source/verification hashes'
initial_source = source_identity(); initial_verification = verification_identity()
assert initial_source['files']['index.html'] == EXPECTED_INDEX
assert initial_source['sha256'] == EXPECTED_SOURCE and initial_verification['sha256'] == EXPECTED_VERIFICATION
for group in (initial_source, initial_verification):
    for name, expected in group['files'].items():
        target = OUT / 'source-snapshot' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = (ROOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected, name
        target.write_bytes(data)
(OUT / 'frozen-inputs.json').write_text(json.dumps({'source':initial_source,'verification':initial_verification},indent=2)+'\n')

def capture():
    return {'source': source_identity(), 'verification': verification_identity(), 'vcs_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(), 'vcs_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode()}

def matrix(engine):
    if engine == 'webkit':
        old_summary = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix/webkit/run-summary.json')
        queued_at = datetime.now(timezone.utc).isoformat()
        print('Final WebKit queued until original baseline WebKit33 terminates.', flush=True)
        while not old_summary.exists():
            time.sleep(5)
        (OUT / 'webkit-start-gate.json').write_text(json.dumps({'queued_at':queued_at,'released_at':datetime.now(timezone.utc).isoformat(),'old_webkit_summary':str(old_summary),'old_webkit_summary_sha256':hashlib.sha256(old_summary.read_bytes()).hexdigest(),'rule':'At most three actual matrix engine workers across old and final runs.'},indent=2)+'\n')
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', XDG_CACHE_HOME='/workspace/.cache', PLAYWRIGHT_BROWSERS_PATH='/workspace/.cache/ms-playwright', PYTHONUNBUFFERED='1')
    env.pop('TASK_TRACER_PRODUCTION_HEADERS', None)
    env.pop('PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS', None)
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

engines = ['chromium', 'firefox', 'webkit']
before_all = capture()
(OUT / 'inputs-initial.json').write_text(json.dumps(before_all, indent=2) + '\n')
with ThreadPoolExecutor(max_workers=3) as pool:
    pending = {pool.submit(matrix, engine): engine for engine in engines}
    results = []
    for item in as_completed(pending):
        result = item.result()
        results.append(result)
        print(json.dumps(result), flush=True)
(OUT / ('orchestration-' + '-'.join(engines) + '.json')).write_text(json.dumps({'results': results, 'max_engine_workers': 3, 'inputs_after': capture()}, indent=2) + '\n')
all_native_passed = all(result['exit_code'] == 0 and result['source_and_tools_unchanged'] for result in results)
for engine in engines:
    native = json.loads((OUT / engine / 'native-report.json').read_text())
    all_native_passed = all_native_passed and native['passed'] and native['completed'] and len(native['checks']) == 33 and native['source_unchanged'] and native['verification_unchanged']
print(json.dumps({'native_orchestration_completed':True,'all_three_registered33_passed':bool(all_native_passed)}),flush=True)
raise SystemExit(0 if all_native_passed else 1)
