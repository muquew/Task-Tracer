python - <<'PY'
import json, math, os, re
from pathlib import Path

checks, planned, status, report = [], None, 'missing', {}
try:
    path = Path('dist/check-results.json')
    if path.is_symlink() or path.stat().st_size > 2_000_000:
        raise ValueError
    report = json.loads(path.read_text(encoding='utf-8'))
    checks, planned = report['checks'], report['planned_checks']
    if not isinstance(checks, list) or not isinstance(planned, list):
        raise ValueError
    status = report.get('status', 'invalid')
    if status not in {'initializing', 'running', 'passed', 'failed', 'interrupted', 'error'}:
        status = 'invalid'
except FileNotFoundError:
    pass
except (OSError, ValueError, TypeError, KeyError):
    checks, planned, status, report = [], None, 'invalid', {}

known = {path.name for path in Path('tools').glob('*.py')
         if re.fullmatch(r'[a-z][a-z0-9_]{0,79}\.py', path.name)}
rows, all_zero = [], True
for item in checks[:100]:
    item = item if isinstance(item, dict) else {}
    program = item.get('program')
    name = Path(program).name if isinstance(program, str) else ''
    name = name if name in known else 'unknown-program'
    code = item.get('exit_code')
    valid_code = type(code) is int and -255 <= code <= 255
    duration = item.get('duration_seconds')
    valid_duration = type(duration) in (int, float) and 0 <= duration <= 86400 and math.isfinite(duration)
    shown_duration = f'{duration:.3f}s' if valid_duration else 'unknown'
    rows.append(f'| `{name}` | {code if valid_code else "unknown"} | {shown_duration} |')
    all_zero = all_zero and valid_code and code == 0 and name != 'unknown-program'
    if valid_code and code != 0:
        print(f'::error::{name} exit={code}')
if status == 'passed' and not (report.get('completed') is True and report.get('passed') is True
        and planned and len(checks) == len(planned) and len(checks) <= 100 and all_zero):
    status = 'incomplete'
count = f'{len(checks)}/{len(planned)}' if planned is not None else '0/unknown'
lines = ['## Check program outcomes', '', f'Status: {status}. Executed/planned: {count}.', '',
         '| Program | Exit | Duration |', '| --- | ---: | ---: |', *rows]
if len(checks) > 100:
    lines += ['', 'Only the first 100 executed programs are shown.']
with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
    summary.write('\n'.join(lines) + '\n')
PY
