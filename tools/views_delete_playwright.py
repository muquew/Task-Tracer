#!/usr/bin/env python3
"""Confirm saved-view deletion while preserving tasks, concurrent views and later drafts."""
from __future__ import annotations

from smoke_playwright import open_task_editor

from smoke_playwright import return_to_task_workspace

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

from recovery_management_playwright import config, stored
from smoke_playwright import reveal_workspace_control, select_language
from smoke_playwright import add_task, browser_launch_options, clear_app_data, local_server, wait_for_app_ready


def save_named(page, name, query):
    return_to_task_workspace(page)
    page.locator('#searchInput').fill(query)
    page.locator('#saveSmartViewBtn').click()
    page.locator('#savedViewNameInput').fill(name)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    return next(view for view in config(stored(page))['savedViews'] if view['searchQuery'] == query)


def prepare(page, url):
    clear_app_data(page,url)
    add_task(page,'Tasks remain unchanged when deleting a view',no_deadline=True)


def delete_button(page, view):
    return page.locator(f'[data-saved-view-delete-id="{view["id"]}"]')


def apply_button(page, view):
    return page.locator(f'[data-saved-view-id="{view["id"]}"]')


def open_delete(page, view):
    reveal_workspace_control(page, delete_button(page,view)).click()
    expect(page.locator('#savedViewDeleteConfirm')).to_be_visible()
    expect(page.locator('#savedViewDeleteName')).to_have_text(view['name'])
    language = page.locator('html').get_attribute('lang')
    translations = json.loads((Path(__file__).resolve().parents[1]/'resources'/f'{language}.json').read_text())['savedViews']
    expect(page.locator('#modalTitle')).to_have_text(translations['deleteConfirmTitle'])
    expect(page.locator('#savedViewDeleteConfirm')).to_have_text(translations['deleteConfirmMessage'].replace('{name}',view['name']))
    expect(page.locator('#submitBtn')).to_have_text(translations['deleteConfirmAction'])
    expect(page.locator('#cancelBtn')).to_be_focused()


def assert_only_selected_removed(page, before, selected):
    after = stored(page)
    expected = config(before)
    expected['savedViews'] = [view for view in expected['savedViews'] if view['id'] != selected['id']]
    assert after['tasks'] == before['tasks'], 'View deletion changed task contents'
    assert config(after) == expected, 'View deletion changed an unrelated view, task revision, backup metadata or another setting'
    return after


def click_paused_clock_control(page, control):
    expect(control).to_be_visible()
    expect(control).to_be_enabled()
    point = control.evaluate("""node => {
        const rect = node.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const target = document.elementFromPoint(x,y);
        return {x,y,hit:Boolean(target && (target === node || node.contains(target)))};
    }""")
    assert point['hit'], 'The pointer target is covered or outside the visible viewport'
    page.mouse.click(point['x'],point['y'])


def cancellation(page, url):
    prepare(page,url)
    view = save_named(page,'<img src=x onerror=window.viewDeleteXss=1>','project:cancel-deletion')
    for language in ('en','zh-CN'):
        select_language(page, language)
        expect(page.locator('html')).to_have_attribute('lang',language)
        page.keyboard.press('Escape')
        before = stored(page)
        for path in ('cancel','enter','escape','x','backdrop'):
            open_delete(page,view)
            assert stored(page) == before, 'Opening a deletion confirmation already changed stored data'
            assert page.locator('#savedViewDeleteConfirm img').count() == 0
            assert not page.evaluate('Boolean(window.viewDeleteXss)')
            if path == 'cancel':
                page.locator('#cancelBtn').click()
            elif path == 'enter':
                page.keyboard.press('Enter')
            elif path == 'escape':
                page.keyboard.press('Escape')
            elif path == 'x':
                page.locator('#closeModalBtn').click()
            else:
                page.locator('#taskModal').click(position={'x':2,'y':2})
            expect(page.locator('#taskModal')).to_be_hidden()
            expect(delete_button(page,view)).to_be_focused()
            assert stored(page) == before, f'{path} changed data while cancelling deletion'
    print('View deletion passed: bilingual exact safe target name, five cancellation paths, default Cancel and return focus preserve every stored field',flush=True)


