"""External 4.9.0 actual-domain core acceptance in two fresh viewports per engine."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import traceback
import uuid

sys.dont_write_bytecode = True
from release_490_common import (AcceptedCandidate, CACHE_NAME, ROOT, SAFE_HEADERS, SITE,
    archive_preparation, base_parser, inherited_proxy, normalize_csp, now,
    require_execution, seal, sha)

FORWARDER_PATH = Path(__file__).with_name('release_490_proxy_forwarder.py')
FORWARDER_SHA256 = '068c4fc3a6335c7abf779bb4794d38126eb9435792dc48730b4a2e61464b1dbf'
CORE_SCOPE = ('Actual-domain language/theme and empty-workspace date navigation; task add/edit/reload; '
              'four views; completion; actual backup and safety downloads; replacement import/subtask normalization; '
              'delete; service-worker-controlled HTTP200 reload with network unavailable and empty persisted records.')


def forwarder_class():
    assert sha(FORWARDER_PATH.read_bytes()) == FORWARDER_SHA256, 'Validated relay source differs'
    spec = importlib.util.spec_from_file_location('release_490_proxy_forwarder', FORWARDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SessionProxyForwarder


def firefox_context(playwright, proxy, viewport, state):
    ca = Path(os.environ.get('NODE_EXTRA_CA_CERTS', ''))
    assert ca.resolve() == Path('/usr/local/share/ca-certificates/environment-proxy-ca.crt').resolve(), 'Unexpected configured public platform CA path'
    bundle = os.environ.get('SSL_CERT_FILE')
    assert bundle, 'Configured system CA bundle required'
    pem = ca.read_text()
    der = ssl.PEM_cert_to_DER_cert(pem)
    metadata = subprocess.check_output(['openssl', 'x509', '-in', str(ca), '-noout', '-subject', '-issuer', '-dates', '-fingerprint', '-sha256', '-ext', 'basicConstraints'], text=True)
    assert 'CA:TRUE' in metadata and 'OpenAI' in metadata, 'Provisioned public CA metadata not recognized'
    verification = subprocess.check_output(['openssl', 'verify', '-CAfile', bundle, str(ca)], text=True)
    profile = tempfile.TemporaryDirectory(prefix='task-tracer-490-production-firefox-nss-')
    state['session_ca_trust'] = {'configured_public_ca': str(ca), 'pem_sha256': sha(pem.encode()),
        'der_sha256': sha(der), 'public_certificate_metadata': metadata,
        'system_bundle_verification': verification.strip(), 'ephemeral_profile': profile.name,
        'global_trust_modified': False, 'certificate_exceptions': False,
        'nss_export_der_equal': False, 'ephemeral_profile_removed': False}
    try:
        database = 'sql:' + profile.name
        nickname = 'Task Tracer session environment proxy CA'
        calls = [['certutil', '-N', '-d', database, '--empty-password'],
                 ['certutil', '-A', '-d', database, '-n', nickname, '-t', 'C,,', '-i', str(ca)]]
        for command in calls:
            subprocess.run(command, check=True, capture_output=True, text=True)
        exported = subprocess.check_output(['certutil', '-L', '-d', database, '-n', nickname, '-a'], text=True)
        assert ssl.PEM_cert_to_DER_cert(exported) == der, 'NSS imported DER differs from provisioned public CA'
        listing = subprocess.check_output(['certutil', '-L', '-d', database], text=True)
        assert nickname in listing and 'C,,' in listing
        state['session_ca_trust'].update(nss_export_der_equal=True, nss_import_commands=calls, nss_trust_listing=listing)
        context = playwright.firefox.launch_persistent_context(profile.name, headless=True,
            timeout=30000, proxy=proxy, locale='en-US', viewport=viewport,
            accept_downloads=True, reduced_motion='reduce', ignore_https_errors=False, bypass_csp=False)
        return context, profile
    except BaseException:
        profile.cleanup()
        state['session_ca_trust']['ephemeral_profile_removed'] = not Path(profile.name).exists()
        raise


def run_combination(candidate, engine, width, directory):
    from playwright.sync_api import expect, sync_playwright
    from validate_static import app_version
    from smoke_playwright import (SW_CACHE_NAME, add_task, assert_theme_chrome,
        close_workspace_navigation, complete_task, delete_task, edit_task,
        exercise_export_backup, exercise_import, exercise_language,
        exercise_workspace_date_focus, exercise_workspace_navigation, get_task_records,
        select_theme_preference, select_view, task_locator, wait_for_app_ready)
    assert SW_CACHE_NAME == CACHE_NAME
    viewport = {'width': width, 'height': 800 if width == 1280 else 844}
    directory.mkdir()
    state = {**candidate.record(), 'schema_version': 1, 'run_id': str(uuid.uuid4()),
        'engine': engine, 'viewport': viewport, 'actual_browser_version': None,
        'status': 'initializing', 'completed': False, 'passed': False,
        'started_at': now(), 'finished_at': None, 'scope': CORE_SCOPE,
        'tls_verification_enabled': True, 'ignore_https_errors': False, 'bypass_csp': False,
        'proxy_inherited': True, 'fresh_synthetic_context': True, 'storage_state_supplied': False,
        'context_closed': False, 'browser_closed': False,
        'page_errors': [], 'console_errors': [], 'request_failures': [], 'http_errors': [],
        'checks': [], 'screenshots': [], 'downloads': [], 'error': None}
    result_path = directory / 'result.json'
    publish = lambda: candidate.atomic_report(result_path, state)
    publish()
    browser = context = page = profile = relay = None
    tracing = False

    def screenshot(filename, description):
        path = directory / filename
        page.screenshot(path=path, animations='disabled')
        state['screenshots'].append({'filename': filename, 'state': description,
            'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes()),
            'manually_inspected': False})
        publish()

    try:
        candidate.check()
        with sync_playwright() as playwright:
            try:
                proxy = inherited_proxy()
                if engine == 'firefox':
                    context, profile = firefox_context(playwright, proxy, viewport, state)
                    browser = context.browser
                    assert browser is not None
                else:
                    options = {'headless': True, 'timeout': 30000, 'proxy': proxy}
                    if engine == 'chromium':
                        assert Path('/usr/bin/chromium').is_file(), 'System Chromium unavailable'
                        options['executable_path'] = '/usr/bin/chromium'
                        state['browser_executable'] = '/usr/bin/chromium'
                    else:
                        relay = forwarder_class()()
                        options['proxy'] = {**proxy, 'server': relay.start()}
                        state['relay_source_sha256'] = FORWARDER_SHA256
                        state['transport_started'] = relay.snapshot()
                        state['host_requirement_override'] = os.environ.get('PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS') == '1'
                    browser = getattr(playwright, engine).launch(**options)
                    context = browser.new_context(locale='en-US', viewport=viewport,
                        accept_downloads=True, reduced_motion='reduce', ignore_https_errors=False,
                        bypass_csp=False, service_workers='allow')
                state['actual_browser_version'] = browser.version
                state['status'] = 'running'
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
                tracing = True
                page = context.new_page()
                downloads = []
                page.on('pageerror', lambda error: state['page_errors'].append(str(error)))
                page.on('console', lambda message: state['console_errors'].append(message.text) if message.type == 'error' else None)
                page.on('requestfailed', lambda request: state['request_failures'].append({'url': request.url, 'failure': request.failure}))
                page.on('response', lambda response: state['http_errors'].append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
                page.on('download', lambda download: downloads.append(download))
                response = page.goto(SITE, wait_until='domcontentloaded', timeout=45000)
                assert response is not None and response.status == 200 and response.url == SITE
                body = response.body()
                (directory / 'online-index.html').write_bytes(body)
                state['online_html'] = {'url': response.url, 'status': response.status,
                    'from_service_worker': response.from_service_worker,
                    'bytes': len(body), 'sha256': sha(body),
                    'expected_sha256': candidate.freeze['source']['files']['index.html'],
                    'headers': {key: response.headers[key] for key in SAFE_HEADERS if key in response.headers}}
                assert not response.from_service_worker, 'Fresh online origin HTML must be a network response'
                assert body == (ROOT / 'index.html').read_bytes(), 'Production HTML differs from accepted source'
                state['loaded_app_version'] = app_version(body.decode('utf-8'))
                assert state['loaded_app_version'] == '4.9.0'
                expected_csp = next(header['value'] for route in json.loads((ROOT / 'vercel.json').read_text())['headers']
                    if route['source'] == '/(.*)' for header in route['headers'] if header['key'].lower() == 'content-security-policy')
                assert normalize_csp(response.headers.get('content-security-policy', '')) == normalize_csp(expected_csp), 'Production CSP differs'
                wait_for_app_ready(page)
                assert get_task_records(page) == [], 'Context was not a fresh empty synthetic workspace'
                expect(page.locator('.task-item')).to_have_count(0)
                state['checks'].append('Network HTML bytes and CSP equal frozen candidate; initially empty synthetic workspace')
                exercise_language(page)
                close_workspace_navigation(page)
                exercise_workspace_navigation(page)
                schedule = page.locator('#workspaceScheduleToggle')
                if schedule.is_visible():
                    schedule.click()
                    expect(page.locator('#workspaceScheduleDialog')).to_be_visible()
                    screenshot('01-narrow-schedule.png', 'New native schedule dialog open with empty synthetic workspace')
                    page.locator('#workspaceScheduleClose').click()
                    expect(page.locator('#workspaceScheduleDialog')).to_be_hidden()
                exercise_workspace_date_focus(page)
                state['checks'].append('English/Chinese native language; responsive navigation; empty week/mini date entries preserve records and visible focus; narrow native schedule when applicable')
                name = f'PROD-490 synthetic {engine}-{width}'
                edited, imported = name + ' edited', name + ' restored'
                add_task(page, name, no_deadline=True, project='Production Acceptance Synthetic', tags=['synthetic', engine])
                edit_task(page, name, edited)
                page.reload(wait_until='domcontentloaded')
                wait_for_app_ready(page)
                expect(task_locator(page, edited)).to_have_count(1)
                for view in ('calendar', 'timeline', 'stats', 'list'):
                    select_view(page, view)
                    expect(page.locator('#taskList')).to_have_attribute('aria-labelledby', f'viewTab-{view}')
                state['checks'].append('Task add/edit/reload persistence and all four views using current business helpers')
                before_theme = get_task_records(page)
                for preference in ('light', 'dark'):
                    select_theme_preference(page, preference)
                    close_workspace_navigation(page)
                    assert_theme_chrome(page)
                    assert get_task_records(page) == before_theme, 'Appearance switch changed task records'
                    screenshot(f'02-online-{preference}.png', f'{preference} theme after persisted add/edit; unchanged synthetic records')
                select_theme_preference(page, 'system')
                close_workspace_navigation(page)
                assert_theme_chrome(page)
                assert get_task_records(page) == before_theme
                state['checks'].append('Native light/dark/system appearance and resolved chrome; no task-record mutation')
                complete_task(page, edited)
                backup = exercise_export_backup(page)
                assert any(task['name'] == edited and task['completed'] for task in backup['tasks'])
                exercise_import(page, imported)
                records = get_task_records(page)
                assert len(records) == 1 and records[0]['name'] == imported
                state['imported_records'] = records
                assert len(downloads) == 2, 'Expected real task backup and pre-import safety download'
                for number, download in enumerate(downloads, 1):
                    target = directory / f'download-{number}.json'
                    download.save_as(target)
                    state['downloads'].append({'filename': target.name, 'suggested_filename': download.suggested_filename,
                        'bytes': target.stat().st_size, 'sha256': sha(target.read_bytes())})
                screenshot('03-online-restored.png', 'Replacement import with two normalized subtasks and one semantically checked; image not yet manually inspected')
                state['checks'].append('Completion; real export and safety downloads; replacement import and subtask normalization with current helper assertions')
                delete_task(page, imported)
                page.wait_for_function("async name => navigator.serviceWorker.controller && (await caches.keys()).includes(name)", arg=CACHE_NAME)
                state['service_worker_ready_before_offline'] = True
                if engine in ('chromium', 'firefox'):
                    context.set_offline(True)
                    state['offline_method'] = 'Normal context.set_offline(True) API'
                else:
                    state['offline_method'] = 'Validated inherited-proxy byte relay fully stopped; no destination bypass or TLS interception'
                    state['transport_before_cut'] = relay.snapshot()
                    state['transport_after_cut'] = relay.stop()
                    try:
                        unexpected = socket.create_connection((relay.host, relay.port), timeout=1)
                    except OSError:
                        state['fresh_connection_refused_after_cut'] = True
                    else:
                        unexpected.close()
                        raise AssertionError('Stopped relay accepted a fresh connection')
                response = page.reload(wait_until='domcontentloaded')
                wait_for_app_ready(page)
                expect(page.locator('.task-item')).to_have_count(0)
                state['offline_observation'] = page.evaluate("() => ({online:navigator.onLine,controlled:Boolean(navigator.serviceWorker.controller),url:location.href,lang:document.documentElement.lang,scrollWidth:document.documentElement.scrollWidth,innerWidth})")
                state['offline_response'] = {'status': response.status if response else None,
                    'from_service_worker': response.from_service_worker if response else None}
                assert response is not None and response.status == 200 and response.from_service_worker
                assert state['offline_observation']['controlled'] and get_task_records(page) == []
                assert state['offline_observation']['scrollWidth'] <= state['offline_observation']['innerWidth'] + 1
                if engine in ('chromium', 'firefox'):
                    assert state['offline_observation']['online'] is False
                else:
                    state['transport_after_cached_reload'] = relay.snapshot()
                    for key in ('accepted_clients', 'upstream_connections_opened', 'bytes_to_upstream', 'bytes_to_client'):
                        assert state['transport_after_cached_reload'][key] == state['transport_after_cut'][key]
                screenshot('04-offline-after-delete.png', 'Network unavailable; HTTP200 from service worker; deleted task remains absent')
                assert not state['page_errors'], 'Unexpected page errors'
                assert not state['console_errors'], 'Unexpected console errors'
                assert not state['request_failures'], 'Unexpected failed requests'
                assert not state['http_errors'], 'Unexpected HTTP errors'
                state['checks'].append('Actual network-unavailable SW HTTP200 reload, empty persisted records, no overflow or runtime/console/network errors')
                candidate.finish_identity(state)
                state.update(status='passed', passed=True)
            except BaseException as error:
                state.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
                if page is not None:
                    try:
                        page.screenshot(path=directory / 'failure.png', timeout=5000)
                    except BaseException as failure:
                        state['failure_screenshot_error'] = type(failure).__name__
                if context is not None and tracing:
                    try:
                        context.tracing.stop(path=directory / 'failure-trace.zip')
                        tracing = False
                    except BaseException as failure:
                        state['failure_trace_error'] = type(failure).__name__
            finally:
                if context is not None:
                    try:
                        if tracing:
                            context.tracing.stop()
                    except BaseException as failure:
                        state.update(status='failed', passed=False, trace_cleanup_error=type(failure).__name__)
                    finally:
                        try:
                            context.close()
                            state['context_closed'] = True
                            if engine == 'firefox':
                                state['browser_closed'] = True
                        except BaseException as failure:
                            state.update(status='failed', passed=False, context_cleanup_error=type(failure).__name__)
                if browser is not None and engine != 'firefox':
                    try:
                        browser.close()
                        state['browser_closed'] = True
                    except BaseException as failure:
                        state.update(status='failed', passed=False, browser_cleanup_error=type(failure).__name__)
    except BaseException as error:
        state.update(status='failed', passed=False, error=state['error'] or f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    finally:
        if relay is not None:
            try:
                state['final_transport_state'] = relay.stop()
            except BaseException as failure:
                state.update(status='failed', passed=False, transport_cleanup_error=type(failure).__name__)
        if profile is not None:
            try:
                name = profile.name
                profile.cleanup()
                state['session_ca_trust']['ephemeral_profile_removed'] = not Path(name).exists()
                assert state['session_ca_trust']['ephemeral_profile_removed']
            except BaseException as failure:
                state.update(status='failed', passed=False, profile_cleanup_error=type(failure).__name__)
        try:
            candidate.finish_identity(state)
        except BaseException as failure:
            state.update(status='failed', passed=False, identity_error=f'{type(failure).__name__}: {failure}')
        if any(state[key] for key in ('page_errors', 'console_errors', 'request_failures', 'http_errors')):
            state.update(status='failed', passed=False, error=state['error'] or 'Unexpected browser errors retained through final cleanup')
        if state['passed'] and not (state['context_closed'] and state['browser_closed']):
            state.update(status='failed', passed=False, error='Browser/context closure not confirmed')
        state.update(completed=True, finished_at=now())
        publish()
    print(json.dumps({'engine': engine, 'width': width, 'status': state['status'], 'result': str(result_path)}), flush=True)
    return state


def main():
    parser = base_parser(__doc__)
    parser.add_argument('--engine', choices=('all', 'chromium', 'firefox', 'webkit'), default='all')
    args = parser.parse_args()
    require_execution(parser, args)
    candidate = AcceptedCandidate(args)
    inherited_proxy()
    engines = ('chromium', 'firefox', 'webkit') if args.engine == 'all' else (args.engine,)
    directory = args.output_root / 'browser-core' / str(uuid.uuid4())
    archive_preparation(candidate, directory, __file__, (FORWARDER_PATH,))
    planned = [{'engine': engine, 'width': width} for engine in engines for width in (1280, 390)]
    record = {**candidate.record(), 'schema_version': 1, 'run_id': directory.name,
        'started_at': now(), 'finished_at': None, 'status': 'running', 'completed': False,
        'passed': False, 'planned': planned, 'checks': [], 'current': None, 'error': None,
        'scope': CORE_SCOPE, 'identical_core_for_each_planned_combination': True,
        'historical_webkit_offline_api_failure': 'Retained separately; WebKit transport loss is not a passed context.set_offline navigation result.',
        'limits': ['Linux browsers and narrow viewports are not physical mobile/Safari/iOS or OS installation/reboot/IME/screen-reader/system-notification acceptance.',
                   'This is the declared actual-domain core sequence, not the full specialized checker/matrix or full WCAG certification.',
                   'Saved screenshots start manually_inspected=false; no image is claimed inspected by this runner.']}
    report_path = directory / 'report.json'
    publish = lambda: candidate.atomic_report(report_path, record)
    publish()
    print('EVIDENCE_DIRECTORY=' + str(directory), flush=True)
    try:
        for planned_entry in planned:
            candidate.check()
            record['current'] = {**planned_entry, 'started_at': now()}
            publish()
            engine, width = planned_entry['engine'], planned_entry['width']
            result = run_combination(candidate, engine, width, directory / f'{engine}-{width}')
            record['checks'].append({'engine': engine, 'width': width, 'passed': result['passed'],
                'result_file': f'{engine}-{width}/result.json', 'completed': result['completed']})
            publish()
            if not result['passed']:
                raise RuntimeError(f'First failed production combination preserved: {engine}-{width}')
        assert len(record['checks']) == len(planned) and all(item['passed'] for item in record['checks'])
        candidate.finish_identity(record)
        record.update(status='passed', passed=True)
    except BaseException as error:
        record.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    finally:
        try:
            candidate.finish_identity(record)
        except BaseException as error:
            record.update(status='failed', passed=False, identity_error=f'{type(error).__name__}: {error}')
        record.update(completed=True, finished_at=now(), current=None)
        publish()
        seal(directory, candidate.atomic_report)
    print(json.dumps({'status': record['status'], 'passed': record['passed'], 'report': str(report_path)}), flush=True)
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
