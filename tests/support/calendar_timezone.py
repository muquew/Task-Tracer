"""Shared calendar timezone fixtures and assertions; no test entry point."""
from __future__ import annotations
from playwright.sync_api import expect

def open_day_task_form(page, day_button):
    """Follow the actual date -> agenda/capture -> full-form navigation."""
    day_key = day_button.get_attribute('data-calendar-add-date') or day_button.get_attribute('data-calendar-detail-date')
    through_capture = False
    day_button.click()
    modal = page.locator('#taskModal')
    if not modal.is_visible():
        shelf = page.locator('#captureShelf')
        agenda_add = page.locator(f'.calendar-agenda-add[data-calendar-add-date="{day_key}"]')
        if agenda_add.is_visible() and not shelf.is_visible():
            agenda_add.click()
        if shelf.is_visible():
            through_capture = True
            page.locator('#captureDetailsBtn').click()
    expect(modal).to_be_visible()
    return through_capture
