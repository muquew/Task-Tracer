#!/usr/bin/env python3
"""Source-bound six-context browser acceptance; defaults to local production-CSP rehearsal."""
from __future__ import annotations
import argparse
import ast
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile
import time
import traceback
from urllib.parse import urljoin, urlsplit, unquote
import uuid
from zoneinfo import ZoneInfo

ROOT = Path('/workspace/Task-Tracer')
BASE = Path(__file__).resolve().parent
EXPECTED_INDEX = '89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30'
RUNTIME = ('index.html', 'sw.js', 'vercel.json', 'resources/en.json', 'resources/zh-CN.json')
sys.path.insert(0, str(ROOT / 'tools'))
from playwright.sync_api import expect, sync_playwright
from performance_playwright import read_workspace
from smoke_playwright import (
    add_task, assert_backup_payload_integrity, browser_launch_options,
    click_task_action, get_task_records, local_server, open_settings,
    return_to_task_workspace, select_accent_preference, select_filter,
    select_language, select_theme_preference, select_view, task_locator,
    wait_for_app_ready,
)
from validate_static import app_version


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def helper_closure():
    queue = ['performance_playwright', 'smoke_playwright', 'validate_static']
    found = set()
    while queue:
        name = queue.pop()
        if name in found:
            continue
        found.add(name)
        for node in ast.walk(ast.parse((ROOT / 'tools' / f'{name}.py').read_text())):
            imports = [node.module] if isinstance(node, ast.ImportFrom) else [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            for module in imports:
                first = module.split('.')[0] if module else None
                if first and (ROOT / 'tools' / f'{first}.py').is_file():
                    queue.append(first)
    return [f'tools/{name}.py' for name in sorted(found)]


def identities():
    return {
        'runtime': {name: digest((ROOT / name).read_bytes()) for name in RUNTIME},
        'helpers': {name: digest((ROOT / name).read_bytes()) for name in helper_closure()},
        'driver': {str(Path(__file__).resolve()): digest(Path(__file__).read_bytes())},
    }


def normalize_csp(value):
    return {part.split()[0]: sorted(set(part.split()[1:])) for part in value.split(';') if part.strip()}


def assert_headers(headers):
    config = json.loads((ROOT / 'vercel.json').read_text())
    wanted = {entry['key'].lower(): entry['value'] for route in config['headers'] if route['source'] == '/(.*)' for entry in route['headers']}
    for key, expected in wanted.items():
        actual = headers.get(key)
        assert actual is not None, f'Missing effective deployment header: {key}'
        if key == 'content-security-policy':
            assert normalize_csp(actual) == normalize_csp(expected), 'Effective CSP differs from frozen source'
        else:
            assert actual.strip() == expected.strip(), f'Effective deployment header differs: {key}'


def check_document(response, mode, folder, label):
    assert response is not None and response.status == 200, f'Unexpected document response: {response}'
    body = response.body()
    actual = digest(body)
    assert actual == EXPECTED_INDEX, f'Document source differs: {actual}'
    headers = response.all_headers()
    assert_headers(headers)
    details = response.security_details()
    if mode == 'production':
        assert urlsplit(response.url).scheme == 'https', 'Production document did not retain HTTPS'
    record = {'url': response.url, 'status': response.status, 'index_sha256': actual,
              'version': app_version(body.decode()), 'response_headers': headers,
              'security_details': details, 'certificate_errors_ignored': False,
              'bypass_csp': False, 'mode': mode,
              'tls_scope': 'Normal browser HTTPS validation; no ignore_https_errors or certificate override.' if mode == 'production' else 'Local HTTP; no TLS claim.'}
    write_json(folder / f'{label}.json', record)
    return record


def check_served_runtime(context, base_url):
    checked = []
    for name in ('sw.js', 'resources/en.json', 'resources/zh-CN.json'):
        response = context.request.get(urljoin(base_url, name))
        assert response.status == 200, f'Runtime asset response {name}: {response.status}'
        actual = digest(response.body())
        assert actual == digest((ROOT / name).read_bytes()), f'Served runtime differs: {name}'
        checked.append({'path': name, 'url': response.url, 'status': response.status, 'sha256': actual})
    return checked


def snapshot(page, folder, name, errors):
    # Await actual finite CSS/Web Animations, without adding arbitrary delays or suppressing motion.
    page.evaluate("""async () => {
        await Promise.all(document.getAnimations().filter(animation =>
            animation.effect?.getComputedTiming().iterations !== Infinity)
            .map(animation => animation.finished.catch(() => {})));
    }""")
    data = page.evaluate("""() => ({
        viewport:{width:innerWidth,height:innerHeight},
        document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},
        title:document.title, language:document.documentElement.lang,
        theme:document.documentElement.dataset.theme, accent:document.documentElement.dataset.accent,
        currentView:document.body.dataset.taskView,
        active:{id:document.activeElement?.id,tag:document.activeElement?.tagName},
        headings:[...document.querySelectorAll('h1,h2')].filter(node => node.getClientRects().length).map(node => node.innerText),
        settingsVisible:document.querySelector('#settingsWorkspace').getClientRects().length>0,
        reducedMotion:matchMedia('(prefers-reduced-motion:reduce)').matches
    })""")
    assert data['document']['width'] <= data['viewport']['width'] + 1, f'Horizontal overflow: {data}'
    assert not data['reducedMotion'], 'Rehearsal/production requires original normal-motion context'
    data.update({'page_errors_so_far': list(errors), 'source_index_sha256': EXPECTED_INDEX,
                 'visual_review': 'Action capture only; no automatic claim of human screenshot review.'})
    page.screenshot(path=str(folder / f'{name}.png'), animations='allow')
    write_json(folder / f'{name}.json', data)


def records_by_id(tasks):
    return {str(task['id']): task for task in tasks}


def exercise(page, context, base_url, engine, width, folder, mode, page_errors):
    response = page.goto(base_url, wait_until='domcontentloaded')
    document = check_document(response, mode, folder, 'document-initial')
    wait_for_app_ready(page)
    assert get_task_records(page) == [], 'Fresh isolated context unexpectedly contains existing tasks'
    served = check_served_runtime(context, base_url)
    snapshot(page, folder, '01-fresh-workspace', page_errors)
    select_language(page, 'en')
    token = f'{engine}-{width}'
    name = f'Acceptance task {token}'
    updated = f'Edited acceptance task {token}'
    second = f'Undated acceptance task {token}'
    description = 'Created through the actual interface.\n保留多行说明。'
    updated_description = 'Edited through the actual interface.\n待输入子任务由主保存收纳。'
    today = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    add_task(page, name, description=description, due_date=today, due_time='18:20',
             project='Acceptance workspace', tags=['acceptance', 'review'], subtasks=['Already added child'])
    add_task(page, second, description='A task without a deadline.', no_deadline=True, project='Acceptance workspace')
    created = get_task_records(page)
    assert len(created) == 2
    primary = next(task for task in created if task['name'] == name)
    assert primary['description'] == description and primary['project'] == 'Acceptance workspace'
    assert primary['tags'] == ['acceptance', 'review']
    assert primary['dueLocalDate'] == today and primary['dueLocalTime'] == '18:20'
    assert primary['dueTimeZone'] == 'Asia/Shanghai'
    assert [child['text'] for child in primary['subtasks']] == ['Already added child']
    write_json(folder / 'created-db.json', read_workspace(page))
    click_task_action(task_locator(page, name), 'edit')
    expect(page.locator('#taskModal')).to_be_visible()
    page.locator('#taskName').fill(updated)
    page.locator('#taskDesc').fill(updated_description)
    page.locator('#subtaskInput').fill('  Pending child saved with task  ')
    expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(1)
    snapshot(page, folder, '02-editor-pending-child', page_errors)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_locator(page, updated)).to_have_count(1)
    edited = get_task_records(page)
    current = next(task for task in edited if task['id'] == primary['id'])
    assert current['name'] == updated and current['description'] == updated_description
    assert current['subtasks'][0] == primary['subtasks'][0]
    assert [child['text'] for child in current['subtasks']] == ['Already added child', 'Pending child saved with task']
    assert current['subtasks'][1]['completed'] is False
    assert {key:value for key,value in current.items() if key not in ('name','description','subtasks')} == {
        key:value for key,value in primary.items() if key not in ('name','description','subtasks')}
    assert next(task for task in edited if task['name'] == second) == next(task for task in created if task['name'] == second)
    write_json(folder / 'edited-db.json', read_workspace(page))
    task_locator(page, updated).locator('[data-action="toggle"]').click()
    expect(task_locator(page, updated)).to_have_count(0)
    completed = get_task_records(page)
    current = next(task for task in completed if task['id'] == primary['id'])
    assert current['completed'] is True and current['completedAt']
    select_filter(page, 'all')
    expect(page.locator('.task-item')).to_have_count(2)
    snapshot(page, folder, '03-list-completed', page_errors)
    view_checks = []
    for view in ('calendar', 'timeline', 'stats', 'list'):
        select_view(page, view)
        expect(page.locator('body')).to_have_attribute('data-task-view', view)
        if view == 'calendar':
            expect(page.locator('.calendar-view')).to_be_visible()
            if width < 780:
                page.locator(f'.calendar-date-number[data-calendar-detail-date="{today}"]').click()
                item = page.locator(f'.calendar-detail-task[data-calendar-task-id="{primary["id"]}"]')
                expect(item).to_be_visible()
                expect(item).to_have_accessible_name(re.compile('18:20.*' + re.escape(updated)))
            else:
                expect(page.locator(f'.calendar-task[data-calendar-task-id="{primary["id"]}"]')).to_be_visible()
        elif view == 'timeline':
            expect(page.locator('.timeline-view')).to_be_visible()
            expect(task_locator(page, updated)).to_have_count(1)
            expect(task_locator(page, second)).to_have_count(1)
        elif view == 'stats':
            expect(page.locator('.stats-review')).to_be_visible()
            expect(page.locator('.stats-review-meta')).to_have_text(re.compile(r'^1 completed today · '))
        else:
            expect(page.locator('.task-item')).to_have_count(2)
        snapshot(page, folder, f'04-view-{view}', page_errors)
        view_checks.append(view)
    before_preferences = get_task_records(page)
    for accent in ('ocean', 'pine', 'berry', 'iris'):
        select_accent_preference(page, accent)
    select_theme_preference(page, 'dark')
    select_accent_preference(page, 'ocean')
    select_language(page, 'zh-CN')
    open_settings(page, 'appearance')
    snapshot(page, folder, '05-settings-dark-ocean-chinese', page_errors)
    for section in ('data', 'experience', 'cleanup', 'help'):
        open_settings(page, section)
    expect(page.locator('#settingsVersion')).to_contain_text(document['version'])
    snapshot(page, folder, '06-help-version', page_errors)
    return_to_task_workspace(page)
    expect(page.locator('body')).to_have_attribute('data-task-view', 'list')
    assert get_task_records(page) == before_preferences, 'Appearance/language/settings navigation changed task records'
    select_language(page, 'en')
    select_theme_preference(page, 'light')
    open_settings(page, 'data')
    before_backup = read_workspace(page)
    with page.expect_download() as pending:
        page.locator('#backupBtn').click()
    download = pending.value
    target = folder / Path(download.suggested_filename).name
    download.save_as(str(target))
    payload = json.loads(target.read_text())
    assert payload['version'] == '2.4' and payload['type'] == 'backup'
    assert_backup_payload_integrity(payload, 'backup')
    assert records_by_id(payload['tasks']) == records_by_id(before_backup['tasks']), 'Downloaded JSON does not match every IndexedDB task field'
    after_backup = read_workspace(page)
    assert after_backup['tasks'] == before_backup['tasks'], 'Downloading backup changed task records'
    write_json(folder / 'before-backup-db.json', before_backup)
    write_json(folder / 'after-backup-db.json', after_backup)
    return_to_task_workspace(page)
    reloaded = page.reload(wait_until='domcontentloaded')
    check_document(reloaded, mode, folder, 'document-reloaded')
    wait_for_app_ready(page)
    assert records_by_id(get_task_records(page)) == records_by_id(payload['tasks']), 'Reload changed saved task fields'
    snapshot(page, folder, '07-reloaded-final-workspace', page_errors)
    write_json(folder / 'final-db.json', read_workspace(page))
    assert not page_errors, page_errors
    return {'document': document, 'served_runtime': served, 'tasks_created': 2,
            'edited_task_id': primary['id'], 'pending_child_saved_once': True,
            'completed_task_retained': True, 'views_exercised': view_checks,
            'workspace_themes_exercised': ['ocean','pine','berry','iris'],
            'appearances_exercised': ['dark','light'], 'languages_exercised': ['en','zh-CN'],
            'settings_categories_exercised': ['appearance','data','experience','cleanup','help'],
            'backup': {'path': str(target), 'sha256': digest(target.read_bytes()), 'checksum': payload['checksum'],
                       'checksum_verified_by_original_helper': True, 'every_task_field_matches_indexeddb': True},
            'reload_preserved_every_task_field': True,
            'physical_device_or_offline_lifecycle_claim': False}



