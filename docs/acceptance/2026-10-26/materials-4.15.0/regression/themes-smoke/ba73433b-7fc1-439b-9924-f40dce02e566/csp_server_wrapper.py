#!/usr/bin/env python3
"""External header selection and passive identity observer; no test assertions replaced."""
from pathlib import Path
import hashlib
import http.server
import json
import os
import runpy
import sys

ROOT = Path('/workspace/Task-Tracer').resolve()
observation_path, bootstrap, entry, *arguments = sys.argv[1:]
sys.path.insert(0, str(ROOT / 'tools'))
observed = {'executed_tools': [], 'servers': [], 'browsers': [], 'documents': [],
            'context_count': 0, 'contexts_closed': 0, 'observer_errors': []}
executed = set()

def record_exec(event, args):
    if event != 'exec':
        return
    filename = getattr(args[0], 'co_filename', '')
    try:
        candidate = Path(filename).resolve()
        if candidate.is_relative_to(ROOT / 'tools') and candidate.is_file():
            executed.add(str(candidate.relative_to(ROOT)))
    except (OSError, ValueError):
        pass

sys.addaudithook(record_exec)
import smoke_playwright
from security_playwright import ProductionHeaderHandler
from playwright.sync_api import Browser, BrowserContext, BrowserType

# Selection occurs before the original entry point constructs its local server.
# The env path also selects this exact class for smoke's separate __main__ module.
os.environ['TASK_TRACER_PRODUCTION_HEADERS'] = '1'
os.environ.pop('TASK_TRACER_URL', None)
smoke_playwright.StaticHandler = ProductionHeaderHandler
original_server_init = http.server.HTTPServer.__init__

def server_init(self, server_address, RequestHandlerClass, *args, **kwargs):
    assert RequestHandlerClass is ProductionHeaderHandler, str(RequestHandlerClass)
    result = original_server_init(self, server_address, RequestHandlerClass, *args, **kwargs)
    observed['servers'].append({'address': list(self.server_address),
                                'handler': RequestHandlerClass.__module__ + '.' + RequestHandlerClass.__name__})
    return result

http.server.HTTPServer.__init__ = server_init
seen_pages = set()

def observe_page(page):
    if id(page) in seen_pages:
        return
    seen_pages.add(id(page))
    def response_event(response):
        if response.request.resource_type != 'document':
            return
        try:
            headers = response.all_headers()
            observed['documents'].append({'url': response.url, 'status': response.status,
                'from_service_worker': response.from_service_worker,
                'content-security-policy': headers.get('content-security-policy'),
                'x-content-type-options': headers.get('x-content-type-options')})
        except Exception as error:
            observed['observer_errors'].append(type(error).__name__ + ': ' + str(error))
    page.on('response', response_event)

def observe_context(context):
    observed['context_count'] += 1
    context.on('close', lambda *_: observed.__setitem__('contexts_closed', observed['contexts_closed'] + 1))
    context.on('page', observe_page)
    for page in context.pages:
        observe_page(page)
    return context

original_new_context = Browser.new_context
def new_context(self, *args, **kwargs):
    return observe_context(original_new_context(self, *args, **kwargs))
Browser.new_context = new_context
original_launch = BrowserType.launch
browser_refs = []
def launch(self, *args, **kwargs):
    browser = original_launch(self, *args, **kwargs)
    browser_refs.append(browser)
    observed['browsers'].append({'engine': self.name, 'version': browser.version,
        'executable_path': kwargs.get('executable_path'), 'launch_options': kwargs})
    return browser
BrowserType.launch = launch
original_persistent = BrowserType.launch_persistent_context
def persistent(self, *args, **kwargs):
    context = original_persistent(self, *args, **kwargs)
    observed['browsers'].append({'engine': self.name, 'persistent': True,
        'executable_path': kwargs.get('executable_path'), 'launch_options': kwargs})
    return observe_context(context)
BrowserType.launch_persistent_context = persistent

try:
    sys.argv = [bootstrap, entry, *arguments]
    runpy.run_path(bootstrap, run_name='__main__')
finally:
    observed['executed_tools'] = sorted(executed)
    # Successful original paths close their own resources. A failure is retained,
    # and its still-live browser is closed here before this worker exits.
    observed['browser_connected_before_final_cleanup'] = [browser.is_connected() for browser in browser_refs]
    for browser in browser_refs:
        if browser.is_connected():
            browser.close()
    observed['browser_connected_after_final_cleanup'] = [browser.is_connected() for browser in browser_refs]
    Path(observation_path).write_text(json.dumps(observed, ensure_ascii=False, indent=2) + '\n')
