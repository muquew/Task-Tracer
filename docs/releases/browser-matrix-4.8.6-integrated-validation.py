"""Verify and retain native 4.8.6 matrices without rewriting reports or logs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from browser_matrix import PROGRAMS, CORE_VIEWPORTS
from check import source_identity, verification_identity

RELEASE = ROOT / 'docs/releases'
FREEZE = json.loads(Path('/tmp/task-tracer-4.8.6-freeze.json').read_text())
ENGINES = ('chromium', 'firefox', 'webkit')
effective_path = Path('/tmp/task-tracer-4.8.6-matrix-effective.json')
effective = json.loads(effective_path.read_text()) if effective_path.exists() else {
    engine: {
        'report': f'/tmp/task-tracer-4.8.6-matrix-{engine}.json',
        'console': f'/tmp/task-tracer-4.8.6-matrix-{engine}-console.log',
    } for engine in ENGINES
}
sha = lambda data: hashlib.sha256(data).hexdigest()
assert source_identity() == FREEZE['source']
assert verification_identity() == FREEZE['verification']
assert len(FREEZE['source']['files']) == 22
assert len(FREEZE['verification']['files']) == 69
assert len(PROGRAMS) == len(set(PROGRAMS)) == 31
assert set(effective) == set(ENGINES)

retained = {}
def retain(relative, original):
    assert not relative.is_absolute() and '..' not in relative.parts
    assert original.is_file() and not original.is_symlink(), original
    data = original.read_bytes()
    target = RELEASE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.is_file() and not target.is_symlink(), target
        assert target.read_bytes() == data, f'Refusing evidence overwrite: {target}'
    else:
        target.write_bytes(data)
    assert target.read_bytes() == data
    retained[relative.as_posix()] = {'bytes': len(data), 'sha256': sha(data)}

summaries = {}
for engine in ENGINES:
    original = Path(effective[engine]['report'])
    console = Path(effective[engine]['console'])
    assert original.parent == console.parent == Path('/tmp')
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
    assert report['planned_checks'] == [{'browser': engine, 'program': program} for program in PROGRAMS]
    assert [item['program'] for item in report['checks']] == list(PROGRAMS)
    assert set(report['browsers']) == {engine}
    probe = report['browsers'][engine]
    version = probe['version']
    assert probe['status'] == 'passed' and probe['exit_code'] == 0 and isinstance(version, str) and version
    for item in report['checks']:
        assert item['browser'] == engine and item['version'] == version
        assert item['status'] == 'passed' and item['exit_code'] == 0
    log_dir = Path(report['log_directory'])
    assert log_dir == Path(f'{original.stem}-logs') / report['run_id']
    logs = [item['log'] for item in (probe, *report['checks'])]
    assert len(logs) == len({item['relative_path'] for item in logs}) == 32
    for info in logs:
        relative = Path(info['relative_path'])
        assert not relative.is_absolute() and '..' not in relative.parts and relative.is_relative_to(log_dir)
        source = original.parent / relative
        assert Path(info['path']) == source
        data = source.read_bytes()
        assert len(data) == info['bytes'] and sha(data) == info['sha256']
        retain(relative, source)
    probe_observations = []
    for line in Path(probe['log']['path']).read_text().splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get('browser') == engine:
            probe_observations.append(value)
    assert probe_observations == [{'browser': engine, 'version': version}]
    core_text = Path(report['checks'][0]['log']['path']).read_text()
    for phrase in (f'{engine} 1280px: starting', f'{engine} 390px: starting',
                   f'{engine}: {version}', f'{engine}: desktop/mobile critical flows and offline reload passed'):
        assert phrase in core_text, (engine, phrase)
    retain(Path(f'browser-matrix-4.8.6-{engine}.json'), original)
    retain(Path(f'browser-matrix-4.8.6-{engine}.log'), console)
    summaries[engine] = {
        'version': version, 'passed_programs': 31,
        'not_run_coverage_groups': len(expected_exceptions),
        'started_at': report['started_at'], 'finished_at': report['finished_at'],
        'program_seconds': round(sum(item['duration_seconds'] for item in report['checks']), 3),
        'run_id': report['run_id'], 'log_directory': log_dir.as_posix(),
        'native_report': str(original), 'canonical_report': f'browser-matrix-4.8.6-{engine}.json',
    }

assert len(retained) == 102
assert sum(summary['not_run_coverage_groups'] for summary in summaries.values()) == 4
assert source_identity() == FREEZE['source']
assert verification_identity() == FREEZE['verification']
native_files = len(retained)
retain(Path('browser-matrix-4.8.6-integrated-validation.py'), Path(__file__))
record = {
    'captured_at': datetime.now(timezone.utc).isoformat(),
    'status': 'passed', 'completed': True, 'passed': True,
    'source_sha256': FREEZE['source']['sha256'],
    'verification_sha256': FREEZE['verification']['sha256'],
    'source_unchanged': True, 'verification_unchanged': True,
    'engines': summaries, 'program_executions': 93,
    'native_retained_files': native_files, 'retained_files': retained,
    'scope': 'Core only repeats 1280x800 and 390x844; special-purpose programs retain their own viewport scopes. Four engine/program live-CDP timezone groups remain not_run. Not real Safari, iOS or physical devices.',
}
output = RELEASE / 'browser-matrix-4.8.6-integrated-validation.json'
assert not output.exists(), 'Review an existing collection record before replacing it'
output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'engines': summaries, 'native_files': native_files,
                  'retained_with_validator': len(retained), 'output': str(output)}, indent=2))
