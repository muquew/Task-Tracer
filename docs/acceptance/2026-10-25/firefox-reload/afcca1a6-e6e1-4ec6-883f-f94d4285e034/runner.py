"""Observe five unchanged Firefox onboarding runs against the accepted freeze."""
from datetime import datetime, timezone
import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
from zoneinfo import ZoneInfo

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from check import atomic_report, source_identity, verification_identity


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def child_run(output):
    import onboarding_playwright as original
    baseline = json.loads((ROOT / 'docs/releases/inputs-4.8.5.json').read_text())['input_capture']['freeze']
    state = {'schema_version': 1, 'run_id': str(uuid.uuid4()), 'status': 'running',
             'completed': False, 'passed': False, 'started_at': now(), 'finished_at': None,
             'engine': 'firefox', 'engine_version': None, 'source': source_identity(),
             'verification': verification_identity(), 'source_final': None,
             'verification_final': None, 'source_unchanged': False,
             'verification_unchanged': False, 'reloads': [], 'contexts': [],
             'events': [], 'error': None, 'traceback': None,
             'scope': 'The unchanged onboarding_playwright.run(firefox), with passive lifecycle listeners, traces, and exact forwarding of reload calls. No assertions, default timeouts, page DOM, dialogs, or service worker behavior are changed.'}
    assert state['source'] == baseline['source'] and state['verification'] == baseline['verification']
    contexts = []
    def save():
        atomic_report(output / 'result.json', state)
    save()
    original_fresh = original.fresh_page
    def observed_fresh(browser, url):
        context, page = original_fresh(browser, url)
        state['engine_version'] = browser.version
        index = len(contexts) + 1
        info = {'number': index, 'url': url, 'opened_at': now(), 'trace': f'context-{index}.zip'}
        state['contexts'].append(info)
        contexts.append(context)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        stopped = False
        def stop_trace():
            nonlocal stopped
            if not stopped:
                context.tracing.stop(path=output / info['trace'])
                info['trace_saved'] = True
                stopped = True
        context_close = context.close
        def observed_close(*args, **kwargs):
            stop_trace()
            info['closed_at'] = now()
            return context_close(*args, **kwargs)
        context.close = observed_close
        def event(kind, **values):
            state['events'].append({'at': now(), 'context': index, 'kind': kind, **values})
        page.on('load', lambda: event('load', url=page.url))
        page.on('domcontentloaded', lambda: event('domcontentloaded', url=page.url))
        page.on('pageerror', lambda error: event('pageerror', message=str(error)))
        page.on('requestfailed', lambda request: event('requestfailed', url=request.url, failure=request.failure))
        reload_page = page.reload
        def observed_reload(*args, **kwargs):
            item = {'context': index, 'started_at': now(), 'args': repr(args), 'kwargs': repr(kwargs)}
            state['reloads'].append(item)
            start = time.perf_counter()
            try:
                response = reload_page(*args, **kwargs)
            except BaseException as error:
                item['error'] = repr(error)
                try:
                    filename = f'context-{index}-reload-failure.png'
                    page.screenshot(path=output / filename, timeout=5000)
                    item['failure_screenshot'] = filename
                except BaseException as capture_error:
                    item['failure_screenshot_error'] = repr(capture_error)
                try:
                    stop_trace()
                except BaseException as trace_error:
                    info['trace_error'] = repr(trace_error)
                raise
            else:
                item['passed'] = True
                return response
            finally:
                item['finished_at'] = now()
                item['duration_seconds'] = round(time.perf_counter() - start, 6)
        page.reload = observed_reload
        save()
        return context, page
    original.fresh_page = observed_fresh
    error = None
    try:
        original.run('firefox')
        assert len(state['contexts']) == 4 and len(state['reloads']) == 4
        assert all(item.get('passed') for item in state['reloads'])
        assert all(item.get('trace_saved') for item in state['contexts'])
        state['status'] = 'passed'
        state['passed'] = True
    except BaseException as exc:
        error = exc
        state['status'] = 'failed'
        state['error'] = repr(exc)
        state['traceback'] = traceback.format_exc()
        print(state['traceback'], flush=True)
    finally:
        for context in contexts:
            try:
                context.close()
            except BaseException:
                pass
        state['source_final'] = source_identity()
        state['verification_final'] = verification_identity()
        state['source_unchanged'] = state['source_final'] == state['source'] == baseline['source']
        state['verification_unchanged'] = state['verification_final'] == state['verification'] == baseline['verification']
        if not state['source_unchanged'] or not state['verification_unchanged']:
            state['status'] = 'failed'
            state['passed'] = False
            state['error'] = state['error'] or 'Frozen inputs changed'
        state['completed'] = True
        state['finished_at'] = now()
        save()
    return 0 if state['passed'] else 1


