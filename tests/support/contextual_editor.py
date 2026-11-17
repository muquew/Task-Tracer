"""Assertions for the contextual editor using the real app and persisted records."""
from __future__ import annotations

import re
import json

from playwright.sync_api import expect

from tests.support.browser import (
    add_task,
    get_task_records,
    navigate_workbench,
    reveal_task_field,
    task_locator,
)


FIRST = '梳理品牌改版的字体与间距规范'
SECOND = '完成设置页的键盘与读屏走查'


def task_title(page, name):
    return task_locator(page, name).locator('[data-task-open]')


def assert_editor_actions_reachable(page):
    geometry = page.evaluate("""() => {
        const hit = node => {
            const r = node.getBoundingClientRect();
            const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return {top:r.top, bottom:r.bottom, left:r.left, right:r.right,
                reachable:r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight
                    && r.left >= 0 && r.right <= innerWidth && Boolean(at && (at === node || node.contains(at)))};
        };
        return {save:hit(document.getElementById('submitBtn')),
            close:hit(document.getElementById('closeModalBtn')),
            overflow:document.documentElement.scrollWidth > innerWidth};
    }""")
    assert geometry['save']['reachable'] and geometry['close']['reachable'], geometry
    assert not geometry['overflow'], geometry
    return geometry


def fixture(page):
    add_task(page, FIRST, description='保留品牌项目、标签和全部子任务。', no_deadline=True,
             project='品牌改版', tags=['设计', '本周'],
             subtasks=[f'第{index}项：核对桌面和手机端的文字与间距' for index in range(1, 21)])
    add_task(page, SECOND, description='这条记录应始终保持不变。', no_deadline=True,
             project='产品发布', tags=['走查'])
    navigate_workbench(page, 'today')
    page.locator('#todayWorkspace .workbench-choose-tasks').click()
    for name in (FIRST, SECOND):
        task_locator(page, name).locator('[data-task-plan]').click()
    page.locator('#planningDoneBtn').click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'today')
    navigate_workbench(page, 'tasks')
    return get_task_records(page)


def clean_and_dirty_transitions(page, baseline):
    first, second = task_title(page, FIRST), task_title(page, SECOND)
    first.click()
    expect(page.locator('#taskModal')).to_have_attribute('data-layout', 'floating')
    expect(page.locator('#taskModal')).to_have_attribute('aria-modal', 'false')
    expect(page.locator('body')).to_have_attribute('data-contextual-editor', 'true')
    expect(task_locator(page, FIRST)).to_have_class(re.compile(r'(^|\s)is-editor-selected(\s|$)'))
    assert not page.locator('.container').evaluate('node => node.inert')
    second.click()
    expect(page.locator('#taskName')).to_have_value(SECOND)
    assert get_task_records(page) == baseline, 'Switching a clean editor wrote tasks'

    page.locator('#taskDesc').fill('尚未保存的评审草稿')
    first.click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    expect(page.locator('#draftKeepEditingBtn')).to_be_focused()
    page.locator('#draftKeepEditingBtn').click()
    expect(page.locator('#taskName')).to_have_value(SECOND)
    expect(page.locator('#taskDesc')).to_have_value('尚未保存的评审草稿')
    assert get_task_records(page) == baseline, 'Keeping a transition draft wrote tasks'
    first.click()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskName')).to_have_value(FIRST)
    assert get_task_records(page) == baseline, 'Discarding a transition draft wrote tasks'

    page.locator('#taskDesc').fill('导航前未保存的草稿')
    page.locator('#workspaceProjectsBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftKeepEditingBtn').click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'tasks')
    expect(page.locator('#taskDesc')).to_have_value('导航前未保存的草稿')
    page.locator('#workspaceProjectsBtn').click()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', 'projects')
    assert get_task_records(page) == baseline, 'Navigating away from a discarded draft wrote tasks'
    navigate_workbench(page, 'tasks')
    return 'clean switching and guarded task/navigation transitions preserve exact records'


def today_context(page, baseline):
    navigate_workbench(page, 'today')
    title = page.locator('#todayWorkspace .workbench-task-name').filter(has_text=re.compile(f'^{re.escape(FIRST)}$'))
    title.click()
    expect(page.locator('#taskModal')).to_have_attribute('data-layout', 'floating')
    expect(title.locator('xpath=ancestor::article')).to_have_class(re.compile(r'(^|\s)is-editor-selected(\s|$)'))
    expect(page.locator('#taskName')).to_have_value(FIRST)
    page.keyboard.press('Escape')
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(title).to_be_focused()
    assert get_task_records(page) == baseline, 'Opening and closing Today changed persisted tasks'
    navigate_workbench(page, 'tasks')
    return 'Today uses its real task anchor and returns focus without changing records'


