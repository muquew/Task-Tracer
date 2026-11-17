#!/usr/bin/env python3
"""Exercise modeless task transitions, responsive drafts and persisted-data safety."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import uuid

from playwright.sync_api import sync_playwright

from tests.support.browser import browser_launch_options, clear_app_data
from tests.support.contextual_editor import (
    breakpoint_and_short_screen,
    clean_and_dirty_transitions,
    fixture,
    oversized_description,
    today_context,
    title_input_and_save,
)
from tests.support.http import local_server


def run(browser_name, output):
    with local_server() as url, sync_playwright() as p:
        browser = getattr(p, browser_name).launch(**browser_launch_options(browser_name))
        context = browser.new_context(viewport={'width': 1440, 'height': 900},
                                      locale='zh-CN', reduced_motion='reduce')
        try:
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            clear_app_data(page, url)
            baseline = fixture(page)
            results = [clean_and_dirty_transitions(page, baseline),
                       today_context(page, baseline),
                       breakpoint_and_short_screen(page, baseline),
                       oversized_description(page, baseline, output / f'{browser_name}-{uuid.uuid4().hex[:8]}'),
                       title_input_and_save(page, baseline)]
            assert not errors, errors
            print(json.dumps({'passed': True, 'browser': browser_name, 'version': browser.version,
                              'checks': results, 'page_errors': errors}, ensure_ascii=False))
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--output', type=Path, default=Path('dist/contextual-editor'))
    args = parser.parse_args()
    run(args.browser, args.output)
