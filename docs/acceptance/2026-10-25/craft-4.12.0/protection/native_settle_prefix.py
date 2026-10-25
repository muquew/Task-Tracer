#!/usr/bin/env python3
"""Verify the committed native animation settler at the original failure path."""
from pathlib import Path
import sys

ROOT=Path('/workspace/Task-Tracer-craft')
sys.path.insert(0,str(ROOT/'tools'))
from playwright.sync_api import sync_playwright
import accessibility_i18n_audit as audit
from smoke_playwright import browser_launch_options,clear_app_data,exercise_workspace_navigation,local_server

with local_server() as url,sync_playwright() as playwright:
    browser=playwright.chromium.launch(**browser_launch_options())
    context=browser.new_context(viewport={'width':1280,'height':720},reduced_motion='no-preference')
    try:
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        clear_app_data(page,url)
        axe=audit.find_axe_source().read_text()
        exercise_workspace_navigation(page)
        audit.audit_page_state(page,axe,'native prefix empty list')
        audit.seed_tasks(page)
        audit.audit_subtask_checkbox_visibility(page,'native prefix 1280px')
        audit.audit_page_state(page,axe,'native prefix populated list after both themes')
        audit.audit_batch_project(page,axe)
        assert not errors,errors
        print('Native settle prefix passed: original shared helper at all three callers, both-theme subtask states and batch More/move dialog axe/focus/layout; no external animation override',flush=True)
    finally:
        context.close()
        browser.close()
