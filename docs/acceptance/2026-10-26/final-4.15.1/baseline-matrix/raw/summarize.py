from pathlib import Path
from datetime import datetime, timezone
import json, hashlib

BASE = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix')
summary = {'kind': 'derived_diagnostic_baseline_matrix_summary', 'generated_at': datetime.now(timezone.utc).isoformat(), 'checkout': '/workspace/task-tracer-final-baseline', 'baseline_commit': '54b95cce891d167617d42bc489cdc801317f00c5', 'planned_engines': ['chromium', 'firefox', 'webkit'], 'registered_programs_per_engine': 33, 'maximum_engine_workers': 2, 'final_delivery_claim': False, 'engines': {}}
for engine in summary['planned_engines']:
    p = BASE / engine / 'native-report.json'
    if not p.exists():
        summary['engines'][engine] = {'status': 'queued', 'executed_programs': 0}
        continue
    d = json.loads(p.read_text())
    checks = d['checks']
    worker_path = BASE / engine / 'run-summary.json'
    summary['engines'][engine] = {'status': d['status'], 'native_completed': d['completed'], 'native_passed': d['passed'], 'native_report': str(p.relative_to(BASE)), 'native_report_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'browser': d['browsers'][engine], 'executed_programs': len(checks), 'passed_programs': sum(x['exit_code'] == 0 for x in checks), 'failures': [{key: x[key] for key in ['program', 'exit_code', 'duration_seconds', 'log']} for x in checks if x['exit_code']], 'unexecuted_checks': d['unexecuted_checks'], 'current_check': d['current_check'], 'source_unchanged': d['source_unchanged'], 'verification_unchanged': d['verification_unchanged'], 'source_sha256': d['source']['sha256'], 'verification_sha256': d['verification']['sha256'], 'coverage_exceptions': d['scope']['coverage_exceptions'], 'runner_summary': json.loads(worker_path.read_text()) if worker_path.exists() else None}
summary['all_engines_completed'] = all(v.get('native_completed') for v in summary['engines'].values())
summary['all_engines_passed'] = all(v.get('native_passed') for v in summary['engines'].values())
summary['webkit_environment'] = {'LD_LIBRARY_PATH': '/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu', 'PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS': '1', 'actual_ldd_and_render_probe': 'probes/webkit-sysroot.json and probes/webkit-actual-render.json', 'note': 'Initial global ldconfig DLOPEN host precheck failed. Superuser install unavailable. Real cached dependencies resolve, actual WebKit renders; official flag skips static host precheck only, with original33 product assertions retained. System dependencies were not installed.'}
summary['limits'] = ['This is an isolated original4.15.0 diagnostic baseline, not a newer source or tool result.', 'Completed means each registered program was invoked; a failed program may stop its own remaining internal subcases.', 'Original native HTTP and motion are unchanged; no global deployment-CSP override.', 'Browser engines and simulated viewports are Linux environments, not physical-device or Safari/iOS certification.']
(BASE / 'baseline-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({engine: {key: value.get(key) for key in ['status', 'executed_programs', 'passed_programs']} for engine, value in summary['engines'].items()}, indent=2))
