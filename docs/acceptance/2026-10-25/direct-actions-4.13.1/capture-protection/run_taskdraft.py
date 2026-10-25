import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

root = pathlib.Path('/workspace/Task-Tracer')
output = pathlib.Path('/tmp/4.13.1-capture-final/taskdraft')
source = root / 'index.html'
started = time.perf_counter()
report = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'index_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'command': [sys.executable, 'tools/task_draft_playwright.py', '--case', 'all'],
          'passed': False}
with (output / 'run.log').open('w') as log:
    result = subprocess.run(report['command'], cwd=root, stdout=log, stderr=subprocess.STDOUT)
report['exit_code'] = result.returncode
report['final_index_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
report['passed'] = result.returncode == 0 and report['final_index_sha256'] == report['index_sha256']
report['seconds'] = round(time.perf_counter() - started, 2)
report['completed_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
sys.exit(0 if report['passed'] else 1)