def production_transport():
    """Use the existing managed-session HTTPS proxy; retain ordinary certificate verification."""
    proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    assert proxy_url, 'Production acceptance requires the inherited managed-session HTTPS proxy'
    parsed = urlsplit(proxy_url)
    assert parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.query and not parsed.fragment, 'Unsupported inherited proxy configuration'
    host = f'[{parsed.hostname}]' if ':' in parsed.hostname else parsed.hostname
    proxy = {'server': f'{parsed.scheme}://{host}' + (f':{parsed.port}' if parsed.port else '')}
    if parsed.username is not None:
        proxy['username'] = unquote(parsed.username)
    if parsed.password is not None:
        proxy['password'] = unquote(parsed.password)
    bypass = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
    if bypass:
        proxy['bypass'] = bypass
    ca = Path(os.environ.get('NODE_EXTRA_CA_CERTS', ''))
    assert ca.is_file(), 'Production API requests require the configured managed-session public CA bundle'
    assert os.environ.get('NODE_TLS_REJECT_UNAUTHORIZED') != '0' and os.environ.get('PYTHONHTTPSVERIFY') != '0', 'Normal TLS verification is required'
    metadata = {'inherited_https_proxy_configured': True, 'proxy_scheme': parsed.scheme,
                'proxy_hostname': parsed.hostname, 'proxy_port': parsed.port,
                'proxy_auth_present': parsed.username is not None or parsed.password is not None,
                'proxy_bypass_configured': bool(bypass), 'configured_node_ca_present': True,
                'configured_node_ca_sha256': digest(ca.read_bytes()),
                'ignore_https_errors': False, 'node_tls_reject_unauthorized_disabled': False,
                'scope': 'Existing managed-session proxy and configured public trust anchor only; no policy, DNS route, or certificate verification bypass.'}
    return proxy, metadata



