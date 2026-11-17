"""Shared workbench navigation fixtures and assertions; no test entry point."""
from __future__ import annotations
import json
from playwright.sync_api import expect
from tests.support.browser import get_task_records, open_task_editor, workbench_screen

def create_on_current_page(page, name, *, project=None, deadline=None):
    """A global Add must honor the current page; no helper changes its scope."""
    before = get_task_records(page)
    origin = workbench_screen(page)
    open_task_editor(page, preserve_context=True)
    expect(page.locator('#taskName')).to_be_focused()
    expect(page.locator('#noDeadline')).to_be_checked()
    if project is None:
        expect(page.locator('#taskProject')).to_have_value('')
    else:
        page.locator('#taskProject').fill(project)
    page.locator('#taskName').fill(name)
    if deadline:
        page.locator('#noDeadline').uncheck()
        page.locator('#dueDate').fill(deadline)
        page.locator('#dueTime').fill('10:00')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', origin)
    after = get_task_records(page)
    added = [task for task in after if task['id'] not in {old['id'] for old in before}]
    assert len(after) == len(before) + 1 and len(added) == 1, 'Creation saved zero or duplicate tasks'
    assert all(task in after for task in before), 'Creation changed a prior task'
    assert added[0]['name'] == name
    return added[0]

def assert_today_focus_reachable(page):
    focused = page.locator(':focus')
    expect(focused).to_be_visible()
    expect(focused).to_be_in_viewport(ratio=1)
    geometry = focused.evaluate("""node => {
        const rect = node.getBoundingClientRect();
        const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        const bounds = el => el ? {top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom,left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right} : null;
        return {reachable:Boolean(node.closest('#todayWorkspace') && hit && (node === hit || node.contains(hit))),
            focused:bounds(node),hit:hit ? {tag:hit.tagName,id:hit.id,className:hit.className} : null,
            topbar:bounds(document.querySelector('.workspace-topbar')),dock:bounds(document.querySelector('.workspace-mobile-dock')),
            notices:[...document.querySelectorAll('.notification.show')].filter(el=>el.getClientRects().length).map(bounds),scrollY};
    }""")
    assert geometry['reachable'], f'Today action left keyboard focus outside its page or beneath another control: {json.dumps(geometry)}'