def breakpoint_and_short_screen(page, baseline):
    task_title(page, FIRST).click()
    name = page.locator('#taskName')
    draft_name = '核对品牌改版的字体与间距，并与产品研发运营确认所有桌面和手机端场景中的组件命名、文字层级以及最终交付标准'
    name.fill(draft_name)
    pending = reveal_task_field(page, '#subtaskInput')
    pending.fill('最后一项尚未加入的子任务草稿')
    pending.evaluate("node => { window.contextualDraftNode = node; node.focus(); node.setSelectionRange(3, 8); }")
    for width, height in ((390, 480), (1440, 900), (320, 400), (1440, 900)):
        page.set_viewport_size({'width': width, 'height': height})
        layout = 'floating' if width > 1000 else 'sheet'
        expect(page.locator('#taskModal')).to_have_attribute('data-layout', layout)
        expect(page.locator('#taskModal')).to_have_attribute('aria-modal', 'false' if width > 1000 else 'true')
        expect(name).to_have_value(draft_name)
        expect(pending).to_have_value('最后一项尚未加入的子任务草稿')
        expect(page.locator('#subtaskListPreview .subtask-preview-item')).to_have_count(20)
        page.wait_for_function("""() => {
            const r = document.getElementById('subtaskInput').getBoundingClientRect();
            const form = document.getElementById('taskForm').getBoundingClientRect();
            const footer = document.querySelector('#taskForm .form-actions').getBoundingClientRect();
            return r.top >= Math.max(0, form.top) - 1
                && r.bottom <= Math.min(innerHeight, footer.top) + 1;
        }""")
        state = pending.evaluate("""node => {
            const r = node.getBoundingClientRect();
            const form = document.getElementById('taskForm').getBoundingClientRect();
            const footer = document.querySelector('#taskForm .form-actions').getBoundingClientRect();
            return {sameNode:window.contextualDraftNode === node, focused:document.activeElement === node,
                selection:[node.selectionStart, node.selectionEnd], top:r.top, bottom:r.bottom,
                clipTop:Math.max(0, form.top), clipBottom:Math.min(innerHeight, footer.top)};
        }""")
        assert state['sameNode'] and state['focused'] and state['selection'] == [3, 8], state
        assert state['top'] >= state['clipTop'] - 1 and state['bottom'] <= state['clipBottom'] + 1, state
        assert_editor_actions_reachable(page)
        assert get_task_records(page) == baseline, 'Resizing a live draft committed task data'

    page.set_viewport_size({'width': 390, 'height': 844})
    expect(page.locator('#taskModal')).to_have_attribute('data-layout', 'sheet')
    page.locator('#submitBtn').focus()
    page.keyboard.press('Tab')
    expect(page.locator('#closeModalBtn')).to_be_focused()
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    for width in (1440, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        expect(page.locator('#draftKeepEditingBtn')).to_be_focused()
        page.wait_for_function("""() => {
            const node = document.getElementById('draftKeepEditingBtn');
            const r = node.getBoundingClientRect();
            const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return Boolean(at && (at === node || node.contains(at)));
        }""")
    page.locator('#draftKeepEditingBtn').click()
    expect(name).to_have_value(draft_name)
    expect(pending).to_have_value('最后一项尚未加入的子任务草稿')
    page.locator('#cancelBtn').click()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_title(page, FIRST)).to_be_focused()
    assert get_task_records(page) == baseline
    page.set_viewport_size({'width': 1440, 'height': 900})
    return 'long draft, 20 subtasks, selection and discard decision survive short screens and breakpoints'