def confirmed_delete(page, url):
    prepare(page,url)
    target = save_named(page,'Selected view','project:selected-for-deletion')
    remaining = save_named(page,'Remaining view','project:preserved-after-deletion')
    before = stored(page)
    undo_state = page.locator('#undoBtn').get_attribute('title')
    open_delete(page,target)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_only_selected_removed(page,before,target)
    expect(apply_button(page,remaining)).to_be_focused()
    assert page.locator('#undoBtn').get_attribute('title') == undo_state, 'View deletion replaced the existing task Undo action'
    last_before = stored(page)
    open_delete(page,remaining)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_only_selected_removed(page,last_before,remaining)
    expect(page.locator('#saveSmartViewBtn')).to_be_focused()
    page.reload()
    wait_for_app_ready(page)
    assert config(stored(page))['savedViews'] == []
    print('View deletion passed: explicit confirmation removes exactly one view, preserves tasks/metadata and focuses the next view or Save view',flush=True)


def deferred_search_focus(page, url):
    page.clock.install()
    prepare(page,url)
    view = save_named(page,'Focus survives a pending search','project:before-focus-rebuild')
    page.clock.run_for(1000)
    before = stored(page)
    # Pause after setup, then queue the real input handler's 300 ms debounce.
    # Verified pointer coordinates avoid animation-frame stability polling while
    # the clock is paused; hit-testing still rejects covered or disabled controls.
    page.clock.pause_at(page.evaluate('Date.now()') / 1000 + 1)
    try:
        page.locator('#searchInput').fill('project:after-focus-rebuild')
        button = delete_button(page,view)
        expect(button).to_be_visible()
        old_button = button.element_handle()
        assert old_button is not None
        click_paused_clock_control(page,button)
        expect(page.locator('#savedViewDeleteName')).to_have_text(view['name'])
        expect(page.locator('#cancelBtn')).to_be_focused()
        assert old_button.evaluate('node => node.isConnected'), 'The pending-search fixture already rebuilt the view before opening its confirmation'
        page.clock.run_for(350)
        assert not old_button.evaluate('node => node.isConnected'), 'The real deferred search did not rebuild the original view control'
        expect(page.locator('#savedViewDeleteConfirm')).to_be_visible()
        expect(page.locator('#cancelBtn')).to_be_focused()
        click_paused_clock_control(page,page.locator('#cancelBtn'))
        expect(page.locator('#taskModal')).to_be_hidden()
        expect(delete_button(page,view)).to_be_focused()
        assert stored(page) == before, 'A deferred search or cancelled confirmation changed stored data'
    finally:
        page.clock.resume()
    print('View deletion passed: a real deferred-search rebuild during confirmation returns Cancel focus to the new matching delete control',flush=True)


def duplicate_names(page, url):
    prepare(page,url)
    target = save_named(page,'Repeated view name','project:duplicate-label-first')
    remaining = save_named(page,'Repeated view name','project:duplicate-label-second')
    assert target['id'] != remaining['id']
    before = stored(page)
    open_delete(page,target)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after = assert_only_selected_removed(page,before,target)
    assert config(after)['savedViews'] == [remaining], 'A duplicate label caused deletion of the wrong view'
    expect(apply_button(page,remaining)).to_be_focused()
    print('View deletion passed: identical labels still delete only the selected stable ID',flush=True)


def concurrent_views(page, url):
    prepare(page,url)
    target = save_named(page,'Reviewed target','project:concurrent-target')
    local_other = save_named(page,'Local unrelated','project:local-unrelated')
    other = page.context.new_page()
    try:
        other.goto(url)
        wait_for_app_ready(other)
        open_delete(page,target)
        remote = save_named(other,'Created after delete review','project:remote-after-review')
        latest = stored(other)
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        after = assert_only_selected_removed(page,latest,target)
        assert {view['id'] for view in config(after)['savedViews']} == {local_other['id'],remote['id']}
        # The stale window still displays the target. Confirming that old chip is
        # idempotent and must not resurrect it or drop a newer view.
        open_delete(other,target)
        other.locator('#submitBtn').click()
        expect(other.locator('#taskModal')).to_be_hidden()
        assert stored(other) == after
    finally:
        other.close()
    print('View deletion passed: atomic deletion preserves newer unrelated views and stale repeat confirmation is idempotent',flush=True)


