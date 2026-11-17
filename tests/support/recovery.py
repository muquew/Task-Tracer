"""Shared recovery fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.browser import open_settings
from playwright.sync_api import Page, expect

def open_recovery(page: Page) -> None:
    open_settings(page)
    page.locator("#recoveryBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    expect(page.locator("#recoverySelect")).to_have_count(1)