def suite():
    run_id = str(uuid.uuid4())
    output = ROOT / 'docs/acceptance/2026-10-25/firefox-reload' / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / 'runner.py').write_bytes(Path(__file__).read_bytes())
    baseline = json.loads((ROOT / 'docs/releases/inputs-4.8.5.json').read_text())['input_capture']['freeze']
    state = {'schema_version': 1, 'run_id': run_id, 'status': 'running', 'completed': False,
             'passed': False, 'started_at': now(), 'finished_at': None,
             'started_at_beijing': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='milliseconds'),
             'source': source_identity(), 'verification': verification_identity(),
             'source_final': None, 'verification_final': None, 'source_unchanged': False,
             'verification_unchanged': False, 'planned_runs': 5, 'runs': [],
             'original_program_sha256': hashlib.sha256((ROOT / 'tools/onboarding_playwright.py').read_bytes()).hexdigest(),
             'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'prior_result': 'The first 2026-10-24 Beijing matrix had one Firefox reload timeout. These are new independent full runs, not a root-cause claim or replacement of that failure.'}
    assert state['source'] == baseline['source'] and state['verification'] == baseline['verification']
    path = output / 'suite.json'
    atomic_report(path, state)
    print('EVIDENCE_DIRECTORY=' + str(output), flush=True)
    for number in range(1, 6):
        target = output / f'run-{number}'
        target.mkdir()
        start = time.perf_counter()
        with (target / 'original-output.log').open('x') as log:
            code = subprocess.call([sys.executable, str(Path(__file__)), '--child', str(target)], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT)
        result_path = target / 'result.json'
        result = json.loads(result_path.read_text()) if result_path.is_file() else None
        state['runs'].append({'number': number, 'directory': target.name, 'exit_code': code,
                              'duration_seconds': round(time.perf_counter() - start, 3),
                              'run_id': result.get('run_id') if result else None,
                              'passed': code == 0 and result is not None and result['passed']})
        atomic_report(path, state)
        print(f'Run {number}/5: exit={code}, passed={state["runs"][-1]["passed"]}', flush=True)
        if code:
            print('FIRST_FAILURE=' + str(target), flush=True)
            break
    state['source_final'] = source_identity()
    state['verification_final'] = verification_identity()
    state['source_unchanged'] = state['source_final'] == state['source'] == baseline['source']
    state['verification_unchanged'] = state['verification_final'] == state['verification'] == baseline['verification']
    state['passed'] = len(state['runs']) == 5 and all(run['passed'] for run in state['runs']) and state['source_unchanged'] and state['verification_unchanged']
    state['status'] = 'passed' if state['passed'] else 'failed'
    state['completed'] = True
    state['finished_at'] = now()
    atomic_report(path, state)
    inventory = {}
    for item in sorted(output.rglob('*')):
        if item.is_file():
            data = item.read_bytes()
            inventory[item.relative_to(output).as_posix()] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (output / 'evidence-sha256.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print('SUITE_STATUS=' + state['status'], flush=True)
    return 0 if state['passed'] else 1

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        raise SystemExit(child_run(Path(sys.argv[2])))
    raise SystemExit(suite())