def aborted_delete(page, url):
    prepare(page,url)
    target = save_named(page,'Abort-protected view','project:aborted-view-delete')
    before = stored(page)
    open_delete(page,target)
    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(value,...args) {
            const request = original.call(this,value,...args);
            if (this.name === 'config' && value?.key === 'savedViews') {
                IDBObjectStore.prototype.put = original;
                window.viewDeleteAbortInjected = true;
                this.transaction.abort();
            }
            return request;
        };
    }""")
    page.locator('#submitBtn').click()
    expect(page.locator('#notification')).to_have_class(re.compile(r'\berror\b'))
    expect(page.locator('#savedViewDeleteConfirm')).to_be_visible()
    expect(page.locator('#submitBtn')).to_be_enabled()
    assert page.evaluate('window.viewDeleteAbortInjected === true')
    assert stored(page) == before
    page.locator('#cancelBtn').click()
    expect(delete_button(page,target)).to_be_focused()
    print('View deletion passed: aborted configuration write preserves the view and confirmation retry/cancel controls',flush=True)


def late_completion(page, url):
    prepare(page,url)
    target = save_named(page,'Delayed committed deletion','project:late-delete')
    before = stored(page)
    open_delete(page,target)
    page.evaluate("""() => {
        const original = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(value,...args) {
            const request = original.call(this,value,...args);
            if (this.name === 'config' && value?.key === 'savedViews') {
                IDBObjectStore.prototype.put = original;
                const tx = this.transaction;
                const complete = tx.oncomplete;
                tx.oncomplete = null;
                tx.addEventListener('complete',event => {
                    window.finishViewDeletion = () => complete.call(tx,event);
                },{once:true});
            }
            return request;
        };
    }""")
    page.locator('#submitBtn').click()
    page.wait_for_function('typeof window.finishViewDeletion === "function"')
    page.locator('#cancelBtn').click()
    open_task_editor(page)
    page.locator('#taskName').fill('A later unsaved task draft')
    page.locator('#taskDesc').fill('Keep this exact newer form text')
    page.evaluate('window.finishViewDeletion()')
    page.evaluate('() => new Promise(requestAnimationFrame)')
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value('A later unsaved task draft')
    expect(page.locator('#taskDesc')).to_have_value('Keep this exact newer form text')
    expect(page.locator('#taskDesc')).to_be_focused()
    expect(page.locator('#submitBtn')).to_be_enabled()
    assert_only_selected_removed(page,before,target)
    print('View deletion passed: a committed old deletion callback cannot close, refocus or alter a newer task draft',flush=True)


CASES = {'cancel':cancellation,'confirm':confirmed_delete,'debounce':deferred_search_focus,'duplicates':duplicate_names,
         'concurrent':concurrent_views,'abort':aborted_delete,'session':late_completion}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=['chromium','firefox','webkit'],default='chromium')
    parser.add_argument('--case',choices=['all',*CASES],default='all')
    args = parser.parse_args()
    expect.set_options(timeout=15000)
    with local_server() as url,sync_playwright() as p:
        options = browser_launch_options() if args.browser == 'chromium' else {'headless':True}
        browser = getattr(p,args.browser).launch(**options)
        print(f'{args.browser}: saved-view deletion on {browser.version}',flush=True)
        try:
            cases = CASES.items() if args.case == 'all' else [(args.case,CASES[args.case])]
            for name,operation in cases:
                context = browser.new_context(accept_downloads=True,reduced_motion='reduce')
                errors = []
                try:
                    page = context.new_page()
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    operation(page,url)
                    assert not errors,(name,errors)
                finally:
                    context.close()
        finally:
            browser.close()
    print(f'{args.browser}: saved-view deletion checks passed',flush=True)


if __name__ == '__main__':
    main()