def fresh_firefox_trust_profile():
    """Import only the configured, already system-trusted public CA into an isolated temporary NSS profile."""
    ca = Path(os.environ['NODE_EXTRA_CA_CERTS'])
    assert digest(ca.read_bytes()) == '7fa2d7d439db8bfa7c191457e61af5e3f4eb412314eb148766ac09e93786e4c3', 'Configured session trust anchor changed'
    verified = subprocess.run(['openssl', 'verify', '-CAfile', os.environ['SSL_CERT_FILE'], str(ca)], capture_output=True, text=True)
    assert verified.returncode == 0, 'Configured public CA is not already trusted by the managed system bundle'
    certificate = subprocess.run(['openssl', 'x509', '-in', str(ca), '-noout', '-text'], capture_output=True, text=True, check=True).stdout
    assert 'CA:TRUE' in certificate, 'Configured trust file is not a public CA certificate'
    profile = tempfile.TemporaryDirectory(prefix='task-tracer-production-firefox-', dir='/tmp')
    try:
        subprocess.run(['certutil', '-N', '--empty-password', '-d', f'sql:{profile.name}'], capture_output=True, text=True, check=True)
        subprocess.run(['certutil', '-A', '-d', f'sql:{profile.name}', '-n', 'Managed existing environment proxy CA', '-t', 'C,,', '-i', str(ca)], capture_output=True, text=True, check=True)
    except BaseException:
        profile.cleanup()
        raise
    metadata = {'temporary_profile_directory': profile.name, 'profile_reused': False,
                'configured_public_ca_sha256': digest(ca.read_bytes()), 'public_ca_basic_constraint_verified': True,
                'public_ca_already_system_trusted': True, 'import_trust': 'C,,',
                'commands_redacted_temporary_path': [
                    ['certutil', '-N', '--empty-password', '-d', 'sql:<unique-temporary-profile>'],
                    ['certutil', '-A', '-d', 'sql:<unique-temporary-profile>', '-n', 'Managed existing environment proxy CA', '-t', 'C,,', '-i', 'NODE_EXTRA_CA_CERTS configured public CA']],
                'profile_or_nss_database_archived': False, 'temporary_profile_removed': False}
    return profile, metadata


