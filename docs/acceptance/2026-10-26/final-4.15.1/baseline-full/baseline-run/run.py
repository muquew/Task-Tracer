from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/workspace/task-tracer-final-baseline')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from check import source_identity, verification_identity

def stamp():
    return datetime.now(timezone.utc).isoformat()

def publish(data):
    temporary = OUT / 'run.json.tmp'
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(OUT / 'run.json')

command = [sys.executable, 'tools/check.py', '--keep-going', '--report', str(OUT / 'full.json')]
record = {
    'command': command,
    'cwd': str(ROOT),
    'started_at': stamp(),
    'source_initial': source_identity(),
    'verification_initial': verification_identity(),
    'vcs_initial': {
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode(),
    },
    'selected_environment': {key: os.environ.get(key) for key in (
        'PYTHONDONTWRITEBYTECODE', 'TASK_TRACER_BROWSER_EXECUTABLE', 'XDG_CACHE_HOME',
        'PLAYWRIGHT_BROWSERS_PATH', 'PYTHONUNBUFFERED', 'TASK_TRACER_PRODUCTION_HEADERS',
        'TASK_TRACER_BROWSER',
    )},
    'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'status': 'running',
}
publish(record)
started = time.monotonic()
with (OUT / 'stdout.log').open('wb') as stdout, (OUT / 'stderr.log').open('wb') as stderr:
    process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
    record['checker_pid'] = process.pid
    publish(record)
    code = process.wait()
record.update({
    'finished_at': stamp(),
    'duration_seconds': round(time.monotonic() - started, 3),
    'exit_code': code,
    'source_final': source_identity(),
    'verification_final': verification_identity(),
    'vcs_final': {
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode(),
    },
})
record['source_unchanged'] = record['source_initial'] == record['source_final']
record['verification_unchanged'] = record['verification_initial'] == record['verification_final']
record['status'] = 'passed' if code == 0 and record['source_unchanged'] and record['verification_unchanged'] else 'failed'
for name in ('stdout.log', 'stderr.log', 'full.json'):
    file = OUT / name
    if file.exists():
        record.setdefault('outputs', {})[name] = {'bytes': file.stat().st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
publish(record)
print(json.dumps({key: record[key] for key in ('status', 'exit_code', 'duration_seconds', 'source_unchanged', 'verification_unchanged')}), flush=True)
raise SystemExit(code if code else (0 if record['status'] == 'passed' else 1))
