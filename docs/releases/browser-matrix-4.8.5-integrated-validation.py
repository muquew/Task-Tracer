"""Retain the unchanged native integrated matrix reports and all referenced logs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from browser_matrix import PROGRAMS, CORE_VIEWPORTS
from check import source_identity, verification_identity

FREEZE = json.loads(Path('/tmp/task-tracer-4.8.5-freeze-4.json').read_text())
RELEASE = ROOT / 'docs/releases'
VERSIONS = {'chromium': '154.0.8037.57', 'firefox': '153.0', 'webkit': '26.5'}
sha = lambda data: hashlib.sha256(data).hexdigest()
assert source_identity() == FREEZE['source']
assert verification_identity() == FREEZE['verification']
assert len(PROGRAMS) == len(set(PROGRAMS)) == 31

retained = {}
def retain(relative, source):
    assert not relative.is_absolute() and '..' not in relative.parts
    assert source.is_file() and not source.is_symlink(), source
    data = source.read_bytes()
    destination = RELEASE / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert destination.is_file() and not destination.is_symlink(), destination
        assert destination.read_bytes() == data, f'Refusing evidence overwrite: {destination}'
    else:
        destination.write_bytes(data)
    assert destination.read_bytes() == data, destination
    retained[relative.as_posix()] = {'bytes': len(data), 'sha256': sha(data)}

summaries = {}
for engine, version in VERSIONS.items():
    run_suffix = 'integrated-rerun' if engine == 'firefox' else 'integrated'
    original = Path(f'/tmp/task-tracer-4.8.5-matrix-{engine}-{run_suffix}.json')
    report = json.loads(original.read_text())
    assert report['status'] == 'passed' and report['completed'] is True and report['passed'] is True
    assert report['source'] == report['source_final'] == FREEZE['source']
    assert report['verification'] == report['verification_final'] == FREEZE['verification']
    assert report['source_unchanged'] is True and report['verification_unchanged'] is True
    assert report['current_check'] is None and report['error'] is None
    assert not report['integrity_errors'] and not report['unexecuted_checks']
    scope = report['scope']
    assert scope['registry_program_count'] == 31 and scope['all_registered_programs'] is True
    assert scope['browsers'] == [engine] and scope['all_engines'] is False
    assert scope['programs'] == list(PROGRAMS) and scope['core_viewports'] == CORE_VIEWPORTS
    assert scope['core_program'] == 'compatibility_playwright.py'
    expected_exceptions = [
        {'browser': engine, 'program': program, 'case': 'Live device-timezone override',
         'status': 'not_run', 'reason': "Requires Chromium CDP; this engine runs the program's fixed-zone cases."}
        for program in ('timezone_playwright.py', 'calendar_timezone_playwright.py')
    ] if engine != 'chromium' else []
    assert scope['coverage_exceptions'] == expected_exceptions
    assert report['planned_checks'] == [{'browser': engine, 'program': p} for p in PROGRAMS]
    assert [item['program'] for item in report['checks']] == list(PROGRAMS)
    for item in report['checks']:
        assert item['browser'] == engine and item['version'] == version
        assert item['status'] == 'passed' and item['exit_code'] == 0
    assert set(report['browsers']) == {engine}
    probe = report['browsers'][engine]
    assert probe['status'] == 'passed' and probe['exit_code'] == 0 and probe['version'] == version
    log_dir = Path(report['log_directory'])
    assert log_dir == Path(f'{original.stem}-logs') / report['run_id']
    logs = [item['log'] for item in [probe, *report['checks']]]
    assert len(logs) == len({item['relative_path'] for item in logs}) == 32
    for info in logs:
        relative = Path(info['relative_path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert relative.is_relative_to(log_dir)
        source = original.parent / relative
        assert Path(info['path']) == source
        data = source.read_bytes()
        assert len(data) == info['bytes'] and sha(data) == info['sha256']
        retain(relative, source)
    retain(Path(f'browser-matrix-4.8.5-{engine}.json'), original)
    retain(Path(f'browser-matrix-4.8.5-{engine}.log'),
           Path(f'/tmp/task-tracer-4.8.5-matrix-{engine}-{run_suffix}-console.log'))
    summaries[engine] = {'version': version, 'passed_programs': 31,
                         'not_run_coverage_groups': len(expected_exceptions),
                         'started_at': report['started_at'], 'finished_at': report['finished_at'],
                         'program_seconds': round(sum(c['duration_seconds'] for c in report['checks']), 3),
                         'run_id': report['run_id'], 'log_directory': log_dir.as_posix()}

assert source_identity() == FREEZE['source']
assert verification_identity() == FREEZE['verification']
record = {'source_sha256': FREEZE['source']['sha256'],
          'verification_sha256': FREEZE['verification']['sha256'],
          'engines': summaries, 'retained_files': retained}
Path('/tmp/task-tracer-4.8.5-matrix-collection.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'engines': summaries, 'retained_files': len(retained)}, indent=2))
