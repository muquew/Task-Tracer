"""Observe the unchanged onboarding program without relaxing its reload/assertions."""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
import onboarding_playwright as original
from check import source_identity, verification_identity

PREFIX = Path('/tmp/task-tracer-4.8.5-firefox-onboarding-diagnostic')
REPORT = Path(f'{PREFIX}.json')
assert not REPORT.exists()
FREEZE = json.loads(Path('/tmp/task-tracer-4.8.5-freeze-4.json').read_text())
assert source_identity() == FREEZE['source'] and verification_identity() == FREEZE['verification']
state = {'status': 'running', 'passed': False, 'started_at': time.time(),
         'source': FREEZE['source'], 'verification': FREEZE['verification'],
         'original_program_sha256': hashlib.sha256((ROOT / 'tools/onboarding_playwright.py').read_bytes()).hexdigest(),
         'diagnostic_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'events': [], 'reloads': [], 'traces': []}
contexts = []

def record(kind, **data):
    event = {'time': time.time(), 'kind': kind, **data}
    state['events'].append(event)
    print(json.dumps(event, ensure_ascii=False), flush=True)

def snapshot(page):
    try:
        return page.evaluate("""async () => {
            const reg = await navigator.serviceWorker?.getRegistration();
            return {url: location.href, readyState: document.readyState,
                quickAdd: document.querySelector('#quickAddInput')?.value,
                visibleDialogs: [...document.querySelectorAll('[role=dialog],dialog')].filter(x=>x.getClientRects().length).map(x=>({id:x.id,open:x.open})),
                controller: navigator.serviceWorker?.controller && {state:navigator.serviceWorker.controller.state,scriptURL:navigator.serviceWorker.controller.scriptURL},
                registration: reg && {installing:reg.installing?.state,waiting:reg.waiting?.state,active:reg.active?.state},
                caches: await caches.keys(), cards:document.querySelectorAll('.task-item').length};
        }""")
    except Exception as error:
        return {'error': repr(error), 'url': page.url}

fresh = original.fresh_page
def observed_fresh(browser, url):
    context, page = fresh(browser, url)
    number = len(contexts) + 1
    contexts.append(context)
    trace = Path(f'{PREFIX}-context-{number}.zip')
    assert not trace.exists()
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    pending = {}
    stopped = False
    def stop_trace():
        nonlocal stopped
        if not stopped:
            try:
                context.tracing.stop(path=trace)
                state['traces'].append(str(trace))
            except Exception as error:
                record('trace_error', context=number, error=repr(error))
            stopped = True
    close = context.close
    def observed_close(*args, **kwargs):
        stop_trace()
        return close(*args, **kwargs)
    context.close = observed_close
    def requested(request):
        pending[id(request)] = {'url': request.url, 'method': request.method, 'type': request.resource_type}
        record('request', context=number, **pending[id(request)])
    def finished(request):
        pending.pop(id(request), None)
        record('request_finished', context=number, url=request.url)
    def failed(request):
        pending.pop(id(request), None)
        record('request_failed', context=number, url=request.url, failure=request.failure)
    page.on('request', requested)
    page.on('requestfinished', finished)
    page.on('requestfailed', failed)
    page.on('console', lambda message: record('console', context=number, type=message.type, text=message.text))
    page.on('pageerror', lambda error: record('pageerror', context=number, error=str(error)))
    page.on('domcontentloaded', lambda: record('domcontentloaded', context=number, url=page.url))
    page.on('load', lambda: record('load', context=number, url=page.url))
    page.on('framenavigated', lambda frame: record('frame_navigated', context=number, url=frame.url))
    reload = page.reload
    def observed_reload(*args, **kwargs):
        item = {'context': number, 'started_at': time.time(), 'before': snapshot(page), 'args': repr(args), 'kwargs': repr(kwargs)}
        state['reloads'].append(item)
        record('reload_start', **item)
        try:
            result = reload(*args, **kwargs)
        except Exception as error:
            item.update({'error': repr(error), 'finished_at': time.time(), 'after': snapshot(page), 'pending_requests': list(pending.values())})
            try:
                image = Path(f'{PREFIX}-context-{number}-failure.png')
                page.screenshot(path=str(image), timeout=5000)
                item['screenshot'] = str(image)
            except Exception as screenshot_error:
                item['screenshot_error'] = repr(screenshot_error)
            record('reload_failed', **item)
            stop_trace()
            raise
        item.update({'finished_at': time.time(), 'after': snapshot(page), 'pending_requests': list(pending.values())})
        record('reload_finished', **item)
        return result
    page.reload = observed_reload
    record('context_ready', context=number, state=snapshot(page))
    return context, page

original.fresh_page = observed_fresh
try:
    original.run('firefox')
except BaseException as error:
    state.update({'status': 'failed', 'error': repr(error), 'traceback': traceback.format_exc()})
    raise
else:
    state.update({'status': 'passed', 'passed': True})
finally:
    state['finished_at'] = time.time()
    state['source_final'] = source_identity()
    state['verification_final'] = verification_identity()
    state['source_unchanged'] = state['source'] == state['source_final']
    state['verification_unchanged'] = state['verification'] == state['verification_final']
    REPORT.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
