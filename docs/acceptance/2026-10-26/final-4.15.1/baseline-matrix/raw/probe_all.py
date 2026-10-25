from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import subprocess, os, json, time

ROOT = Path('/workspace/task-tracer-final-baseline')
OUT = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix/probes')
OUT.mkdir(parents=True, exist_ok=True)

def probe(engine):
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', XDG_CACHE_HOME='/workspace/.cache', PLAYWRIGHT_BROWSERS_PATH='/workspace/.cache/ms-playwright', PYTHONUNBUFFERED='1')
    if engine == 'chromium':
        env['TASK_TRACER_BROWSER_EXECUTABLE'] = '/usr/bin/chromium'
    else:
        env.pop('TASK_TRACER_BROWSER_EXECUTABLE', None)
    cmd = ['python', 'tools/browser_matrix.py', '--probe-browser', engine]
    start = time.monotonic()
    with (OUT / f'{engine}.stdout.log').open('wb') as so, (OUT / f'{engine}.stderr.log').open('wb') as se:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=so, stderr=se)
    data = {'engine': engine, 'command': cmd, 'exit_code': result.returncode, 'duration_seconds': round(time.monotonic() - start, 3), 'stdout': f'{engine}.stdout.log', 'stderr': f'{engine}.stderr.log'}
    (OUT / f'{engine}.json').write_text(json.dumps(data, indent=2) + '\n')
    return data

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(probe, ['firefox', 'webkit']))
(OUT / 'summary.json').write_text(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'results': results}, indent=2) + '\n')
print(json.dumps(results, indent=2))
