"""Screenshot preparation; natural toast expiry is accepted after a bounded click."""
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def dismiss_notice(page):
    close = page.locator('#workspaceNotificationClose')
    if close.is_visible():
        try:
            close.click(timeout=5000)
        except PlaywrightTimeoutError:
            if close.is_visible():
                raise

def capture(page, output, name):
    dismiss_notice(page)
    page.wait_for_function("""() => document.getAnimations().every(animation =>
        animation.playState !== 'running' || animation.effect?.getComputedTiming().iterations === Infinity)""")
    page.screenshot(path=str(output / f'{name}.png'), full_page=False)
