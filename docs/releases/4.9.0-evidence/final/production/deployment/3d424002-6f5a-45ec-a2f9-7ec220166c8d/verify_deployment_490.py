"""External 4.9.0 native deployment polling and exact-response evidence. Inert without --start."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from urllib.parse import urljoin
import uuid

sys.dont_write_bytecode = True
from release_490_common import (AcceptedCandidate, ROOT, SAFE_HEADERS, SITE, VERSION,
    archive_preparation, base_parser, inherited_proxy, now, require_execution, seal, sha)


def run(args):
    candidate = AcceptedCandidate(args)
    inherited_proxy()
    import verify_deployment as native
    directory = args.output_root / 'deployment' / str(uuid.uuid4())
    archive_preparation(candidate, directory, __file__)
    (directory / 'assets').mkdir()
    record = {**candidate.record(), 'schema_version': 1, 'run_id': directory.name,
              'started_at': now(), 'finished_at': None, 'status': 'waiting', 'completed': False,
              'passed': False, 'attempts': [], 'observation_requests': [], 'error': None,
              'scope': 'Unmodified native deployment CLI plus exact-response observation: 15 bodies and configured headers/CSP. No browser, remote CI or Vercel backend Git-metadata claim.',
              'tls_verification_enabled': True, 'proxy_inherited': True,
              'application_cache_overrides': False}
    report_path = directory / 'report.json'
    publish = lambda: candidate.atomic_report(report_path, record)
    publish()
    print('EVIDENCE_DIRECTORY=' + str(directory), flush=True)
    started = time.monotonic()
    try:
        while True:
            candidate.check()
            number = len(record['attempts']) + 1
            prefix = f'attempt-{number:02d}'
            attempt = {'number': number, 'started_at': now(), 'exit_code': None,
                       'stdout': prefix + '.stdout.log', 'stderr': prefix + '.stderr.log'}
            try:
                result = subprocess.run([sys.executable, str(ROOT / 'tools/verify_deployment.py'), '--url', SITE],
                    cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                    capture_output=True, text=True, timeout=360)
            except subprocess.TimeoutExpired as error:
                def decoded(value):
                    return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
                (directory / attempt['stdout']).write_text(decoded(error.stdout))
                (directory / attempt['stderr']).write_text(decoded(error.stderr))
                attempt.update(finished_at=now(), status='native_timeout', timeout_seconds=360)
                record['attempts'].append(attempt)
                publish()
                raise
            (directory / attempt['stdout']).write_text(result.stdout)
            (directory / attempt['stderr']).write_text(result.stderr)
            attempt.update(finished_at=now(), exit_code=result.returncode,
                           status='matched' if result.returncode == 0 else 'pending_or_mismatch')
            if result.returncode == 0:
                attempt['native_result'] = json.loads(result.stdout)
                assert attempt['native_result']['passed'] and attempt['native_result']['version'] == VERSION
                assert len(attempt['native_result']['checked']) == 15
            record['attempts'].append(attempt)
            publish()
            print(json.dumps({'attempt': number, 'status': attempt['status'], 'at': attempt['finished_at']}), flush=True)
            if result.returncode == 0:
                record['first_native_pass_at'] = attempt['finished_at']
                break
            elapsed = time.monotonic() - started
            if elapsed >= args.wait_seconds:
                raise TimeoutError('No matching deployment within the configured bounded polling period')
            time.sleep(min(args.interval, args.wait_seconds - elapsed))
        candidate.check()
        original_open = native.urlopen

        class ObservedResponse:
            def __init__(self, request_url, *positional, **named):
                self.request_url, self.positional, self.named = request_url, positional, named

            def __enter__(self):
                self.response = original_open(self.request_url, *self.positional, **self.named)
                self.response.__enter__()
                self.headers = self.response.headers
                return self

            def __exit__(self, *values):
                return self.response.__exit__(*values)

            def read(self):
                raw = self.response.read()
                relative = f'assets/matched-{len(record["observation_requests"]) + 1:02d}.bin'
                (directory / relative).write_bytes(raw)
                record['observation_requests'].append({'request_url': self.request_url,
                    'final_url': self.response.geturl(), 'status': self.response.status, 'at': now(),
                    'bytes': len(raw), 'sha256': sha(raw), 'body_file': relative,
                    'headers': {key: self.headers.get(key) for key in SAFE_HEADERS if self.headers.get(key) is not None}})
                return raw

        native.urlopen = ObservedResponse
        try:
            record['observed_native_verify'] = native.verify(SITE)
        finally:
            native.urlopen = original_open
        expected = {'': ROOT / 'index.html', **native.deployment_assets()}
        assert len(expected) == len(record['observation_requests']) == 15
        for response, (url_path, source) in zip(record['observation_requests'], expected.items()):
            assert response['request_url'] == response['final_url'] == urljoin(SITE, url_path)
            assert response['status'] == 200
            response['local_file'] = source.relative_to(ROOT).as_posix()
            response['local_sha256'] = sha(source.read_bytes())
            response['bytes_equal'] = response['sha256'] == response['local_sha256']
            assert response['bytes_equal'], url_path
        candidate.finish_identity(record)
        record.update(status='passed', passed=True)
    except BaseException as error:
        record.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    finally:
        try:
            candidate.finish_identity(record)
        except BaseException as error:
            record.update(status='failed', passed=False, identity_error=f'{type(error).__name__}: {error}')
        record.update(completed=True, finished_at=now())
        publish()
        seal(directory, candidate.atomic_report)
        print(json.dumps({'status': record['status'], 'passed': record['passed'], 'report': str(report_path)}), flush=True)
    return 0 if record['passed'] else 1


def main():
    parser = base_parser(__doc__)
    parser.add_argument('--wait-seconds', type=int, default=600)
    parser.add_argument('--interval', type=int, default=25)
    args = parser.parse_args()
    require_execution(parser, args)
    if not 0 <= args.wait_seconds <= 1800 or not 1 <= args.interval <= 30:
        parser.error('wait-seconds must be 0..1800; interval must be 1..30 seconds')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
