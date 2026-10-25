"""Default is read-only dry-run; --execute requires the parent's explicit GO."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, tempfile, uuid, zipfile
sys.dont_write_bytecode = True
R = Path('/workspace/Task-Tracer')
B = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/release-proof/v6')
sys.path.insert(0, str(R / 'tools'))
from check import source_identity, verification_identity
from build_release import DISTRIBUTION_SOURCES, expected_distribution_files
HEAD = '6a3b8e61ba0699cc316fd92a247cc9c917a7521d'
SOURCE = '58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54'
VERIFY = '1d0a6604a369bd42c75045692eb11536ae9636ee6f4320a0d4e07c4a65ca9561'
DIGEST = '0540eca3d0d83a140c3695f575e24e6c73252afe08e5ae2f4f3457cef4691aca'
OLD_DIGEST = '02cc67c9ac2a454b9ca248c3a122f92060c674677914dfab567cd7de5f6fbca3'
ZIP = B / 'canonical-prepared/0ebbd959-fe4e-4824-8b5d-80a571619dfa/one/task-tracer-4.15.1.zip'
SIDE = ZIP.with_suffix('.zip.sha256')
OLD = R / 'dist/task-tracer-4.15.0.zip'
sha = lambda data: hashlib.sha256(data).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=R, text=True).strip()

def identity():
    s, v = source_identity(), verification_identity()
    assert git('rev-parse', 'HEAD') == HEAD and s['sha256'] == SOURCE and v['sha256'] == VERIFY
    assert len(s['files']) == 23 and len(v['files']) == 84
    assert all(not n.startswith(('dist/', 'downloads/')) for group in (s, v) for n in group['files'])
    return {'head': HEAD, 'source': s, 'verification': v}

def package(path):
    assert path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == DIGEST
    with zipfile.ZipFile(path) as archive:
        assert len(archive.namelist()) == 24 and set(archive.namelist()) == expected_distribution_files()
        raw_manifest = archive.read('integrity.json')
        manifest = json.loads(raw_manifest)
        assert manifest['version'] == '4.15.1' and manifest['commit'] == HEAD and manifest['working_tree_dirty'] is False
        assert set(manifest['files']) == set(DISTRIBUTION_SOURCES)
        for target, source in DISTRIBUTION_SOURCES.items():
            data = (R / source).read_bytes()
            if target in ('README.md', 'README_zh_cn.md'):
                data = data.replace(b'](../LICENSE)', b'](LICENSE)')
            assert archive.read(target) == data and sha(data) == manifest['files'][target]
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': DIGEST, 'files': 24,
            'manifest_sha256': sha(raw_manifest), 'manifest': manifest, 'all23_payload_bytes_match_primary': True}

def old_package():
    data = OLD.read_bytes()
    assert sha(data) == OLD_DIGEST and len(data) == 990442
    with zipfile.ZipFile(OLD) as archive:
        manifest = json.loads(archive.read('integrity.json'))
        assert len(archive.namelist()) == 24 and manifest['version'] == '4.15.0'
        assert manifest['commit'] == '93c990012deaf8556517cbc5995dfebfd2a2a952' and manifest['working_tree_dirty'] is False
        assert set(archive.namelist()) == set(manifest['files']) | {'integrity.json'}
        assert all(sha(archive.read(name)) == digest for name, digest in manifest['files'].items())
    return {'path': str(OLD), 'bytes': len(data), 'sha256': OLD_DIGEST, 'files': 24,
            'manifest_commit': manifest['commit'], 'manifest_dirty': False}

def targets():
    result = []
    for directory in ('dist', 'downloads'):
        folder = R / directory
        assert not folder.is_symlink() and (not folder.exists() or folder.is_dir())
        for source in (ZIP, SIDE):
            dest = folder / source.name
            assert not dest.is_symlink() and (not dest.exists() or dest.is_file())
            relative = dest.relative_to(R).as_posix()
            rule = subprocess.run(['git', 'check-ignore', '-v', '--no-index', '--', relative], cwd=R, text=True, capture_output=True)
            assert rule.returncode in (0, 1) and (rule.returncode == 0) == (directory == 'dist')
            digest = sha(source.read_bytes())
            assert not dest.exists() or sha(dest.read_bytes()) == digest, 'Existing target conflicts with the frozen clean package'
            result.append({'source_path': str(source), 'target_path': str(dest), 'bytes': source.stat().st_size,
                           'sha256': digest, 'exists': dest.exists(), 'ignored': rule.returncode == 0,
                           'ignore_rule': rule.stdout.strip(), 'tracked_intended': directory == 'downloads'})
    tracked = git('ls-files', '--', *(Path(x['target_path']).relative_to(R).as_posix() for x in result)).splitlines()
    assert not any(name.startswith('dist/') for name in tracked)
    return {'files': result, 'tracked_targets_before': tracked,
            'downloads_directory_exists': (R / 'downloads').exists(),
            'both_destination_directories_excluded_from107': True}

assert len(sys.argv) <= 2 and (len(sys.argv) == 1 or sys.argv[1] in ('--dry-run', '--execute'))
execute = len(sys.argv) == 2 and sys.argv[1] == '--execute'
P = B / ('copy-execution' if execute else 'copy-preparation') / str(uuid.uuid4())
P.mkdir(parents=True)
record = {'started_at': now(), 'mode': 'execute' if execute else 'dry-run', 'status': 'initializing',
          'copy_executed': False, 'git_stage_or_commit_executed': False, 'publish_executed': False,
          'writes': [], 'error': None, 'explicit_parent_GO_required_before_execute': True}
original_temp = []
try:
    before = identity()
    canonical = package(ZIP)
    checksum_bytes = SIDE.read_bytes()
    assert not SIDE.is_symlink() and checksum_bytes == (DIGEST + '  ' + ZIP.name + '\n').encode()
    old = old_package()
    plan = targets()
    record.update(before=before, canonical=canonical,
                  source_sidecar={'path': str(SIDE), 'bytes': len(checksum_bytes), 'sha256': sha(checksum_bytes), 'content': checksum_bytes.decode()},
                  old_package_before=old, plan=plan)
    if execute:
        prepared = []
        for item in plan['files']:
            dest = Path(item['target_path'])
            dest.parent.mkdir(exist_ok=True)
            assert not dest.parent.is_symlink() and not dest.is_symlink()
            if dest.exists():
                assert sha(dest.read_bytes()) == item['sha256']
                continue
            with tempfile.NamedTemporaryFile(dir=dest.parent, prefix='.task-tracer-4.15.1-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                original_temp.append(temporary)
                stream.write(Path(item['source_path']).read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            assert sha(temporary.read_bytes()) == item['sha256']
            prepared.append((temporary, dest))
        for temporary, dest in prepared:
            assert not dest.exists() and not dest.is_symlink()
            os.replace(temporary, dest)
            record['writes'].append(str(dest))
        for item in plan['files']:
            dest = Path(item['target_path'])
            assert dest.read_bytes() == Path(item['source_path']).read_bytes()
            assert len(dest.read_bytes()) == item['bytes'] and sha(dest.read_bytes()) == item['sha256']
        record['destination_packages'] = [package(R / directory / ZIP.name) for directory in ('dist', 'downloads')]
        record['copy_executed'] = True
    record['after'] = identity()
    record['old_package_after'] = old_package()
    record['targets_after'] = targets()
    assert record['after'] == before and record['old_package_after'] == old
    record['all107_and_HEAD_unchanged'] = True
    record['primary_target_status'] = git('status', '--short', '--untracked-files=all', '--', *(Path(x['target_path']).relative_to(R).as_posix() for x in plan['files']))
    record['status'] = 'copied_and_verified_not_published' if execute else 'dry_run_ready_waiting_for_GO'
except BaseException as error:
    record['status'] = 'failed'
    record['error'] = {'type': type(error).__name__, 'message': str(error)}
finally:
    for temporary in original_temp:
        if temporary.exists():
            temporary.unlink()
    record['finished_at'] = now()
    (P / 'driver.py').write_bytes(Path(__file__).read_bytes())
    (P / 'receipt.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in P.iterdir() if p.is_file()}
    (P / 'files.json').write_text(json.dumps(files, indent=2) + '\n')
    print(json.dumps({'receipt': str(P / 'receipt.json'), 'status': record['status'],
                      'receipt_sha256': sha((P / 'receipt.json').read_bytes()), 'copy_executed': record['copy_executed'],
                      'publish_executed': False, 'writes': record['writes'], 'error': record['error']}), flush=True)
if record['status'] == 'failed':
    raise SystemExit(1)
