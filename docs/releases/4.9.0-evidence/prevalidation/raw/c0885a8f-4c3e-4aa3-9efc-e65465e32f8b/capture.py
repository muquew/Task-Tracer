#!/usr/bin/env python3
"""Capture eight synthetic-data app screens under the repository's real CSP.

Run only after receiving the final stable source SHA:
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium \
  python capture-integrated.py --expected-index-sha <64-hex-sha> \
  --output-root /tmp/task-tracer-4.9.0-ui-final
Browser time is a declared synthetic fixture: 2026-10-25 07:00 UTC
(15:00 Asia/Shanghai), installed before navigation and allowed to keep ticking.
Python timestamps remain actual wall-clock UTC. Existing output is never reused.
No application file, verification tool, browser security setting, or production
origin is changed by this script. All browser data is in fresh local contexts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
from pathlib import Path
import sys
import threading
import traceback
import uuid

sys.dont_write_bytecode = True


def expected_sha(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(char not in '0123456789abcdef' for char in normalized):
        raise argparse.ArgumentTypeError('Expected a complete 64-character hexadecimal SHA-256')
    return normalized


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-index-sha', required=True, type=expected_sha,
                    help='Final, explicitly authorized index.html SHA-256; required before any app navigation')
parser.add_argument('--output-root', type=Path, default=Path('/tmp/task-tracer-4.9.0-ui-final'),
                    help='Root for a new UUID evidence directory; existing captures are never overwritten')
parser.add_argument('--repo-root', type=Path, default=Path('/workspace/Task-Tracer-redesign'),
                    help='Read-only application worktree; helpers are imported from this tree/tools')
args = parser.parse_args()
ROOT = args.repo_root.resolve()
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))
from check import atomic_report, source_identity, timestamp, verification_identity
from security_playwright import ProductionHeaderHandler
from smoke_playwright import (ThreadingHTTPServer, add_task, browser_launch_options,
                              select_language, select_theme_preference,
                              task_locator, wait_for_app_ready)
from playwright.sync_api import expect, sync_playwright

OUT = args.output_root.resolve() / str(uuid.uuid4())
OUT.mkdir(parents=True, exist_ok=False)
EXPECTED_INDEX = args.expected_index_sha
BROWSER_CLOCK_BASELINE = datetime(2026, 10, 25, 7, 0, tzinfo=timezone.utc)
REPORT_PATH = OUT / 'report.json'
SCRIPT_ORIGIN = Path(__file__).resolve()
shutil.copyfile(SCRIPT_ORIGIN, OUT / 'capture.py')
report = {
    'scope': 'Eight real Chromium app captures with enforced production CSP, synthetic local data and declared controlled browser clock',
    'synthetic_data': {'enabled': True, 'origin': 'Four explicitly provided design fixtures, entered through real app UI',
                       'anchor_date': '2026-10-25', 'contains_real_user_data': False},
    'controlled_browser_clock': {'enabled': True, 'api': 'page.clock.install(time=...)',
                                 'baseline_utc': BROWSER_CLOCK_BASELINE.isoformat(),
                                 'baseline_asia_shanghai': '2026-10-25T15:00:00+08:00',
                                 'behavior': 'Installed immediately before every explicit page.goto; clock continues ticking with real elapsed time',
                                 'pause_used': False, 'fixed_time_used': False, 'manual_time_advance_used': False,
                                 'installations': []},
    'python_wall_clock': {'provider': 'Actual Python datetime.now(timezone.utc)',
                          'started_at_utc': timestamp()},
    'started_at': timestamp(), 'status': 'running', 'passed': False,
    'source': source_identity(), 'verification': verification_identity(),
    'expected_index_sha256': EXPECTED_INDEX,
    'browser_security': {'bypass_csp': False, 'ignore_https_errors': False,
                         'launch_flags': 'browser_launch_options() without extra flags'},
    'environment': {'PYTHONDONTWRITEBYTECODE': os.environ.get('PYTHONDONTWRITEBYTECODE'),
                    'TASK_TRACER_BROWSER_EXECUTABLE': os.environ.get('TASK_TRACER_BROWSER_EXECUTABLE')},
    'imports': {'tools_directory': str(TOOLS),
                'handler_module': sys.modules[ProductionHeaderHandler.__module__].__file__,
                'smoke_module': sys.modules[add_task.__module__].__file__,
                'identity_module': sys.modules[source_identity.__module__].__file__},
    'current_phase': 'preflight', 'captures': [], 'headers': {}, 'actions': [],
    'page_errors': [], 'console_errors': [], 'console_messages': [],
    'request_failures': [], 'http_errors': [], 'errors': [],
    'contexts': [], 'cleanup': {},
}
report['identity_input_counts'] = {
    'distribution_source_files': len(report['source']['files']),
    'verification_files': len(report['verification']['files']),
    'combined_release_inputs': len(report['source']['files']) + len(report['verification']['files']),
}
index = (ROOT / 'index.html').read_bytes()
(OUT / 'index.input.html').write_bytes(index)
report['index_input_sha256'] = hashlib.sha256(index).hexdigest()
report['capture_script_sha256'] = hashlib.sha256(SCRIPT_ORIGIN.read_bytes()).hexdigest()
atomic_report(REPORT_PATH, report)


def action(name: str, **details) -> None:
    report['actions'].append({'at': timestamp(), 'name': name, **details})


def close_navigation(page) -> None:
    toggle = page.locator('#workspaceNavToggle')
    if toggle.is_visible() and toggle.get_attribute('aria-expanded') == 'true':
        page.keyboard.press('Escape')
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        action('close_navigation_with_escape')


def dismiss_notice(page, required: bool = False) -> None:
    close = page.locator('.notification.show #workspaceNotificationClose')
    if required:
        expect(close).to_be_visible(timeout=3000)
    if close.is_visible():
        close.click()
        expect(page.locator('.notification')).not_to_have_class(__import__('re').compile(r'\bshow\b'))
        action('click_workspace_notification_close')


def attach_errors(page, label: str) -> None:
    def metadata():
        return {'at': timestamp(), 'context': label, 'phase': report['current_phase']}
    page.on('pageerror', lambda error: report['page_errors'].append({**metadata(), 'message': str(error)}))
    def console(message):
        item = {**metadata(), 'type': message.type, 'text': message.text, 'location': message.location}
        report['console_messages'].append(item)
        if message.type == 'error':
            report['console_errors'].append(item)
    page.on('console', console)
    page.on('requestfailed', lambda request: report['request_failures'].append(
        {**metadata(), 'url': request.url, 'method': request.method,
         'resource_type': request.resource_type, 'failure': request.failure}))
    page.on('response', lambda response: report['http_errors'].append(
        {**metadata(), 'url': response.url, 'status': response.status}) if response.status >= 400 else None)


def start_context(browser, label: str, language: str, url: str):
    context = browser.new_context(viewport={'width': 1440, 'height': 1024},
                                  locale='zh-CN' if language == 'zh-CN' else 'en-US',
                                  timezone_id='Asia/Shanghai', reduced_motion='reduce',
                                  color_scheme='light', device_scale_factor=1,
                                  bypass_csp=False, ignore_https_errors=False)
    record = {'label': label, 'language': language, 'fresh': True, 'closed': False}
    report['contexts'].append(record)
    page = context.new_page()
    attach_errors(page, label)
    # Declared screenshot fixture, not actual wall-clock time. Do not pause it.
    page.clock.install(time=BROWSER_CLOCK_BASELINE)
    report['controlled_browser_clock']['installations'].append({
        'context': label, 'before_navigation_url': url,
        'baseline_utc': BROWSER_CLOCK_BASELINE.isoformat(),
        'python_wall_time_utc': timestamp(), 'continues_ticking': True,
    })
    response = page.goto(url, wait_until='domcontentloaded')
    assert response is not None and response.status == 200
    headers = response.all_headers()
    assert headers.get('content-security-policy'), 'Actual document did not receive CSP'
    body_sha = hashlib.sha256(response.body()).hexdigest()
    assert body_sha == EXPECTED_INDEX, f'Unexpected served HTML: {body_sha}'
    report['headers'][label] = {'url': response.url, 'status': response.status,
                                'headers': headers, 'document_sha256': body_sha}
    wait_for_app_ready(page)
    expect(page.locator('#taskList .task-item')).to_have_count(0)
    select_language(page, language)
    select_theme_preference(page, 'light')
    action('fresh_context_ready', context=label, html_language=page.locator('html').get_attribute('lang'))
    return context, page, record


def seed(page, language: str) -> str:
    if language == 'zh-CN':
        names = ['整理本周计划', '准备项目提案', '阅读20分钟', '更新个人作品集']
        projects = ['个人', '工作', '学习', '个人']
        description = '回顾本周进展，安排下周的重点。'
        subtasks = ['回顾本周任务', '确定下周重点']
    else:
        names = ['Plan next week', 'Prepare the project proposal', 'Read for 20 minutes', 'Update my portfolio']
        projects = ['Personal', 'Work', 'Learning', 'Personal']
        description = "Review this week's progress and set priorities for next week."
        subtasks = ['Review this week', 'Choose next priorities']
    add_task(page, names[0], description=description, project=projects[0],
             due_date='2026-10-25', due_time='16:30', reminder_offset='-1', subtasks=subtasks)
    add_task(page, names[1], description='', project=projects[1],
             due_date='2026-10-26', due_time='09:30', reminder_offset='-1')
    add_task(page, names[2], description='', project=projects[2], no_deadline=True,
             reminder_offset='-1')
    add_task(page, names[3], description='', project=projects[3],
             due_date='2026-10-28', due_time='18:00', reminder_offset='-1')
    first = task_locator(page, names[0])
    summary = first.locator('.subtask-summary-bar')
    if summary.get_attribute('aria-expanded') != 'true':
        summary.click()
    expect(summary).to_have_attribute('aria-expanded', 'true')
    first.locator('.subtask-display-item').first.click()
    expect(first.locator('.subtask-checkbox').nth(0)).to_be_checked()
    expect(first.locator('.subtask-checkbox').nth(1)).not_to_be_checked()
    expect(page.locator('#taskList .task-item')).to_have_count(4)
    dismiss_notice(page, required=True)
    action('seed_four_synthetic_tasks_through_ui', language=language, names=names,
           projects=projects, first_subtask_checked=True, parent_completion_count=0)
    return names[0]


def capture(page, name: str, language: str, theme: str, first_name: str) -> None:
    report['current_phase'] = name
    close_navigation(page)
    dismiss_notice(page)
    page.evaluate('window.scrollTo(0, 0)')
    page.evaluate('document.fonts.ready')
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    expect(page.locator('html')).to_have_attribute('data-theme', theme)
    expect(page.locator('html')).to_have_attribute('lang', language)
    path = OUT / f'{name}.png'
    page.screenshot(path=str(path), full_page=False, animations='disabled')
    snapshot = page.evaluate("""() => {
      const first=document.querySelector('#taskList .task-name');
      const bounds=first?.getBoundingClientRect();
      return {language:document.documentElement.lang,theme:document.documentElement.dataset.theme,
        language_preference:document.querySelector('#languageSelect')?.value,
        theme_preference:document.querySelector('#themeToggleBtn')?.value,
        viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
        document:{client_width:document.documentElement.clientWidth,scroll_width:document.documentElement.scrollWidth},
        scroll:{x:scrollX,y:scrollY},controlled_browser_time_utc:new Date().toISOString(),
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
        reduced_motion:matchMedia('(prefers-reduced-motion: reduce)').matches,
        first_task_title_bounds:bounds?{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height}:null,
        task_names:[...document.querySelectorAll('#taskList .task-name')].map(el=>el.textContent),
        task_modal_open:!document.querySelector('#taskModal').classList.contains('hidden')&&getComputedStyle(document.querySelector('#taskModal')).display!=='none',
        schedule_open:!!document.querySelector('#workspaceScheduleDialog')?.open,
        focus:{id:document.activeElement.id,tag:document.activeElement.tagName},
        visible_notification:!!document.querySelector('.notification.show')};
    }""")
    first = task_locator(page, first_name)
    snapshot['first_subtasks'] = first.locator('.subtask-checkbox').evaluate_all(
        '(nodes)=>nodes.map(node=>({label:node.getAttribute("aria-label"),checked:node.checked}))')
    assert snapshot['document']['scroll_width'] <= snapshot['document']['client_width'], snapshot
    record = {'name': name, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'at': timestamp(), 'captured_at_python_wall_utc': timestamp(),
              'browser_time_is_controlled_fixture': True, 'animations': 'disabled', **snapshot}
    report['captures'].append(record)
    atomic_report(REPORT_PATH, report)
    print(f'captured {name}: {snapshot["viewport"]["width"]}x{snapshot["viewport"]["height"]}', flush=True)


server = thread = browser = None
contexts = []
try:
    assert report['index_input_sha256'] == EXPECTED_INDEX
    assert report['identity_input_counts']['combined_release_inputs'] == 93
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    assert os.environ.get('TASK_TRACER_BROWSER_EXECUTABLE') == '/usr/bin/chromium'
    server = ThreadingHTTPServer(('127.0.0.1', 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    report['url'] = url
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        report['browser_version'] = browser.version
        context, page, ctx_record = start_context(browser, 'zh', 'zh-CN', url)
        contexts.append((context, ctx_record))
        report['current_phase'] = 'seed-zh'
        first = seed(page, 'zh-CN')
        capture(page, '01-zh-desktop-light', 'zh-CN', 'light', first)
        select_theme_preference(page, 'dark')
        capture(page, '02-zh-desktop-dark', 'zh-CN', 'dark', first)
        page.set_viewport_size({'width': 390, 'height': 844})
        capture(page, '03-zh-narrow-dark', 'zh-CN', 'dark', first)
        page.locator('#workspaceScheduleToggle').click()
        expect(page.locator('#workspaceScheduleDialog')).to_be_visible()
        capture(page, '04-zh-narrow-schedule', 'zh-CN', 'dark', first)
        page.locator('#workspaceScheduleClose').click()
        expect(page.locator('#workspaceScheduleDialog')).not_to_be_visible()
        expect(page.locator('#workspaceScheduleToggle')).to_be_focused()
        action('schedule_closed_and_focus_returned')
        select_theme_preference(page, 'light')
        capture(page, '05-zh-narrow-light', 'zh-CN', 'light', first)
        page.set_viewport_size({'width': 1440, 'height': 1024})
        close_navigation(page)
        page.locator('#openModalBtn').click()
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskName')).to_have_value('')
        capture(page, '06-zh-new-task', 'zh-CN', 'light', first)
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).not_to_be_visible()
        action('empty_zh_new_task_cancelled_without_dirty_prompt')
        context.close()
        ctx_record['closed'] = True
        context, page, ctx_record = start_context(browser, 'en', 'en', url)
        contexts.append((context, ctx_record))
        report['current_phase'] = 'seed-en'
        first = seed(page, 'en')
        capture(page, '07-en-desktop-light', 'en', 'light', first)
        page.locator('#openModalBtn').click()
        expect(page.locator('#taskModal')).to_be_visible()
        expect(page.locator('#taskName')).to_have_value('')
        capture(page, '08-en-new-task', 'en', 'light', first)
        page.locator('#cancelBtn').click()
        expect(page.locator('#taskModal')).not_to_be_visible()
        action('empty_en_new_task_cancelled_without_dirty_prompt')
        report['status'] = 'captured'
        for context, record in contexts:
            if not record['closed']:
                context.close()
                record['closed'] = True
        browser.close()
        browser = None
        report['cleanup']['browser_closed'] = True
except BaseException as error:
    report['status'] = 'failed'
    report['errors'].append({'at': timestamp(), 'phase': report['current_phase'],
                              'type': type(error).__name__, 'message': str(error),
                              'traceback': traceback.format_exc()})
finally:
    for context, record in contexts:
        if not record['closed']:
            try:
                context.close()
                record['closed'] = True
            except BaseException as error:
                report['errors'].append({'phase': 'context_cleanup', 'message': str(error)})
    if browser is not None:
        try:
            browser.close()
            report['cleanup']['browser_closed'] = True
        except BaseException as error:
            report['errors'].append({'phase': 'browser_cleanup', 'message': str(error)})
    if server is not None:
        server.shutdown()
        server.server_close()
        report['cleanup']['server_closed'] = True
    if thread is not None:
        thread.join(timeout=3)
        report['cleanup']['server_thread_stopped'] = not thread.is_alive()
    report['source_final'] = source_identity()
    report['verification_final'] = verification_identity()
    report['source_unchanged'] = report['source'] == report['source_final']
    report['verification_unchanged'] = report['verification'] == report['verification_final']
    report['finished_at'] = timestamp()
    report['python_wall_clock']['finished_at_utc'] = report['finished_at']
    report['passed'] = (len(report['captures']) == 8 and report['source_unchanged']
                        and report['verification_unchanged'] and not report['errors']
                        and not report['page_errors'] and not report['console_errors']
                        and not report['request_failures'] and not report['http_errors']
                        and all(record['closed'] for _, record in contexts)
                        and all(report['cleanup'].values()))
    report['visual_acceptance'] = 'Not established by automation. Images require individual visual review.'
    atomic_report(REPORT_PATH, report)
    print(json.dumps({'report': str(REPORT_PATH), 'passed': report['passed'],
                      'captures': len(report['captures']), 'status': report['status'],
                      'errors': report['errors'], 'page_errors': report['page_errors'],
                      'console_errors': report['console_errors']}, ensure_ascii=False), flush=True)
sys.exit(0 if report['passed'] else 1)
