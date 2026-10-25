#!/usr/bin/env python3
"""Ten fresh, real-control editor captures with production CSP and normal motion."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import threading
import traceback
import uuid

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from playwright.sync_api import expect, sync_playwright
from recovery_management_playwright import stored
from security_playwright import ProductionHeaderHandler
from smoke_playwright import (
    ThreadingHTTPServer, assert_backup_payload_integrity, click_task_action,
    get_task_records, open_settings, open_task_editor, reveal_task_field,
    return_to_task_workspace, select_accent_preference, select_language,
    select_theme_preference, select_visible_option, task_locator, wait_for_app_ready,
)

parser = argparse.ArgumentParser()
parser.add_argument('--expected-index', required=True)
args = parser.parse_args()
OUT = ROOT.parent / 'design-research/task-tracer-final-delivery-2026-10-26/final-theme-review' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + str(uuid.uuid4()))
OUT.mkdir(parents=True)
print(f'Evidence directory: {OUT}', flush=True)
shutil.copyfile(__file__, OUT / 'driver.py')
RUNTIME = ('index.html', 'resources/en.json', 'resources/zh-CN.json', 'sw.js', 'vercel.json')
def save(name, data):
    (OUT / name).parent.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def identity(stage):
    tools = sorted({str(Path(module.__file__).resolve().relative_to(ROOT))
                    for module in list(sys.modules.values())
                    if getattr(module, '__file__', None)
                    and Path(module.__file__).suffix == '.py'
                    and (ROOT / 'tools') in Path(module.__file__).resolve().parents})
    result = {'runtime': {}, 'actual_tools': {}}
    for kind, names in (('runtime', RUNTIME), ('actual_tools', tools)):
        for name in names:
            source = ROOT / name
            result[kind][name] = hashlib.sha256(source.read_bytes()).hexdigest()
            dest = OUT / f'{stage}-snapshot' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
    save(f'{stage}-identity.json', result)
    return result

report = {'started_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Fresh synthetic local profile; ProductionHeaderHandler CSP; no bypassCSP; normal motion; Chromium; real controls only; five runtime files and actual tools locked, public PNGs excluded',
          'captures': [], 'page_errors': [], 'console_errors': [], 'actions': [], 'closed': False}
before = identity('before')
report['before'] = before
assert before['runtime']['index.html'] == args.expected_index
save('report.json', report)

def action(label, operation):
    operation()
    report['actions'].append({'name': label, 'passed': True})
    save('report.json', report)

def settle(page):
    page.evaluate("""async () => {
        await document.fonts.ready;
        await Promise.all(document.getAnimations().filter(animation => Number.isFinite(animation.effect?.getComputedTiming().endTime))
            .map(animation => animation.finished.catch(() => {})));
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    }""")

def protected(snapshot):
    return {entry['key']: entry['value'] for entry in snapshot['config'] if entry['key'] in ('taskRevision', 'recoveryHistory')}

def capture(page, name, kind='editor'):
    settle(page)
    layout = page.evaluate("""() => {
        const visible = e => !!e && e.checkVisibility({opacityProperty: true, visibilityProperty: true});
        const rect = e => { if (!e) return null; const r=e.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
        const form=document.querySelector('#taskForm');
        const footer=form.querySelector('.form-actions');
        const header=document.querySelector('#taskModal .modal-header');
        const f=rect(form), a=rect(footer), h=rect(header);
        const clip={left:Math.max(0,f.left),right:Math.min(innerWidth,f.right),top:Math.max(0,f.top,h.bottom),bottom:Math.min(innerHeight,f.bottom,visible(footer)?a.top:innerHeight)};
        const selectors=['#taskName','#taskDesc','#taskProject','#taskTags','#dueDate','#dueTime','#dueDateError','#repeatInterval','#repeatIntervalError','#submitBtn','#cancelBtn','#draftDiscardPrompt','#draftKeepEditingBtn','#draftDiscardBtn'];
        const controls=selectors.map(selector=>{const e=document.querySelector(selector),r=rect(e);const center=r?document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2):null;return {selector,visible:visible(e),rect:r,disabled:e?.disabled,required:e?.required,ariaInvalid:e?.getAttribute('aria-invalid'),text:e?.innerText,value:e?.value,
            fullyInFormClip:!!r&&visible(e)&&r.top>=clip.top-1&&r.bottom<=clip.bottom+1&&r.left>=clip.left-1&&r.right<=clip.right+1,
            hitInside:!!center&&!!e&&(center===e||e.contains(center))};});
        const surfaces=['#taskModal .modal-content','#taskEditor','.task-editor-properties','#taskDesc','#dueDate','#submitBtn','.form-actions','#draftDiscardPrompt'].map(selector=>{const e=document.querySelector(selector);if(!e)return{selector,exists:false};const c=getComputedStyle(e);return {selector,visible:visible(e),background:c.backgroundColor,backgroundImage:c.backgroundImage,color:c.color,border:c.borderColor,shadow:c.boxShadow,backdropFilter:c.backdropFilter,radius:c.borderRadius};});
        return {viewport:{width:innerWidth,height:innerHeight},docWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,normalMotion:!matchMedia('(prefers-reduced-motion: reduce)').matches,
            language:document.documentElement.lang,theme:document.documentElement.dataset.theme,accent:document.documentElement.dataset.accent,
            footer:{visible:visible(footer),rect:a},header:h,form:{rect:f,scrollTop:form.scrollTop,scrollHeight:form.scrollHeight,clientHeight:form.clientHeight},clip,controls,surfaces,activeElement:document.activeElement?.id};
    }""")
    assert layout['normalMotion']
    assert layout['docWidth'] <= layout['viewport']['width'] and layout['bodyWidth'] <= layout['viewport']['width'], layout
    by_selector = {entry['selector']: entry for entry in layout['controls']}
    required = ['#dueDate', '#dueTime'] if kind in ('editor', 'error') else ['#draftKeepEditingBtn', '#draftDiscardBtn']
    if kind == 'error':
        required += ['#dueDateError']
    for selector in required:
        assert by_selector[selector]['fullyInFormClip'] and by_selector[selector]['hitInside'], f'{name}: {selector} not fully visible and reachable: {by_selector[selector]}; clip={layout["clip"]}'
    if kind != 'discard':
        for selector in ('#submitBtn', '#cancelBtn'):
            item = by_selector[selector]
            assert item['visible'] and item['hitInside'] and item['rect']['bottom'] <= layout['viewport']['height'] + 1 and item['rect']['left'] >= 0 and item['rect']['right'] <= layout['viewport']['width'], item
    assert get_task_records(page) == baseline_tasks, f'{name}: committed task fields changed'
    assert protected(stored(page)) == baseline_protected, f'{name}: task revision or recovery history changed'
    assert not report['page_errors'], report['page_errors']
    png = OUT / f'{name}.png'
    page.screenshot(path=str(png), full_page=False, animations='allow')
    layout.update({'png': png.name, 'png_sha256': hashlib.sha256(png.read_bytes()).hexdigest(), 'task_fields_exactly_unchanged': True, 'task_revision_history_exactly_unchanged': True, 'kind': kind})
    save(f'{name}.json', layout)
    report['captures'].append(layout)
    save('report.json', report)
    print(json.dumps({'capture': name, 'viewport': layout['viewport'], 'theme': layout['theme'], 'accent': layout['accent'], 'language': layout['language'], 'passed': True}, ensure_ascii=False), flush=True)

server = thread = browser = context = p = None
baseline_tasks = baseline_protected = None
try:
    server = ThreadingHTTPServer(('127.0.0.1', 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium')
    context = browser.new_context(viewport={'width':1280,'height':1000}, locale='en-US', timezone_id='Asia/Shanghai', reduced_motion='no-preference', accept_downloads=True)
    page = context.new_page()
    page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
    page.on('console', lambda message: report['console_errors'].append(message.text) if message.type == 'error' else None)
    response = page.goto(f'http://127.0.0.1:{server.server_port}/', wait_until='networkidle')
    headers = response.all_headers()
    assert hashlib.sha256(response.body()).hexdigest() == args.expected_index
    assert headers.get('content-security-policy')
    report['source'] = {'url': response.url, 'status': response.status, 'response_headers': headers, 'index_sha256': args.expected_index, 'browser': browser.version, 'bypassCSP': False, 'normalMotion': True}
    wait_for_app_ready(page)
    # Create the representative task through the production editor controls.
    open_task_editor(page)
    page.locator('#taskName').fill('交付体验检查 · Product release')
    page.locator('#taskDesc').fill('确认任务、时间与项目完整保留。\nReview the details before shipping.')
    page.locator('#taskProject').fill('Task Tracer')
    reveal_task_field(page, '#taskTags').fill('release, design')
    page.locator('#noDeadline').uncheck()
    page.locator('#dueDate').fill('2032-05-06')
    page.locator('#dueTime').fill('16:35')
    for selector, value in (('#reminderOffset','60'),('#reminderRepeat','15'),('#repeatType','weekly-days')):
        reveal_task_field(page, selector)
        select_visible_option(page, selector, value)
    for day in ('0','1','2','3','4','5','6'):
        page.locator(f'#repeatWeekday{day}').uncheck()
    for day in ('2','4'):
        page.locator(f'#repeatWeekday{day}').check()
    for child in ('复核关键路径 · Review flows', '整理交付清单 · Prepare release'):
        page.locator('#subtaskInput').fill(child)
        page.locator('#addSubtaskBtn').click()
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    task = task_locator(page, '交付体验检查 · Product release')
    expect(task).to_have_count(1)
    baseline = stored(page)
    baseline_tasks = baseline['tasks']
    baseline_protected = protected(baseline)
    save('task-fields-before.json', baseline_tasks)
    save('task-write-state-before.json', baseline_protected)
    action('Create representative task using real editor controls', lambda: None)
    configs = [('iris','light',1280,1000,'en'),('iris','dark',390,844,'zh-CN'),
               ('ocean','light',390,844,'zh-CN'),('ocean','dark',1280,1000,'en'),
               ('pine','light',1280,1000,'en'),('pine','dark',390,844,'zh-CN'),
               ('berry','light',390,844,'zh-CN'),('berry','dark',1280,1000,'en')]
    for number, (accent, appearance, width, height, language) in enumerate(configs, 1):
        page.set_viewport_size({'width':width,'height':height})
        select_language(page, language)
        select_accent_preference(page, accent)
        select_theme_preference(page, appearance)
        return_to_task_workspace(page)
        click_task_action(task_locator(page, '交付体验检查 · Product release'), 'edit')
        expect(page.locator('#taskModal')).to_be_visible()
        page.locator('#dueDate').focus()
        capture(page, f'{number:02d}-{accent}-{appearance}-{width}-{language}')
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
    page.set_viewport_size({'width':320,'height':500})
    select_language(page, 'zh-CN')
    select_accent_preference(page, 'berry')
    select_theme_preference(page, 'dark')
    open_task_editor(page)
    page.locator('#taskName').fill('未保存的体验检查')
    page.locator('#noDeadline').uncheck()
    page.locator('#dueDate').fill('')
    page.locator('#submitBtn').click()
    expect(page.locator('#dueDateError')).to_be_visible()
    expect(page.locator('#dueDate')).to_have_attribute('aria-invalid', 'true')
    capture(page, '09-berry-dark-320-empty-date-error', 'error')
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    capture(page, '10-berry-dark-320-discard-confirmation', 'discard')
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert get_task_records(page) == baseline_tasks
    assert protected(stored(page)) == baseline_protected
    # Download a real restorable backup and verify every task field.
    open_settings(page, 'data')
    with page.expect_download() as pending:
        page.locator('#backupBtn').click()
    download = pending.value
    download_path = OUT / download.suggested_filename
    download.save_as(str(download_path))
    payload = json.loads(download_path.read_text())
    assert_backup_payload_integrity(payload, 'backup')
    assert payload['tasks'] == baseline_tasks
    report['backup'] = {'path': download_path.name, 'sha256': hashlib.sha256(download_path.read_bytes()).hexdigest(), 'checksum_valid': True, 'tasks_exactly_equal_before': True}
    save('task-fields-after.json', get_task_records(page))
    save('task-write-state-after.json', protected(stored(page)))
    assert get_task_records(page) == baseline_tasks
    assert protected(stored(page)) == baseline_protected
    assert len(report['captures']) == 10
    assert not report['page_errors']
    assert not [message for message in report['console_errors'] if 'Content Security Policy' in message or 'unsafe-eval' in message or 'Refused to' in message], report['console_errors']
    report['passed'] = True
except Exception as error:
    report.update({'passed': False, 'error': str(error), 'traceback': traceback.format_exc()})
    if 'page' in locals():
        try:
            page.screenshot(path=str(OUT / 'failure.png'), full_page=False, animations='allow')
            save('failure-dom.json', {'body_text': page.locator('body').inner_text(), 'modal_text': page.locator('#taskModal').inner_text() if page.locator('#taskModal').is_visible() else None})
        except Exception:
            pass
    raise
finally:
    if context:
        context.close()
    if browser:
        browser.close()
    if p:
        p.stop()
    if server:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    report['closed'] = True
    report['after'] = identity('after')
    report['runtime_and_actual_tools_stable'] = before == report['after']
    report['passed'] = report.get('passed', False) and report['runtime_and_actual_tools_stable']
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    save('report.json', report)
    print(json.dumps({'closed': True, 'passed': report['passed'], 'captures': len(report['captures']), 'runtime_and_actual_tools_stable': report['runtime_and_actual_tools_stable'], 'path': str(OUT)}, ensure_ascii=False), flush=True)
