import sys, json, hashlib, uuid, traceback, contextlib, os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from check import source_identity, verification_identity
from smoke_playwright import local_server, browser_launch_options, wait_for_app_ready, get_task_records
from playwright.sync_api import sync_playwright, expect

RUN = str(uuid.uuid4())
OUT = ROOT / 'docs/acceptance/2026-10-25/browser-flow' / RUN
OUT.mkdir(parents=True)
(OUT / 'runner.py').write_bytes(Path(__file__).read_bytes())
freeze = json.loads((ROOT / 'docs/releases/inputs-4.8.5.json').read_text())['input_capture']['freeze']
report = {'schema_version': 1, 'run_id': RUN, 'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'running', 'completed': False, 'passed': False, 'source': source_identity(), 'verification': verification_identity(), 'steps': [], 'actions': [], 'contexts': [], 'errors': [], 'limits': ['Linux cloud browsers and emulated viewports; no physical phone, OS installation, screen reader or system notification acceptance.']}
assert report['source'] == freeze['source'] and report['verification'] == freeze['verification']
browser = context = page = None
active = None

def save():
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

def stamp():
    return datetime.now(timezone.utc).isoformat()

def state():
    aria = page.locator('body').aria_snapshot()
    metrics = page.evaluate('''() => ({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,focus:document.activeElement?.id,language:document.documentElement.lang,swControlled:!!navigator.serviceWorker?.controller})''')
    return {'aria': aria, 'metrics': metrics, 'task_cards': page.locator('.task-item').count(), 'url': page.url}

def emit(result):
    print(json.dumps(result, ensure_ascii=False), flush=True)

with local_server() as url, sync_playwright() as pw:
    emit({'ready': True, 'run_id': RUN, 'output': str(OUT), 'local_url': url})
    save()
    for line in sys.stdin:
        try:
            cmd = json.loads(line)
            op = cmd['op']
            entry = {'at': stamp(), 'command': cmd, 'context': active}
            if op == 'start':
                if context:
                    context.close()
                    browser.close()
                engine = cmd.get('engine', 'chromium')
                options = browser_launch_options() if engine == 'chromium' else {'headless': True}
                if cmd.get('target') == 'production':
                    options['proxy'] = {'server': os.environ.get('HTTPS_PROXY', 'http://proxy:8080'), 'bypass': '127.0.0.1,localhost'}
                browser = getattr(pw, engine).launch(timeout=30000, **options)
                context = browser.new_context(locale=cmd.get('locale', 'zh-CN'), viewport=cmd.get('viewport', {'width':1280,'height':800}), reduced_motion='reduce', timezone_id='Asia/Shanghai', accept_downloads=True)
                active = cmd['name']
                info = {'name':active,'engine':engine,'version':browser.version,'viewport':cmd.get('viewport',{'width':1280,'height':800}),'locale':cmd.get('locale','zh-CN'),'timezone':'Asia/Shanghai','target':cmd.get('target','local'),'page_errors':[],'failed_requests':[]}
                report['contexts'].append(info)
                page = context.new_page()
                page.on('pageerror', lambda error, info=info: info['page_errors'].append(str(error)))
                page.on('requestfailed', lambda req, info=info: info['failed_requests'].append({'url':req.url,'failure':req.failure,'offline':info.get('offline',False)}))
                target = 'https://todo.muquew.com/' if cmd.get('target') == 'production' else url
                response = page.goto(target, wait_until='load', timeout=30000)
                wait_for_app_ready(page)
                expect(page.locator('#taskList .empty-state')).to_be_visible()
                info['initial_status'] = response.status if response else None
                info['rendered_dom_sha256'] = hashlib.sha256(page.content().encode()).hexdigest()
                result = {'context':info,'state':state()}
            elif op == 'state':
                result = state() if not cmd.get('selector') else {'aria': page.locator(cmd['selector']).aria_snapshot()}
            elif op == 'act':
                locator = page.locator(cmd['selector'])
                if cmd.get('first'): locator = locator.first
                entry['before'] = state()
                method = cmd.get('method','click')
                if method == 'click': locator.click()
                elif method == 'fill': locator.fill(cmd['value'])
                elif method == 'press': locator.press(cmd['value'])
                elif method == 'check': locator.set_checked(cmd['value'])
                elif method == 'select': locator.select_option(cmd['value'])
                else: raise ValueError(method)
                result = state()
            elif op == 'snapshot':
                before = state()
                target = OUT / (cmd['name'] + '.png')
                assert not target.exists()
                page.screenshot(path=target, full_page=True, animations='disabled')
                raw = target.read_bytes()
                step = {'name':cmd['name'],'context':active,'at':stamp(),'file':target.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'accepted_after_inspection':False,'state':before,'notes':cmd.get('notes','')}
                report['steps'].append(step)
                result = {'path':str(target),'step':len(report['steps']),'state':before}
            elif op == 'accept_screenshot':
                step = next(x for x in report['steps'] if x['name']==cmd['name'])
                step['accepted_after_inspection'] = True
                step['inspection_notes'] = cmd.get('notes','')
                result = {'accepted':cmd['name']}
            elif op == 'download':
                entry['before'] = state()
                with page.expect_download() as pending:
                    page.locator(cmd['selector']).click()
                dl = pending.value
                target = OUT / (cmd.get('filename') or dl.suggested_filename)
                assert not target.exists()
                dl.save_as(target)
                data = json.loads(target.read_text())
                raw = target.read_bytes()
                result = {'path':str(target),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'data':data}
            elif op == 'upload':
                entry['before'] = state()
                target = OUT / cmd['filename']
                page.locator(cmd['selector']).set_input_files(target)
                result = state()
            elif op == 'records':
                records = get_task_records(page)
                result = {'count':len(records),'records':records}
                if cmd.get('compare_backup'):
                    wanted = json.loads((OUT/cmd['compare_backup']).read_text())['tasks']
                    normal = lambda tasks: sorted(tasks,key=lambda task:task['id'])
                    assert normal(records)==normal(wanted), 'Actual imported fields differ from downloaded backup'
                    result['exact_backup_fields_match'] = True
            elif op == 'offline':
                context.set_offline(cmd['value'])
                report['contexts'][-1]['offline'] = cmd['value']
                result = {'offline':cmd['value']}
            elif op == 'reload':
                page.reload(timeout=30000, wait_until='load')
                wait_for_app_ready(page)
                result = state()
            elif op == 'assert':
                locator = page.locator(cmd['selector'])
                rule = cmd['rule']
                if rule=='visible': expect(locator).to_be_visible()
                elif rule=='hidden': expect(locator).to_be_hidden()
                elif rule=='count': expect(locator).to_have_count(cmd['value'])
                elif rule=='value': expect(locator).to_have_value(cmd['value'])
                elif rule=='text': expect(locator).to_have_text(cmd['value'])
                else: raise ValueError(rule)
                result = {'assertion':'passed',**cmd}
            elif op == 'finish':
                report['source_final'] = source_identity()
                report['verification_final'] = verification_identity()
                report['source_unchanged'] = report['source']==report['source_final']==freeze['source']
                report['verification_unchanged'] = report['verification']==report['verification_final']==freeze['verification']
                assert report['source_unchanged'] and report['verification_unchanged']
                assert not any(c['page_errors'] for c in report['contexts']), 'Uncaught page errors'
                assert report['steps'] and all(x['accepted_after_inspection'] for x in report['steps'])
                assert not report['errors'], 'A failed interactive action remains recorded'
                report.update(status='passed',completed=True,passed=True,finished_at=stamp())
                save()
                emit({'finished':True,'report':str(OUT/'report.json')})
                break
            else: raise ValueError(op)
            entry['result'] = result
            report['actions'].append(entry)
            save()
            emit(result)
        except Exception as error:
            failure = {'at':stamp(),'command':cmd,'error':str(error),'traceback':traceback.format_exc()}
            report['errors'].append(failure)
            save()
            emit({'failure':failure})
    if context: context.close()
    if browser: browser.close()
