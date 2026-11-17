"""Shared direct capture fixtures and assertions; no test entry point."""
from __future__ import annotations
from playwright.sync_api import expect
from tests.support.browser import close_workspace_navigation, get_task_records

def records_unchanged(page, before, phase):
    assert get_task_records(page) == before, f'{phase} changed stored tasks'

def direct_editor(page):
    close_workspace_navigation(page)
    expect(page.locator('#openModalBtn')).to_have_count(1)
    expect(page.locator('#openModalBtn')).to_be_visible()
    expect(page.locator('#openModalBtn')).to_have_attribute('aria-controls', 'taskModal')
    page.locator('#openModalBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#captureShelf')).to_be_hidden()
    expect(page.locator('#taskName')).to_be_focused()

def cancel_empty(page):
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('#captureShelf')).to_be_hidden()
    expect(page.locator('#openModalBtn')).to_be_focused()
    expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
