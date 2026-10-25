from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/workspace/Task-Tracer')
OUT = Path(__file__).resolve().parent
RUNTIME = ['index.html', 'resources/en.json', 'resources/zh-CN.json', 'sw.js', 'vercel.json']
TOOLS = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'tools').rglob('*.py'))

def snapshot(names):
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}

def stamp():
    return datetime.now(timezone.utc).isoformat()

def publish(data):
    tmp = OUT / 'run.json.tmp'
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(OUT / 'run.json')

record = {
    'command': [sys.executable, 'tools/accessibility_i18n_audit.py'],
    'cwd': str(ROOT),
    'started_at': stamp(),
    'runtime_initial': snapshot(RUNTIME),
    'tools_initial': snapshot(TOOLS),
    'axe_initial_sha256': hashlib.sha256((ROOT / 'node_modules/axe-core/axe.min.js').read_bytes()).hexdigest(),
    'original_full_scaled_scope': True,
    'viewport_option': 'both default',
    'skip_scaled': False,
    'collect_axe': False,
    'status': 'running',
    'selected_environment': {key: os.environ.get(key) for key in ('TASK_TRACER_PRODUCTION_HEADERS', 'TASK_TRACER_URL', 'TASK_TRACER_BROWSER_EXECUTABLE')},
    'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
assert record['runtime_initial']['index.html'] == '4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4'
publish(record)
started = time.monotonic()
with (OUT / 'stdout.log').open('wb') as stdout, (OUT / 'stderr.log').open('wb') as stderr:
    child = subprocess.Popen(record['command'], cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
    record['worker_pid'] = child.pid
    publish(record)
    code = child.wait()
record.update({'finished_at': stamp(), 'duration_seconds': round(time.monotonic() - started, 3), 'exit_code': code,
               'runtime_final': snapshot(RUNTIME), 'tools_final': snapshot(TOOLS),
               'axe_final_sha256': hashlib.sha256((ROOT / 'node_modules/axe-core/axe.min.js').read_bytes()).hexdigest()})
record['runtime_unchanged'] = record['runtime_initial'] == record['runtime_final']
record['tools_unchanged'] = record['tools_initial'] == record['tools_final']
record['axe_unchanged'] = record['axe_initial_sha256'] == record['axe_final_sha256']
text = (OUT / 'stdout.log').read_text()
record['native_state_observations'] = sum(line.startswith('Accessibility state: ') for line in text.splitlines())
record['workflow_completed'] = [line for line in text.splitlines() if line.startswith('Accessibility workflow completed: ')]
record['native_pass_line'] = 'Accessibility/i18n audit passed' in text.splitlines()
record['status'] = 'passed' if code == 0 and record['runtime_unchanged'] and record['tools_unchanged'] and record['axe_unchanged'] else 'failed'
for name in ('stdout.log', 'stderr.log'):
    p = OUT / name
    record.setdefault('outputs', {})[name] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
publish(record)
print(json.dumps({key: record[key] for key in ('status', 'exit_code', 'duration_seconds', 'native_state_observations', 'runtime_unchanged', 'tools_unchanged', 'native_pass_line')}), flush=True)
raise SystemExit(code if code else (0 if record['status'] == 'passed' else 1))
