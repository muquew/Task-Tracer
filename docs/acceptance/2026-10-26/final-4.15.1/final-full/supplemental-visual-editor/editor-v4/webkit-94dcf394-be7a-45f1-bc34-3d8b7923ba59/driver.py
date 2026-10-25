#!/usr/bin/env python3
"""Bind one untouched original editor-safety CLI to the final 23/84 identities."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from check import source_identity, verification_identity

engine = sys.argv[1]
assert engine in ('firefox', 'webkit')
EXPECTED_INDEX = '4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4'
EXPECTED_SOURCE = sys.argv[3] if len(sys.argv) > 3 else '61ce62bb18afa3fc612ecb634f20f74ff577162ed458a12d6cf31ef840d46543'
EXPECTED_VERIFICATION = sys.argv[2] if len(sys.argv) > 2 else '6fc0d03b8437601b3f07a7304c6059d0f644b625f8c8a4213110e14a298593f3'
OUT = ROOT.parent / 'design-research/task-tracer-final-delivery-2026-10-26/final-editor-cross-engine' / (engine + '-' + str(uuid.uuid4()))
OUT.mkdir(parents=True)
shutil.copyfile(__file__, OUT / 'driver.py')
def stamp():
    return datetime.now(timezone.utc).isoformat()
def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def inputs():
    return {'source': source_identity(), 'verification': verification_identity()}
before = inputs()
save('before-identities.json', before)
assert before['source']['sha256'] == EXPECTED_SOURCE, before['source']['sha256']
assert before['verification']['sha256'] == EXPECTED_VERIFICATION, before['verification']['sha256']
assert before['source']['files']['index.html'] == EXPECTED_INDEX
assert len(before['source']['files']) == 23 and len(before['verification']['files']) == 84
for name in sorted(set(before['source']['files']) | set(before['verification']['files'])):
    dest = OUT / 'frozen-inputs' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, dest)

env = os.environ.copy()
if engine == 'webkit':
    env['LD_LIBRARY_PATH'] = '/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu'
    env['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'
command = [sys.executable, 'tools/editor_safety_playwright.py', '--browser', engine, '--case', 'all',
           '--report-dir', str(OUT / 'native'), '--expected-index-sha', EXPECTED_INDEX]
summary = {'engine': engine, 'directory': str(OUT), 'started_at': stamp(), 'command': command,
           'before': before, 'normal_csp': 'Original deployment_server; no bypass or bootstrap shim',
           'motion': 'Original default context; normal motion', 'widths': 'Original default [1280, 390]',
           'webkit_dependency_environment': {key: env[key] for key in ('LD_LIBRARY_PATH', 'PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS')} if engine == 'webkit' else None}
save('summary.json', summary)
print(json.dumps({'started': True, 'directory': str(OUT), 'command': command, 'source': EXPECTED_SOURCE, 'verification': EXPECTED_VERIFICATION}), flush=True)
start = time.monotonic()
with (OUT / 'stdout.log').open('wb') as stdout, (OUT / 'stderr.log').open('wb') as stderr:
    process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
after = inputs()
save('after-identities.json', after)
native_reports = list((OUT / 'native').glob('*/results.json'))
summary.update({'exit_code': process.returncode, 'after': after, 'identities_stable': before == after,
                'finished_at': stamp(), 'duration_seconds': round(time.monotonic() - start, 3)})
if len(native_reports) == 1:
    native = json.loads(native_reports[0].read_text())
    summary['native_report'] = str(native_reports[0].relative_to(OUT))
    summary['browser_version'] = native.get('native_browser_version')
    summary['native_results'] = native.get('results', [])
    summary['all_ten_native_cases_passed'] = len(summary['native_results']) == 10 and all(case['status'] == 'passed' for case in summary['native_results'])
else:
    summary['all_ten_native_cases_passed'] = False
summary['passed'] = process.returncode == 0 and summary['identities_stable'] and summary['all_ten_native_cases_passed']
save('summary.json', summary)
manifest = {path.relative_to(OUT).as_posix(): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
            for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'files.json'}
save('files.json', manifest)
print(json.dumps({'engine': engine, 'directory': str(OUT), 'exit_code': process.returncode, 'identities_stable': summary['identities_stable'], 'all_ten_native_cases_passed': summary['all_ten_native_cases_passed'], 'passed': summary['passed'], 'duration_seconds': summary['duration_seconds']}), flush=True)
raise SystemExit(0 if summary['passed'] else 1)
