from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, sys, os
from playwright.sync_api import sync_playwright, expect

ROOT = Path('/workspace/task-tracer-final-baseline')
OUT = Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/baseline-matrix/probes')
sys.path.insert(0, str(ROOT / 'tools'))
from smoke_playwright import local_server, add_task, task_locator

errors = []
with local_server() as url, sync_playwright() as playwright:
    browser = playwright.webkit.launch(headless=True, timeout=30000)
    context = browser.new_context(viewport={'width': 1280, 'height': 800}, locale='zh-CN', timezone_id='Asia/Shanghai', reduced_motion='no-preference')
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    response = page.goto(url, wait_until='networkidle')
    source = hashlib.sha256(response.body()).hexdigest()
    assert source == 'bfb0a142fb4c813e17af52267062c6faa63a7a56bd5e41feb335728c1999e9c5', source
    add_task(page, 'WebKit sysroot render probe', no_deadline=True, project='Probe')
    expect(task_locator(page, 'WebKit sysroot render probe')).to_have_count(1)
    page.wait_for_timeout(350)
    page.screenshot(path=str(OUT / 'webkit-actual-render.png'))
    data = {'at': datetime.now(timezone.utc).isoformat(), 'engine': 'webkit', 'version': browser.version, 'source_index_sha256': source, 'http_status': response.status, 'http_headers': response.all_headers(), 'viewport': {'width': 1280, 'height': 800}, 'page_errors': errors, 'task_count': page.locator('.task-item').count(), 'html_width': page.evaluate('document.documentElement.scrollWidth'), 'viewport_width': page.evaluate('innerWidth'), 'official_nonstandard_sysroot_environment': {'LD_LIBRARY_PATH': os.environ.get('LD_LIBRARY_PATH'), 'PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS': os.environ.get('PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS')}, 'browser_closed': False, 'server_closed': False, 'scope': 'Actual WebKit launch/render/real form save with original native local HTTP handler, no CSP or assertion changes. This is a readiness probe, not the registered33 result.'}
    assert not errors and data['html_width'] <= data['viewport_width'], data
    context.close()
    browser.close()
data['browser_closed'] = True
data['server_closed'] = True
(OUT / 'webkit-actual-render.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(data, ensure_ascii=False, indent=2))
