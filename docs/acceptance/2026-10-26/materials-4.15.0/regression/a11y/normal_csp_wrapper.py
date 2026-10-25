#!/usr/bin/env python3
"""Compile expression-style automation waits as ordinary function predicates."""
from pathlib import Path
import re
import runpy
import sys

from playwright.sync_api import Page

original_wait = Page.wait_for_function

def wait_function(self, expression, *, arg=None, polling=None, timeout=None):
    function = re.match(r'^\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>', expression)
    if not function and not re.match(r'^\s*(?:async\s+)?function\b', expression):
        expression = '() => (' + expression + ')'
    return original_wait(self, expression, arg=arg, polling=polling, timeout=timeout)

Page.wait_for_function = wait_function
sys.path.insert(0, '/workspace/Task-Tracer/tools')
import smoke_playwright
from security_playwright import ProductionHeaderHandler
smoke_playwright.StaticHandler = ProductionHeaderHandler
entry, *arguments = sys.argv[1:]
sys.path.insert(0, str(Path(entry).parent))
sys.argv = [entry, *arguments]
print('External harness: expression waits compiled as function predicates; deployment CSP and service worker unchanged', flush=True)
runpy.run_path(entry, run_name='__main__')
