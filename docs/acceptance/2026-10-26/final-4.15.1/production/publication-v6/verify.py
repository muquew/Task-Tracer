#!/usr/bin/env python3
"""Run unchanged native deployment verification plus six public documentation/images."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from verify_deployment import verify

BASE = 'https://todo.muquew.com/'
EXPECTED_INDEX = '89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30'
EXTRA = ('screenshots/task-list.png', 'screenshots/add-task.png',
         'screenshots/task-list-en.png', 'screenshots/add-task-en.png',
         'docs/distribution.md', 'docs/distribution_zh_cn.md')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise RuntimeError('Use a new report path for each observation')
    before = {name: sha((ROOT / name).read_bytes()) for name in ('index.html', 'vercel.json', *EXTRA)}
    assert before['index.html'] == EXPECTED_INDEX
    report = {'started_at': datetime.now(timezone.utc).isoformat(),
              'site': BASE, 'index_sha256': EXPECTED_INDEX, 'passed': False,
              'normal_tls': True, 'native': None, 'extra': [], 'source_before': before}
    try:
        report['native'] = verify(BASE)
        for name in EXTRA:
            with urlopen(BASE + name, timeout=20) as response:
                payload = response.read()
                item = {'path': name, 'status': response.status,
                        'bytes': len(payload), 'sha256': sha(payload)}
                report['extra'].append(item)
                assert response.status == 200
                assert item['sha256'] == before[name], 'Deployed asset differs: ' + name
        after = {name: sha((ROOT / name).read_bytes()) for name in before}
        report['source_after'] = after
        assert before == after
        report['passed'] = True
    except Exception as exc:
        report['error'] = {'class': type(exc).__name__, 'message': str(exc)}
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'report': str(output),
                      'native_responses': len((report['native'] or {}).get('checked', [])),
                      'extra_responses': len(report['extra']), 'error': report.get('error')}, ensure_ascii=False))
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
