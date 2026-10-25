"""First 4.9.0 code-candidate push with completed prerequisite evidence; inert without --start."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import traceback
from urllib.parse import urlsplit
import uuid
import zipfile

sys.dont_write_bytecode = True
from release_490_common import (AcceptedCandidate, ROOT, archive_preparation,
    base_parser, git, inherited_proxy, now, require_execution, seal, sha)

BASELINE_SHA = '7a54122aae730cc566ef7e7b4040183842e02b8aa4f27d1b73ddd3bddafff895'
PUSH_COMMAND = ['git', 'push', '--porcelain', '--no-follow-tags', 'origin', 'HEAD:refs/heads/main']


def checked_origin():
    for options in (['--all'], ['--push', '--all']):
        urls = git('remote', 'get-url', *options, 'origin').decode().splitlines()
        assert len(urls) == 1, 'Origin must have exactly one fetch and one effective push URL'
        parsed = urlsplit(urls[0])
        assert (parsed.scheme == 'https' and parsed.hostname == 'github.com'
                and parsed.port in (None, 443) and parsed.username is None and parsed.password is None
                and parsed.path in ('/muquew/Task-Tracer', '/muquew/Task-Tracer.git')
                and not parsed.query and not parsed.fragment), 'Origin must be the existing HTTPS muquew/Task-Tracer repository'
    mirror = subprocess.run(['git', 'config', '--bool', '--get', 'remote.origin.mirror'], cwd=ROOT, capture_output=True, text=True)
    assert mirror.returncode in (0, 1) and mirror.stdout.strip() != 'true', 'Mirror push is forbidden'
    return 'https://github.com/muquew/Task-Tracer.git'


def prerequisite_gate(candidate, record):
    evidence = candidate.freeze_path.parent
    observed = record['prerequisite_files']

    def capture(path):
        path = Path(path).resolve(strict=True)
        raw = path.read_bytes()
        observed[str(path)] = {'bytes': len(raw), 'sha256': sha(raw)}
        return raw

    def load(name):
        return json.loads(capture(evidence / name))

    def terminal(data):
        assert data.get('completed') is True and data.get('passed') is True and data.get('status') == 'passed', 'Prerequisite is not completed/passed'
        assert data.get('error') is None and not data.get('integrity_errors'), 'Prerequisite retains an error'

    def identities(data):
        for key in ('source', 'verification'):
            assert data[key] == data[key + '_final'] == candidate.freeze[key], 'Prerequisite input maps drifted'
            assert data.get(key + '_unchanged') is True

    def log(spec):
        path = Path(spec['path']).resolve(strict=True)
        assert path.is_relative_to(evidence), 'Execution log must remain in this freeze evidence root'
        raw = capture(path)
        assert len(raw) == spec['bytes'] and sha(raw) == spec['sha256'], 'Execution log differs from report'
        return raw.decode()

    module = ast.parse((ROOT / 'tools/check.py').read_text())
    main = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    initial = [ast.literal_eval(node.value) for node in ast.walk(main) if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'checks' for target in node.targets)]
    extensions = [ast.literal_eval(node.args[0]) for node in ast.walk(main) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                  and node.func.value.id == 'checks' and node.func.attr == 'extend']
    assert len(initial) == len(extensions) == 1
    full_plan = initial[0] + extensions[0]
    full = load('check-results.json')
    terminal(full); identities(full)
    assert len(full_plan) == 59 and full['planned_checks'] == full_plan
    assert [item['program'] for item in full['checks']] == full_plan
    assert all(item['exit_code'] == 0 for item in full['checks']) and full['current_check'] is None
    wrapper = load('full-run.json')
    terminal(wrapper)
    assert wrapper['freeze_sha256'] == candidate.freeze_sha256 and wrapper['application_commit'] == candidate.commit
    assert wrapper['working_tree_status'] == '' and wrapper['snapshot_verified_input_count'] == 93
    assert wrapper['source'] == candidate.freeze['source'] and wrapper['verification'] == candidate.freeze['verification']
    full_log = Path(wrapper['stdout_stderr_log']).resolve(strict=True)
    assert full_log.is_relative_to(evidence) and capture(full_log), 'Native full stdout/stderr must exist'
    module = ast.parse((ROOT / 'tools/browser_matrix.py').read_text())
    programs = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'PROGRAMS' for target in node.targets))
    assert len(programs) == 32
    for engine in ('chromium', 'firefox', 'webkit'):
        matrix = load(f'matrix-{engine}.json')
        terminal(matrix); identities(matrix)
        plan = [{'browser': engine, 'program': program} for program in programs]
        assert matrix['planned_checks'] == plan and len(matrix['checks']) == 32
        assert [{'browser': item['browser'], 'program': item['program']} for item in matrix['checks']] == plan
        assert matrix['unexecuted_checks'] == [] and matrix['current_check'] is None
        assert matrix['scope']['all_registered_programs'] is True and matrix['scope']['registry_program_count'] == 32
        assert matrix['scope']['browsers'] == [engine] and matrix['scope']['programs'] == list(programs)
        assert set(matrix['browsers']) == {engine}
        probe = matrix['browsers'][engine]
        assert probe['status'] == 'passed' and probe['exit_code'] == 0 and probe['version']
        probe_lines = [json.loads(line) for line in log(probe['log']).splitlines() if line.startswith('{')]
        assert probe_lines == [{'browser': engine, 'version': probe['version']}], 'Actual engine probe does not match'
        for item in matrix['checks']:
            assert item['status'] == 'passed' and item['exit_code'] == 0 and item['version'] == probe['version']
            assert log(item['log']), 'Matrix program log is empty'
    for name in ('upgrade-archive-4.8.6', 'workspace-10000'):
        supplement = load(name + '.json')
        terminal(supplement); identities(supplement)
        assert supplement['freeze_sha256'] == candidate.freeze_sha256 and supplement['exit_code'] == 0
        text = log(supplement['log'])
        if name == 'upgrade-archive-4.8.6':
            baseline = supplement['baseline_archive']
            assert Path(baseline['path']).resolve() == (ROOT / 'dist/task-tracer-4.8.6.zip').resolve()
            raw = capture(baseline['path'])
            assert baseline['sha256'] == sha(raw) == BASELINE_SHA and len(raw) == baseline['bytes'] == 812059
            for phrase in ('Actual 4.8.6 → 4.9.0:', 'Actual rollback to 4.8.6:', 'Actual re-upgrade to 4.9.0:'):
                assert any(phrase in line and 'passed' in line for line in text.splitlines()), 'Actual baseline upgrade/rollback stage missing'
    workspace = load('workspace-10000-program.json')
    terminal(workspace)
    assert workspace['source'] == workspace['source_final'] == candidate.freeze['source'] and workspace['source_unchanged'] is True
    assert workspace['tool_inputs'] == workspace['tool_inputs_final'] and workspace['tool_inputs_unchanged'] is True
    assert len(workspace['tool_inputs']['files']) == 5
    assert all(candidate.freeze['verification']['files'][name] == digest for name, digest in workspace['tool_inputs']['files'].items())
    assert workspace['tasks'] == 10000 and workspace['subtasks_per_task'] == 6 and workspace['scope']['full_views'] is True
    assert workspace['assertions_passed'] is True and workspace['page_errors'] == [] and len(workspace['checks']) == 9
    build = load('build-result.json')
    assert build['status'] == 'passed' and build['passed'] is True and build['byte_identical'] is True
    assert build['working_tree_dirty'] is False and build['commit'] == candidate.commit and build['file_count'] == 24
    module = ast.parse((ROOT / 'tools/build_release.py').read_text())
    sources = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'DISTRIBUTION_SOURCES' for target in node.targets))
    archives = [Path(build[name]).resolve(strict=True) for name in ('archive', 'repeat_archive')]
    assert archives[0] != archives[1] and all(path.is_relative_to(evidence) for path in archives)
    raw_archives = [capture(path) for path in archives]
    assert raw_archives[0] == raw_archives[1]
    for path, raw in zip(archives, raw_archives):
        assert len(raw) == build['bytes'] and sha(raw) == build['sha256']
        assert capture(path.with_suffix('.zip.sha256')).decode() == f'{sha(raw)}  {path.name}\n'
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) == 24 and set(names) == set(sources) | {'integrity.json'}
            manifest = json.loads(archive.read('integrity.json'))
            assert manifest == build['integrity_manifest'] and manifest['version'] == '4.9.0'
            assert manifest['commit'] == candidate.commit and manifest['working_tree_dirty'] is False
            assert manifest['files'] == {target: candidate.freeze['source']['files'][source] for target, source in sources.items()}
            assert all(archive.read(target) == (ROOT / source).read_bytes() for target, source in sources.items())
    record['prerequisites_passed'] = {'full_programs': 59, 'matrix_programs': 96, 'actual_engine_probes': 3,
        'frozen_inputs': 93, 'actual_4_8_6_archive_upgrade': True, 'workspace_10000_by_6_full_views': True,
        'byte_identical_clean_archives': 2, 'archive_files_each': 24, 'archive_sha256': build['sha256']}


def unchanged_prerequisites(record):
    for name, spec in record['prerequisite_files'].items():
        raw = Path(name).read_bytes()
        assert len(raw) == spec['bytes'] and sha(raw) == spec['sha256'], 'Accepted prerequisite evidence changed'


def remote_main(directory, label):
    command = ['git', 'ls-remote', 'origin', 'refs/heads/main']
    result = {'command': command, 'started_at': now(), 'exit_code': None, 'sha': None}
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        stdout, stderr = process.stdout, process.stderr
        result['exit_code'] = process.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b'', error.stderr or b''
        result['timed_out'] = True
    (directory / f'{label}.stdout.log').write_bytes(stdout)
    (directory / f'{label}.stderr.log').write_bytes(stderr)
    lines = stdout.decode(errors='replace').splitlines()
    if result['exit_code'] == 0 and len(lines) == 1 and re.fullmatch(r'[0-9a-f]{40}\s+refs/heads/main', lines[0]):
        result['sha'] = lines[0].split()[0]
    result['finished_at'] = now()
    return result


def run(args):
    candidate = AcceptedCandidate(args)
    inherited_proxy()
    directory = args.output_root / 'push' / str(uuid.uuid4())
    archive_preparation(candidate, directory, __file__)
    record = {**candidate.record(), 'schema_version': 1, 'run_id': directory.name,
        'started_at': now(), 'finished_at': None, 'status': 'checking_prerequisites',
        'completed': False, 'passed': False, 'error': None, 'prerequisite_files': {},
        'push_command_executed': False, 'dry_run': False, 'vercel_status': 'not_checked_pending_domain_verification',
        'scope': 'First ordinary HEAD-to-main candidate push and actual GitHub ref observation. No remote CI or Vercel backend/deployment claim.'}
    publish = lambda: candidate.atomic_report(directory / 'report.json', record)
    publish()
    print('EVIDENCE_DIRECTORY=' + str(directory), flush=True)
    try:
        assert candidate.freeze['application_commit'] == candidate.commit and candidate.freeze['working_tree_dirty'] is False
        assert len(candidate.freeze['source']['files']) == 23 and len(candidate.freeze['verification']['files']) == 70
        record['origin'] = checked_origin()
        record['working_tree_status_before'] = git('status', '--porcelain', '--untracked-files=all').decode()
        assert record['working_tree_status_before'] == '', 'Candidate checkout must be clean'
        prerequisite_gate(candidate, record)
        candidate.check(); unchanged_prerequisites(record)
        record['remote_main_before'] = remote_main(directory, 'remote-main-before')
        assert record['remote_main_before']['sha'] is not None, 'Reading remote main failed; raw output retained'
        previous = record['remote_main_before']['sha']
        assert previous != candidate.commit, 'Candidate already published; refuse to label a no-op as first push'
        ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', previous, candidate.commit], cwd=ROOT, capture_output=True)
        assert ancestor.returncode == 0, 'Remote main must be a locally known ancestor; no force or automatic history rewrite'
        candidate.check(); unchanged_prerequisites(record); checked_origin()
        assert git('status', '--porcelain', '--untracked-files=all') == b'', 'Checkout changed before push'
        record.update(status='pushing', push={'command': PUSH_COMMAND, 'started_at': now(), 'exit_code': None,
            'stdout': 'push.stdout.log', 'stderr': 'push.stderr.log'})
        publish()
        try:
            process = subprocess.run(PUSH_COMMAND, cwd=ROOT, capture_output=True, timeout=180)
            stdout, stderr = process.stdout, process.stderr
            record['push']['exit_code'] = process.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b'', error.stderr or b''
            record['push']['timed_out'] = True
        record['push_command_executed'] = True
        (directory / 'push.stdout.log').write_bytes(stdout)
        (directory / 'push.stderr.log').write_bytes(stderr)
        record['push']['finished_at'] = now()
        publish()
        record['remote_main_after'] = remote_main(directory, 'remote-main-after')
        assert record['push']['exit_code'] == 0, 'Actual push failed or timed out; raw exit/stdout/stderr retained'
        assert record['remote_main_after']['sha'] == candidate.commit, 'Remote main does not match the accepted candidate'
        transitions = [line.split('\t') for line in stdout.decode().splitlines() if '\t' in line]
        assert any(parts[0] == ' ' and parts[1] == 'HEAD:refs/heads/main' for parts in transitions), 'No ordinary fast-forward update reported by actual push'
        candidate.finish_identity(record); unchanged_prerequisites(record)
        record['working_tree_status_after'] = git('status', '--porcelain', '--untracked-files=all').decode()
        assert record['working_tree_status_after'] == ''
        record.update(status='github_ref_matched_vercel_pending', passed=True)
    except BaseException as error:
        record.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    finally:
        try:
            candidate.finish_identity(record)
            if 'prerequisites_passed' in record:
                unchanged_prerequisites(record)
            record['working_tree_status_final'] = git('status', '--porcelain', '--untracked-files=all').decode()
            assert record['working_tree_status_final'] == ''
        except BaseException as error:
            record.update(status='failed', passed=False, final_identity_error=f'{type(error).__name__}: {error}')
        record.update(completed=True, finished_at=now())
        publish(); seal(directory, candidate.atomic_report)
    print(json.dumps({'status': record['status'], 'passed': record['passed'], 'report': str(directory / 'report.json')}), flush=True)
    return 0 if record['passed'] else 1


def main():
    parser = base_parser(__doc__)
    args = parser.parse_args()
    require_execution(parser, args)
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
