"""Run unchanged smoke helpers in fresh production-origin browser contexts."""
from datetime import datetime, timezone
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
SITE = 'https://todo.muquew.com/'
FREEZE = json.loads((ROOT / 'docs/releases/inputs-4.8.5.json').read_text())['input_capture']['freeze']


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def verify():
    assert source_identity() == FREEZE['source'], 'Accepted source bytes changed'
    assert verification_identity() == FREEZE['verification'], 'Accepted verification inputs changed'


def child(engine, width, out):
    from playwright.sync_api import expect, sync_playwright
    from smoke_playwright import (SW_CACHE_NAME, add_task, complete_task, delete_task,
        edit_task, exercise_export_backup, exercise_import, exercise_language,
        get_task_records, select_view, task_locator, wait_for_app_ready)
    viewport = {'width': width, 'height': 800 if width == 1280 else 844}
    state = {'schema_version': 1, 'run_id': str(uuid.uuid4()), 'status': 'running',
             'completed': False, 'passed': False, 'started_at': now(), 'finished_at': None,
             'engine': engine, 'actual_version': None, 'site': SITE, 'viewport': viewport,
             'source': source_identity(), 'verification': verification_identity(),
             'source_final': None, 'verification_final': None,
             'source_unchanged': False, 'verification_unchanged': False,
             'proxy_inherited': True, 'tls_verification_enabled': True,
             'fresh_synthetic_context': True, 'page_errors': [], 'console_errors': [],
             'request_failures': [], 'screenshots': [], 'downloads': [], 'checks': [],
             'error': None, 'traceback': None}
    path = out / 'result.json'
    atomic_report(path, state)
    context = browser = page = None
    tracing = False
    error = None
    try:
        verify()
        with sync_playwright() as p:
            try:
                browser = getattr(p, engine).launch(headless=True, timeout=30000,
                    proxy={'server': os.environ.get('HTTPS_PROXY', 'http://proxy:8080'),
                           'bypass': '127.0.0.1,localhost'})
                state['actual_version'] = browser.version
                context = browser.new_context(locale='en-US', viewport=viewport,
                    accept_downloads=True, reduced_motion='reduce', ignore_https_errors=False)
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
                tracing = True
                page = context.new_page()
                downloads = []
                page.on('pageerror', lambda value: state['page_errors'].append(str(value)))
                page.on('console', lambda message: state['console_errors'].append(message.text) if message.type == 'error' else None)
                page.on('requestfailed', lambda request: state['request_failures'].append({'url': request.url, 'failure': request.failure}))
                page.on('download', downloads.append)
                response = page.goto(SITE, wait_until='domcontentloaded')
                assert response is not None and response.status == 200
                body = response.body()
                (out / 'online-index.html').write_bytes(body)
                state['online_html'] = {'url': response.url, 'status': response.status,
                    'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                    'local_sha256': hashlib.sha256((ROOT / 'index.html').read_bytes()).hexdigest()}
                assert body == (ROOT / 'index.html').read_bytes(), 'Production response differs from accepted source'
                wait_for_app_ready(page)
                expect(page.locator('.task-item')).to_have_count(0)
                exercise_language(page)
                name = f'PROD-ACCEPT {engine}-{width}'
                edited = name + ' edited'
                imported = name + ' restored'
                add_task(page, name, no_deadline=True, project='Production Acceptance', tags=['synthetic', engine])
                edit_task(page, name, edited)
                page.reload()
                wait_for_app_ready(page)
                expect(task_locator(page, edited)).to_have_count(1)
                for view in ('calendar', 'timeline', 'stats', 'list'):
                    select_view(page, view)
                    expect(page.locator('#taskList')).to_have_attribute('aria-labelledby', f'viewTab-{view}')
                state['checks'].append('CRUD, reload persistence and all four views with original helper assertions')
                complete_task(page, edited)
                backup = exercise_export_backup(page)
                assert any(task['name'] == edited and task['completed'] for task in backup['tasks'])
                exercise_import(page, imported)
                records = get_task_records(page)
                assert len(records) == 1 and records[0]['name'] == imported
                state['imported_records'] = records
                state['checks'].append('Actual JSON export, pre-import safety download, replace import and subtask normalization with original helper assertions')
                for number, download in enumerate(downloads, 1):
                    target = out / f'download-{number}.json'
                    download.save_as(target)
                    raw = target.read_bytes()
                    state['downloads'].append({'filename': target.name, 'suggested_filename': download.suggested_filename,
                        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
                assert len(state['downloads']) == 2
                filename = '01-online-restored.png'
                page.screenshot(path=out / filename, animations='disabled')
                state['screenshots'].append({'filename': filename, 'state': 'online replacement import, two subtasks with one completed'})
                delete_task(page, imported)
                page.wait_for_function("async name => navigator.serviceWorker.controller && (await caches.keys()).includes(name)", arg=SW_CACHE_NAME)
                state['service_worker_ready_before_offline'] = True
                context.set_offline(True)
                offline_response = page.reload(wait_until='domcontentloaded')
                wait_for_app_ready(page)
                expect(page.locator('.task-item')).to_have_count(0)
                state['offline_observation'] = page.evaluate("() => ({online:navigator.onLine,controlled:Boolean(navigator.serviceWorker.controller),url:location.href,lang:document.documentElement.lang,title:document.title,scrollWidth:document.documentElement.scrollWidth,innerWidth})")
                state['offline_response'] = {'status': offline_response.status if offline_response else None,
                    'from_service_worker': offline_response.from_service_worker if offline_response else None}
                assert state['offline_observation']['controlled']
                assert state['offline_observation']['scrollWidth'] <= state['offline_observation']['innerWidth'] + 1
                assert get_task_records(page) == []
                filename = '02-offline-after-delete.png'
                page.screenshot(path=out / filename, animations='disabled')
                state['screenshots'].append({'filename': filename, 'state': 'context network disabled, service-worker reload, deleted task stays absent'})
                assert not state['page_errors'], state['page_errors']
                state['checks'].append('Original delete/accessibility assertions, service-worker readiness, context offline reload, empty persisted records and no horizontal overflow/runtime errors')
                state['status'] = 'passed'
                state['passed'] = True
                print(f'{engine} {width}: actual version={browser.version}; original helpers, production HTML, downloads and offline reload PASS', flush=True)
            except BaseException as exc:
                error = exc
                state['status'] = 'failed'
                state['error'] = repr(exc)
                state['traceback'] = traceback.format_exc()
                print(state['traceback'], flush=True)
                if page is not None:
                    try:
                        page.screenshot(path=out / 'failure.png', timeout=5000)
                        state['failure_screenshot'] = 'failure.png'
                    except BaseException as capture_error:
                        state['failure_screenshot_error'] = repr(capture_error)
                if context is not None and tracing:
                    try:
                        context.tracing.stop(path=out / 'failure-trace.zip')
                        tracing = False
                    except BaseException as trace_error:
                        state['failure_trace_error'] = repr(trace_error)
                raise
            finally:
                if context is not None:
                    if tracing:
                        try: context.tracing.stop()
                        except BaseException: pass
                    context.close()
                if browser is not None:
                    browser.close()
    except BaseException as exc:
        state['passed'] = False
        if state['error'] is None:
            state['status'] = 'failed'
            state['error'] = repr(exc)
            state['traceback'] = traceback.format_exc()
    finally:
        state['source_final'] = source_identity()
        state['verification_final'] = verification_identity()
        state['source_unchanged'] = state['source'] == state['source_final'] == FREEZE['source']
        state['verification_unchanged'] = state['verification'] == state['verification_final'] == FREEZE['verification']
        if not state['source_unchanged'] or not state['verification_unchanged']:
            state['status'] = 'failed'; state['passed'] = False
            state['error'] = state['error'] or 'Accepted frozen inputs changed'
        state['completed'] = True
        state['finished_at'] = now()
        atomic_report(path, state)
    return 0 if state['passed'] else 1


def suite():
    run_id = str(uuid.uuid4())
    out = ROOT / 'docs/acceptance/2026-10-25/production-compatibility' / run_id
    out.mkdir(parents=True, exist_ok=False)
    (out / 'runner.py').write_bytes(Path(__file__).read_bytes())
    report = {'schema_version': 1, 'run_id': run_id, 'started_at': now(),
        'started_at_beijing': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='milliseconds'),
        'finished_at': None, 'site': SITE, 'status': 'running', 'completed': False, 'passed': False,
        'source': source_identity(), 'verification': verification_identity(),
        'source_final': None, 'verification_final': None, 'source_unchanged': False,
        'verification_unchanged': False, 'planned': [{'engine':e,'width':w} for e in ('firefox','webkit') for w in (1280,390)],
        'checks': [], 'current': None, 'error': None,
        'scope': 'Fresh synthetic profiles on the actual HTTPS production origin, original smoke helpers and assertions; inherited browser proxy and normal TLS validation; service-worker cache under context.set_offline(True).',
        'limitations': ['Cloud Linux Firefox/WebKit narrow viewports are not real mobile/Safari/iOS or OS-level installation, reboot, IME, screen-reader or system notification acceptance.', 'These are production core acceptance flows; not a complete rerun of all 31 specialized programs or the 58-check suite.']}
    path = out / 'report.json'
    atomic_report(path, report)
    print('EVIDENCE_DIRECTORY=' + str(out), flush=True)
    try:
        verify()
        for entry in report['planned']:
            verify()
            engine, width = entry['engine'], entry['width']
            target = out / f'{engine}-{width}'
            target.mkdir()
            report['current'] = {'engine': engine, 'width': width, 'started_at': now()}
            atomic_report(path, report)
            env = os.environ.copy()
            env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','XDG_CACHE_HOME':'/workspace/.cache','PLAYWRIGHT_BROWSERS_PATH':'/workspace/.cache/ms-playwright'})
            if engine == 'webkit':env['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS']='1'
            start = time.perf_counter()
            with (target / 'original-helper-output.log').open('x') as log:
                code = subprocess.call([sys.executable,str(Path(__file__)),'--child',engine,str(width),str(target)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            result = json.loads((target/'result.json').read_text()) if (target/'result.json').is_file() else None
            report['checks'].append({'engine':engine,'width':width,'exit_code':code,'passed':code==0 and result is not None and result['passed'],'duration_seconds':round(time.perf_counter()-start,3),'directory':target.name})
            atomic_report(path, report)
            print(f'{engine} {width}: exit={code}, passed={report["checks"][-1]["passed"]}',flush=True)
            if code or not report['checks'][-1]['passed']:
                raise RuntimeError(f'First failure preserved: {target}')
        verify()
        report['status']='passed';report['passed']=True
    except BaseException as exc:
        report['status']='failed';report['error']=repr(exc)
        print(traceback.format_exc(),flush=True)
    finally:
        report['source_final']=source_identity();report['verification_final']=verification_identity()
        report['source_unchanged']=report['source']==report['source_final']==FREEZE['source']
        report['verification_unchanged']=report['verification']==report['verification_final']==FREEZE['verification']
        if not report['source_unchanged'] or not report['verification_unchanged']:
            report['status']='failed';report['passed']=False;report['error']=report['error'] or 'Frozen inputs changed'
        report['completed']=True;report['finished_at']=now();report['current']=None
        atomic_report(path,report)
        inventory={}
        for item in sorted(out.rglob('*')):
            if item.is_file():
                raw=item.read_bytes();inventory[item.relative_to(out).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        (out/'evidence-sha256.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print('FINAL_STATUS='+report['status'],flush=True)
    return 0 if report['passed'] else 1

if __name__=='__main__':
    if len(sys.argv)==5 and sys.argv[1]=='--child':raise SystemExit(child(sys.argv[2],int(sys.argv[3]),Path(sys.argv[4])))
    raise SystemExit(suite())
