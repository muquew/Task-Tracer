"""Shared views delete fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.browser import return_to_task_workspace
from playwright.sync_api import expect
from tests.support.storage import config, stored

def save_named(page, name, query):
    return_to_task_workspace(page)
    page.locator('#searchInput').fill(query)
    page.locator('#saveSmartViewBtn').click()
    page.locator('#savedViewNameInput').fill(name)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    return next(view for view in config(stored(page))['savedViews'] if view['searchQuery'] == query)
