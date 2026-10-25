#!/usr/bin/env python3
"""Read-only source diagnosis; the z-index trial exists only in the browser."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/workspace/Task-Tracer')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))

from playwright.sync_api import expect, sync_playwright
from service_worker_update_playwright import UpdateServer, current_bundle
from smoke_playwright import browser_launch_options, clear_app_data, ensure_capture, task_locator


def inspect(page, task):
    return task.evaluate('''task => {
        const bounds = node => {
            const r = node.getBoundingClientRect();
            return {x:r.x,y:r.y,width:r.width,height:r.height,top:r.top,bottom:r.bottom,left:r.left,right:r.right};
        };
        const describe = node => {
            const s = getComputedStyle(node);
            return {tag:node.tagName,id:node.id,className:node.className,
                position:s.position,zIndex:s.zIndex,transform:s.transform,filter:s.filter,
                backdropFilter:s.backdropFilter,opacity:s.opacity,isolation:s.isolation,
                contain:s.contain,overflow:s.overflow,rect:bounds(node)};
        };
        const edit = task.querySelector('[data-action="edit"]');
        const menu = task.querySelector('.task-action-menu');
        const trigger = task.querySelector('.task-more-toggle');
        const r = edit.getBoundingClientRect();
        const point = {x:r.left+r.width/2,y:r.top+r.height/2};
        const ancestry=[];
        for(let node=menu;node;node=node.parentElement) ancestry.push(describe(node));
        return {scrollY:scrollY,viewport:{width:innerWidth,height:innerHeight},
            trigger:describe(trigger),menu:describe(menu),edit:describe(edit),
            editCenter:point,hitChain:document.elementsFromPoint(point.x,point.y).map(describe),
            capture:describe(document.querySelector('#captureShelf')),
            tools:describe(document.querySelector('#toolsDrawer')),
            topbar:describe(document.querySelector('header.workspace-topbar')),
            menuAncestry:ancestry};
    }''')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    release = current_bundle()
    source = OUT / 'source-snapshot'
    source.mkdir(exist_ok=True)
    (source / 'index.html').write_bytes(release.files['index.html'])
    report = {
        'source_version': release.version,
        'source_index_sha256': hashlib.sha256(release.files['index.html']).hexdigest(),
        'fixture': 'Unmodified source bundle; same UTC clock and first quick-add input as quick_add_date weekday regression',
        'steps': [],
    }
    server = UpdateServer(release)
    server.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**browser_launch_options())
            context = browser.new_context(timezone_id='UTC',locale='en-US',reduced_motion='reduce')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.clock.install(time=datetime(2026,3,1,12,tzinfo=timezone.utc))
            try:
                clear_app_data(page, server.url)
                page.clock.set_system_time(datetime(2026,10,25,12,tzinfo=timezone.utc))
                ensure_capture(page).fill('周三 14:00 Weekday civil capture 0')
                page.locator('#quickAddInput').press('Enter')
                expect(page.locator('#quickAddInput')).to_have_value('')
                task = task_locator(page, 'Weekday civil capture 0')
                expect(task).to_be_visible()
                page.screenshot(path=str(OUT / '01-before-menu.png'))
                task.locator('.task-more-toggle').click()
                report['opened_menu'] = inspect(page, task)
                page.screenshot(path=str(OUT / '02-open-menu-overlapped.png'))
                try:
                    task.locator('[data-action="edit"]').click(timeout=1800)
                    report['original_click'] = {'success':True}
                except Exception as error:
                    report['original_click'] = {'success':False,'error':str(error)}
                report['after_click_attempt'] = inspect(page, task)
                page.screenshot(path=str(OUT / '03-failed-edit-click.png'))
                assert report['original_click']['success'] is False, 'Original bug did not reproduce'
                # A controlled paint-order experiment, without changing source,
                # menu dimensions, scroll position, or the hit-test rules.
                page.add_style_tag(content='.task-action-menu { z-index: 1000 !important; }')
                report['browser_only_zindex_trial'] = inspect(page, task)
                page.screenshot(path=str(OUT / '04-browser-only-zindex-1000.png'))
                task.locator('[data-action="edit"]').click(timeout=5000)
                expect(page.locator('#taskModal')).to_be_visible()
                expect(page.locator('#taskName')).to_have_value('Weekday civil capture 0')
                report['browser_only_zindex_trial']['native_edit_click_succeeded'] = True
                page.screenshot(path=str(OUT / '05-trial-native-edit-click-success.png'))
                report['page_errors'] = errors
                assert errors == [], errors
                report['status'] = 'reproduced-and-isolated'
            except Exception:
                report['status'] = 'diagnostic-error'
                raise
            finally:
                (OUT / 'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                context.close()
                browser.close()
    finally:
        server.stop()


if __name__ == '__main__':
    main()