def run(args):
    before = identities()
    assert before['runtime']['index.html'] == EXPECTED_INDEX, 'Checkout is not the fixed final runtime'
    mode = args.mode
    proxy, transport_metadata = production_transport() if mode == 'production' else (None, {'scope': 'Local rehearsal; inherited browser transport unchanged.'})
    if mode == 'production':
        assert args.url, '--url is required for explicit production mode'
        parsed = urlsplit(args.url)
        assert parsed.scheme == 'https' and parsed.hostname and parsed.path in ('','/') and not parsed.query and not parsed.fragment and not parsed.username and not parsed.password, 'Use a normal HTTPS site root'
        server = nullcontext(args.url.rstrip('/') + '/')
    else:
        assert not args.url, 'Local rehearsal does not accept an external URL'
        os.environ['TASK_TRACER_PRODUCTION_HEADERS'] = '1'
        server = local_server()
    out = BASE / f'{mode}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}-{uuid.uuid4().hex[:10]}'
    out.mkdir()
    write_json(out / 'before.json', before)
    frozen = out / 'frozen-inputs'
    for name in RUNTIME + tuple(before['helpers']):
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    (frozen / 'driver.py').write_bytes(Path(__file__).read_bytes())
    report = {'mode': mode, 'started_at': datetime.now(timezone.utc).isoformat(),
              'output': str(out), 'argv': sys.argv, 'source_before': before,
              'production_transport': transport_metadata,
              'normal_motion': True, 'normal_csp': True, 'ignore_https_errors': False,
              'bypass_csp': False, 'fresh_isolated_context_per_combo': True,
              'runtime_scope': 'Five runtime inputs and actual transitive helpers/driver; promotional PNG deliberately not locked.',
              'runs': [], 'browsers_closed': {}, 'firefox_browser_launches': [], 'server_closed': False, 'passed': False}
    print('RUN_DIRECTORY', out, flush=True)
    expect.set_options(timeout=10000)
    try:
        with server as base_url, sync_playwright() as playwright:
            report['base_url'] = base_url
            for engine in ('chromium','firefox','webkit'):
                browser = None
                try:
                    options = browser_launch_options() if engine == 'chromium' else {'headless':True}
                    if mode == 'production':
                        options['proxy'] = proxy
                    firefox_persistent = mode == 'production' and engine == 'firefox'
                    if not firefox_persistent:
                        browser = getattr(playwright, engine).launch(**options)
                    for width,height in ((1280,900),(390,844)):
                        folder = out / f'{engine}-{width}'
                        folder.mkdir()
                        start = time.monotonic()
                        context_options = {'proxy': proxy} if mode == 'production' else {}
                        common_context = dict(viewport={'width':width,'height':height},locale='zh-CN',timezone_id='Asia/Shanghai',
                            reduced_motion='no-preference',color_scheme='light',accept_downloads=True,ignore_https_errors=False)
                        profile = None
                        trust_metadata = None
                        if firefox_persistent:
                            profile, trust_metadata = fresh_firefox_trust_profile()
                            try:
                                context = playwright.firefox.launch_persistent_context(profile.name, **options,
                                    firefox_user_prefs={'security.enterprise_roots.enabled':True}, **common_context)
                            except BaseException:
                                profile.cleanup()
                                trust_metadata['temporary_profile_removed'] = not Path(profile.name).exists()
                                raise
                            assert context.browser is not None, 'Persistent Firefox context has no public browser metadata'
                            current_browser = context.browser
                            report['firefox_browser_launches'].append({'width':width,'browser_version':current_browser.version,'closed':False})
                        else:
                            context = browser.new_context(**context_options, **common_context)
                            current_browser = browser
                        page = context.new_page()
                        page.set_default_timeout(10000)
                        errors = []
                        page.on('pageerror',lambda error:errors.append(str(error)))
                        item = {'engine':engine,'browser_version':current_browser.version,'width':width,'height':height,
                                'source_before':identities(),'passed':False,'context_closed':False,
                                'firefox_isolated_normal_ca_trust':trust_metadata}
                        try:
                            item['checks'] = exercise(page,context,base_url,engine,width,folder,mode,errors)
                            item['passed'] = True
                        except Exception:
                            item['exception'] = traceback.format_exc()
                            print(item['exception'],flush=True)
                            try:
                                page.screenshot(path=str(folder/'failure.png'),animations='allow')
                                (folder/'failure-dom.html').write_text(page.content())
                            except Exception:
                                item['failure_capture_exception'] = traceback.format_exc()
                        finally:
                            item['page_errors'] = list(errors)
                            try:
                                context.close()
                                item['context_closed'] = True
                                if firefox_persistent:
                                    report['firefox_browser_launches'][-1]['closed'] = True
                            finally:
                                if profile is not None:
                                    profile.cleanup()
                                    trust_metadata['temporary_profile_removed'] = not Path(profile.name).exists()
                            item['source_after'] = identities()
                            item['inputs_unchanged'] = item['source_before'] == item['source_after']
                            item['duration_seconds'] = round(time.monotonic()-start,3)
                            item['passed'] = item['passed'] and item['inputs_unchanged'] and not errors
                            write_json(folder/'report.json',item)
                            report['runs'].append(item)
                            print(json.dumps({'engine':engine,'width':width,'passed':item['passed'],'seconds':item['duration_seconds']},ensure_ascii=False),flush=True)
                finally:
                    if browser is not None:
                        browser.close()
                        report['browsers_closed'][engine] = True
                    elif engine == 'firefox' and mode == 'production':
                        report['browsers_closed'][engine] = len(report['firefox_browser_launches']) == 2 and all(item['closed'] for item in report['firefox_browser_launches'])
        report['server_closed'] = True
        report['passed'] = len(report['runs']) == 6 and all(run['passed'] for run in report['runs'])
    except Exception:
        report['exception'] = traceback.format_exc()
        print(report['exception'],flush=True)
    finally:
        report['source_after'] = identities()
        report['inputs_unchanged'] = before == report['source_after']
        report['passed'] = report['passed'] and report['inputs_unchanged']
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_json(out/'report.json',report)
        write_json(BASE/f'latest-{mode}.json',{'directory':str(out),'passed':report['passed']})
        print('REPORT',out/'report.json', 'PASS',report['passed'],flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('local','production'),default='local')
    parser.add_argument('--url')
    raise SystemExit(run(parser.parse_args()))