def oversized_description(page, baseline, evidence):
    task_title(page, FIRST).click()
    description = page.locator('#taskDesc')
    text = '\n'.join(f'第{index}行：检查长描述的光标与滚动位置' for index in range(1, 61))
    description.fill(text)
    description.press('Control+End')
    description.evaluate('node => { window.contextualDescriptionNode = node; }')
    evidence.mkdir(parents=True, exist_ok=True)
    for width, height in ((320, 400), (1440, 900)):
        page.set_viewport_size({'width': width, 'height': height})
        expect(description).to_be_focused()
        expect(description).to_have_value(text)
        visibility_check = """() => {
            const node = document.getElementById('taskDesc');
            const r = node.getBoundingClientRect();
            const form = document.getElementById('taskForm').getBoundingClientRect();
            const footer = document.querySelector('#taskForm .form-actions').getBoundingClientRect();
            const style = getComputedStyle(node);
            const lastLineBottom = r.bottom - parseFloat(style.paddingBottom) - parseFloat(style.borderBottomWidth);
            return node.clientHeight >= node.scrollHeight - 1
                && lastLineBottom > Math.max(0, form.top) + parseFloat(style.lineHeight)
                && lastLineBottom <= Math.min(innerHeight, footer.top) + 1;
        }"""
        try:
            page.wait_for_function(visibility_check, timeout=5000)
        finally:
            geometry = description.evaluate("""node => {
                const rect = n => { const r = n.getBoundingClientRect(); return {top:r.top,bottom:r.bottom,height:r.height}; };
                const style = getComputedStyle(node);
                return {textarea:rect(node), form:rect(document.getElementById('taskForm')),
                    footer:rect(document.querySelector('#taskForm .form-actions')),
                    clientHeight:node.clientHeight,scrollHeight:node.scrollHeight,scrollTop:node.scrollTop,
                    selection:[node.selectionStart,node.selectionEnd],length:node.value.length,
                    lineHeight:style.lineHeight,paddingBottom:style.paddingBottom,borderBottomWidth:style.borderBottomWidth};
            }""")
            (evidence / f'description-end-{width}.json').write_text(json.dumps(geometry, ensure_ascii=False), encoding='utf-8')
            page.screenshot(path=str(evidence / f'description-end-{width}.png'), animations='disabled')
        state = description.evaluate("""node => ({sameNode:window.contextualDescriptionNode === node,
            selection:[node.selectionStart, node.selectionEnd], clientHeight:node.clientHeight,
            scrollHeight:node.scrollHeight, scrollTop:node.scrollTop,
            bottomPadding:parseFloat(getComputedStyle(node).paddingBottom)})""")
        assert state['sameNode'] and state['selection'] == [len(text), len(text)], state
        assert state['clientHeight'] >= state['scrollHeight'] - 1, state
        assert_editor_actions_reachable(page)
        assert get_task_records(page) == baseline, 'Resizing a long description wrote task data'
    description.press('ArrowLeft')
    description.press('ArrowRight')
    page.keyboard.insert_text('末尾可继续编辑')
    expect(description).to_have_value(text + '末尾可继续编辑')
    assert description.evaluate('node => node.selectionStart === node.value.length && node.selectionEnd === node.value.length')
    assert get_task_records(page) == baseline, 'Typing in a long description committed task data'
    page.locator('#cancelBtn').click()
    page.locator('#draftDiscardBtn').click()
    expect(task_title(page, FIRST)).to_be_focused()
    assert get_task_records(page) == baseline, 'Discarding a long description changed the original records'
    return '60-line description remains uncapped, end caret reachable and editable across short and wide screens'


def title_input_and_save(page, baseline):
    task_title(page, FIRST).click()
    name = page.locator('#taskName')
    name.fill('核对中文输入与多行标题')
    name.press('Shift+Enter')
    name.press('End')
    page.keyboard.insert_text('保留第二行')
    assert '\n' in name.input_value(), 'Shift+Enter did not add a title line'
    expect(page.locator('#taskModal')).to_be_visible()
    assert get_task_records(page) == baseline
    name.dispatch_event('compositionstart', {'data': '中文'})
    name.press('Enter')
    name.press('Escape')
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#draftDiscardPrompt')).to_have_count(0)
    assert get_task_records(page) == baseline, 'An IME composition shortcut committed task data'
    name.dispatch_event('compositionend', {'data': '中文'})
    updated = '核对中文输入后保存的标题'
    name.fill(updated)
    name.press('Enter')
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(task_title(page, updated)).to_be_focused()
    records = get_task_records(page)
    old = next(record for record in baseline if record['name'] == FIRST)
    saved = next(record for record in records if record['id'] == old['id'])
    assert len(records) == len(baseline) and saved['name'] == updated
    assert all(record in records for record in baseline if record['id'] != old['id']), 'Saving changed an unrelated task'
    for key in ('description', 'project', 'tags', 'subtasks', 'dueDate', 'reminderOffset', 'repeatType'):
        assert saved.get(key) == old.get(key), f'Title save changed {key}'
    page.reload(wait_until='load')
    navigate_workbench(page, 'tasks')
    expect(task_title(page, updated)).to_be_visible()
    assert get_task_records(page) == records, 'Reload changed the saved records'
    return 'multiline and IME input remain drafts; committed Enter saves one target and returns focus'
