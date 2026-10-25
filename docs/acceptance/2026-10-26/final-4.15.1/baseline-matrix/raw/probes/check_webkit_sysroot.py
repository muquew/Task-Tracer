from pathlib import Path
from datetime import datetime, timezone
import subprocess, os, json, hashlib, sys

ROOT = Path('/workspace/task-tracer-final-baseline')
OUT = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix/probes')
WK = Path('/workspace/.cache/ms-playwright/webkit-2336/minibrowser-wpe')
LIBS = Path('/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu')
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = ':'.join([str(WK / 'lib'), str(WK / 'sys/lib'), str(LIBS)])
reports = []
for name in ['MiniBrowser', 'WPEWebProcess', 'WPEGPUProcess', 'WPENetworkProcess']:
    executable = WK / 'bin' / name
    result = subprocess.run(['ldd', str(executable)], env=env, capture_output=True, text=True)
    output = result.stdout + result.stderr
    (OUT / f'ldd-{name}.log').write_text(output)
    missing = [line for line in output.splitlines() if 'not found' in line]
    reports.append({'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(), 'exit_code': result.returncode, 'missing': missing, 'output': f'ldd-{name}.log'})
    assert result.returncode == 0 and not missing, reports[-1]
data = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'ldd_environment': {'LD_LIBRARY_PATH': env['LD_LIBRARY_PATH']}, 'all_missing_library_counts_zero': True, 'actual_sysroot_library': {'path': str(LIBS / 'libGLESv2.so.2.1.0'), 'sha256': hashlib.sha256((LIBS / 'libGLESv2.so.2.1.0').read_bytes()).hexdigest()}, 'reports': reports, 'proposed_launch_environment': {'LD_LIBRARY_PATH': str(LIBS), 'PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS': '1'}, 'preflight_scope': 'Original global ldconfig-only DLOPEN check failed; process dependencies resolve with actual preinstalled sysroot. No validator or product source modified. Official flag skips static host validation only; actual launch/render and all registered product assertions remain required.'}
(OUT / 'webkit-sysroot.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(data, indent=2))
