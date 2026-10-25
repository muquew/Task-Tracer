"""External 4.9.0 acceptance support. Importing this module performs no I/O."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
ROOT = Path('/workspace/Task-Tracer-redesign')
SITE = 'https://todo.muquew.com/'
VERSION = '4.9.0'
RESOURCE_VERSION = '4.37'
CACHE_NAME = 'task-tracer-v4.9.0'
DEFAULT_OUTPUT = Path('/workspace/design-research/task-tracer-2026-10-25/production-4.9.0')
SAFE_HEADERS = ('date', 'age', 'cache-control', 'content-type', 'content-security-policy',
                'referrer-policy', 'x-content-type-options', 'x-frame-options',
                'permissions-policy', 'strict-transport-security', 'x-vercel-cache', 'x-vercel-id', 'etag')
EXPECTED_ASSETS = {
    'THIRD_PARTY_NOTICES.md', 'fav/android-chrome-192x192.png',
    'fav/android-chrome-512x512.png', 'fav/apple-touch-icon.png',
    'fav/favicon-16x16.png', 'fav/favicon-32x32.png', 'fav/favicon.ico',
    'index.html', 'manifest.json', 'resources/en.json?v=4.37',
    'resources/zh-CN.json?v=4.37', 'resources/en.json', 'resources/zh-CN.json', 'sw.js',
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.PIPE)


def base_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--start', action='store_true', help='Required: execute only after explicit final freeze/push signal')
    parser.add_argument('--freeze', type=Path, default=os.environ.get('TASK_TRACER_ACCEPTANCE_FREEZE_PATH'))
    parser.add_argument('--app-commit', default=os.environ.get('TASK_TRACER_APPLICATION_COMMIT'))
    parser.add_argument('--freeze-sha256', help='Optional externally supplied SHA256 of the exact freeze JSON bytes')
    parser.add_argument('--output-root', type=Path, default=DEFAULT_OUTPUT)
    return parser


def require_execution(parser, args):
    if not args.start:
        parser.error('Preparation is inert: --start requires the final freeze and publication signal')
    if args.freeze is None or not args.app_commit:
        parser.error('--freeze and --app-commit (or their documented environment variables) are required')
    if not re.fullmatch(r'[0-9a-f]{40}', args.app_commit):
        parser.error('--app-commit must be an exact lowercase 40-character Git commit')
    if args.freeze_sha256 and not re.fullmatch(r'[0-9a-f]{64}', args.freeze_sha256):
        parser.error('--freeze-sha256 must be a lowercase SHA256')
    output = args.output_root.resolve()
    allowed = (Path('/workspace/design-research/task-tracer-2026-10-25').resolve(), Path('/tmp').resolve())
    if not any(output.is_relative_to(root) for root in allowed) or output.is_relative_to(ROOT.resolve()):
        parser.error('Output must stay in the authorized external research directory or /tmp')


def inherited_proxy():
    value = os.environ.get('HTTPS_PROXY')
    if not value:
        raise RuntimeError('Inherited HTTPS_PROXY is required; no direct-network fallback')
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise RuntimeError('Inherited proxy must be the configured plain-HTTP sidecar URL without inline credentials')
    return {'server': value, 'bypass': '127.0.0.1,localhost'}


def normalize_csp(value):
    return {part.split()[0]: set(part.split()[1:]) for part in value.split(';') if part.strip()}


class AcceptedCandidate:
    def __init__(self, args):
        self.freeze_path = Path(args.freeze).resolve(strict=True)
        self.freeze_raw = self.freeze_path.read_bytes()
        self.freeze_sha256 = sha(self.freeze_raw)
        if args.freeze_sha256 and self.freeze_sha256 != args.freeze_sha256:
            raise AssertionError('Freeze JSON differs from the explicitly supplied SHA256')
        document = json.loads(self.freeze_raw)
        self.freeze = document['input_capture']['freeze'] if 'input_capture' in document else document
        assert self.freeze.get('app_version') == VERSION, 'Refuse a freeze from another app version'
        self.commit = args.app_commit
        sys.path.insert(0, str(ROOT / 'tools'))
        from check import atomic_report, source_identity, verification_identity
        from validate_static import app_version
        from verify_deployment import deployment_assets
        self.atomic_report = atomic_report
        self.source_identity, self.verification_identity = source_identity, verification_identity
        assert app_version((ROOT / 'index.html').read_text()) == VERSION, 'Wrong checkout app version'
        html = (ROOT / 'index.html').read_text()
        assert re.search(r"\bRESOURCE_VERSION\s*:\s*['\"]4\.37['\"]", html), 'Wrong checkout resource version'
        worker = (ROOT / 'sw.js').read_text()
        assert re.search(r"\bCACHE_NAME\s*=\s*['\"]task-tracer-v4\.9\.0['\"]", worker), 'Wrong worker cache version'
        assert set(deployment_assets()) == EXPECTED_ASSETS, 'Expected root plus exactly 14 declared 4.9.0 asset URLs'
        self.check()
        for identity in (self.freeze['source'], self.freeze['verification']):
            for name, digest in identity['files'].items():
                assert sha(git('show', f'{self.commit}:{name}')) == digest, f'Git candidate blob differs: {name}'

    def check(self):
        assert self.freeze_path.read_bytes() == self.freeze_raw, 'Freeze JSON changed during execution'
        assert git('rev-parse', 'HEAD').decode().strip() == self.commit, 'HEAD differs from the supplied application commit'
        assert self.source_identity() == self.freeze['source'], 'Frozen source bytes differ'
        assert self.verification_identity() == self.freeze['verification'], 'Frozen verification bytes differ'

    def record(self):
        return {'site': SITE, 'app_version': VERSION, 'resource_version': RESOURCE_VERSION,
                'cache_name': CACHE_NAME, 'application_source_commit': self.commit,
                'freeze_path': str(self.freeze_path), 'freeze_bytes': len(self.freeze_raw),
                'freeze_sha256': self.freeze_sha256, 'source': self.source_identity(),
                'verification': self.verification_identity(), 'git_candidate_blobs_match': True}

    def finish_identity(self, record):
        record['source_final'] = self.source_identity()
        record['verification_final'] = self.verification_identity()
        record['source_unchanged'] = record['source_final'] == self.freeze['source'] == record['source']
        record['verification_unchanged'] = record['verification_final'] == self.freeze['verification'] == record['verification']
        self.check()
        assert record['source_unchanged'] and record['verification_unchanged']


def archive_preparation(candidate, directory, runner, extra=()):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'freeze.json').write_bytes(candidate.freeze_raw)
    for path in (Path(runner), Path(__file__), *map(Path, extra)):
        (directory / path.name).write_bytes(path.read_bytes())


def seal(directory, atomic_report):
    inventory = {path.relative_to(directory).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
                 for path in sorted(directory.rglob('*')) if path.is_file() and path.name != 'evidence-sha256.json'}
    atomic_report(directory / 'evidence-sha256.json', inventory)
