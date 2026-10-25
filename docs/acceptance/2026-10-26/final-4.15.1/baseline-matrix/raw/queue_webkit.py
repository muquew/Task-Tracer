from pathlib import Path
from datetime import datetime, timezone
import subprocess, time, json, os

OUT = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix')
ROOT = Path('/workspace/task-tracer-final-baseline')
start = datetime.now(timezone.utc).isoformat()
print('WebKit queued until one initial engine completes; maximum two engine workers.', flush=True)
while not any((OUT / engine / 'run-summary.json').exists() for engine in ['chromium', 'firefox']):
    time.sleep(10)
at = datetime.now(timezone.utc).isoformat()
(OUT / 'webkit-queue.json').write_text(json.dumps({'queued_at': start, 'started_at': at, 'gate': 'At least one Chromium/Firefox runner has returned and saved its summary.', 'max_engine_workers': 2}, indent=2) + '\n')
print('Starting queued WebKit full33 registry.', flush=True)
with (OUT / 'webkit-orchestrator.stdout.log').open('wb') as so, (OUT / 'webkit-orchestrator.stderr.log').open('wb') as se:
    result = subprocess.run(['python', str(OUT / 'run_webkit_matrix.py'), 'webkit'], cwd=ROOT, env=os.environ.copy(), stdout=so, stderr=se)
print(json.dumps({'webkit_orchestrator_exit': result.returncode, 'finished_at': datetime.now(timezone.utc).isoformat()}), flush=True)
raise SystemExit(result.returncode)
