#!/usr/bin/env python3
"""Refresh time-sensitive views after real timer/visibility events without task writes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re

from playwright.sync_api import expect, sync_playwright

from performance_playwright import read_workspace
from smoke_playwright import reveal_workspace_control
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, local_server,
    select_filter, select_view, task_locator, wait_for_app_ready, discard_task_draft,
)


DAY = '2026-10-23'
TOMORROW = '2026-10-24'


def after_minutes(page, minutes=2):
    page.clock.fast_forward(minutes * 60_000)


def verify_overdue(page, url):
    clear_app_data(page, url)
    add_task(page, 'Crossing deadline task', due_date=DAY, due_time='13:01', reminder_offset='-1')
    select_filter(page, 'overdue')
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    before = read_workspace(page)
    after_minutes(page)
    expect(task_locator(page, 'Crossing deadline task')).to_have_count(1)
    expect(page.locator('#count-overdue')).to_have_text('(1)')
    assert read_workspace(page) == before, 'Timer-based overdue refresh wrote task/config records'
    print('Time refresh passed: a due task enters an initially empty overdue view without user navigation or writes', flush=True)


def verify_midnight_search(page, url):
    clear_app_data(page, url)
    add_task(page, 'Yesterday due search result', due_date=DAY, due_time='23:59', reminder_offset='-1')
    add_task(page, 'New day due search result', due_date=TOMORROW, due_time='12:00', reminder_offset='-1')
    page.locator('#searchInput').fill('due:today')
    expect(page.locator('.task-item .task-name')).to_have_text(['Yesterday due search result'])
    before = read_workspace(page)
    after_minutes(page)
    expect(page.locator('.task-item .task-name')).to_have_text(['New day due search result'])
    assert read_workspace(page) == before, 'Midnight search refresh wrote task/config records'
    print('Time refresh passed: due:today follows the new local day without another search edit', flush=True)


def prepare_today_plan(page, url):
    clear_app_data(page, url)
    add_task(page, 'Yesterday planned task', no_deadline=True)
    add_task(page, 'New day planned task', no_deadline=True)
    page.evaluate("""({day,tomorrow}) => new Promise((resolve,reject) => {
        const request=indexedDB.open('TaskTrackerDB',2);
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
            const db=request.result; const tx=db.transaction('tasks','readwrite');
            const store=tx.objectStore('tasks'); const all=store.getAll();
            all.onsuccess=()=>all.result.forEach(task=>store.put({...task,
                focusDate:task.name.startsWith('Yesterday')?day:tomorrow}));
            tx.oncomplete=()=>{db.close();resolve();}; tx.onabort=()=>reject(tx.error);
        };
    })""", {'day':DAY,'tomorrow':TOMORROW})
    page.reload()
    wait_for_app_ready(page)
    reveal_workspace_control(page, '#focusModeToggleBtn').click()
    expect(page.locator('.task-item .task-name')).to_have_text(['Yesterday planned task'])


def verify_midnight_focus(page, url):
    prepare_today_plan(page, url)
    before = read_workspace(page)
    after_minutes(page)
    expect(page.locator('.task-item .task-name')).to_have_text(['New day planned task'])
    expect(page.locator('#focusModeSummary')).to_contain_text('0/1')
    assert read_workspace(page) == before, 'Midnight Today Plan refresh rewrote focus dates or config'
    print('Time refresh passed: Today Plan follows the local day while retaining original task focus dates', flush=True)


def verify_midnight_stats(page, url):
    clear_app_data(page, url)
    add_task(page, 'Completed before midnight', no_deadline=True)
    task_locator(page, 'Completed before midnight').locator('[data-action="toggle"]').click()
    expect(task_locator(page, 'Completed before midnight')).to_have_count(0)
    select_view(page, 'stats')
    today = page.locator('.stats-mini').nth(4).locator('strong')
    expect(today).to_have_text('1')
    before = read_workspace(page)
    after_minutes(page)
    expect(today).to_have_text('0')
    trend = page.locator('.stats-trend-bar').evaluate_all('bars=>bars.map(bar=>Number(bar.dataset.trendCount))')
    assert trend[-2:] == [1,0], f'Completion trend did not follow midnight: {trend}'
    assert read_workspace(page) == before, 'Midnight statistics refresh wrote tasks/config'
    print('Time refresh passed: completion-today and the last two trend dates follow midnight without writes', flush=True)


def prepare_relative_search(page, url):
    clear_app_data(page, url)
    add_task(page, 'Yesterday due search result', due_date=DAY, due_time='23:59', reminder_offset='-1')
    add_task(page, 'New day due search result', due_date=TOMORROW, due_time='12:00', reminder_offset='-1')
    page.locator('#searchInput').fill('due:today')
    expect(page.locator('.task-item .task-name')).to_have_text(['Yesterday due search result'])


def verify_draft_protection(page, url):
    prepare_relative_search(page, url)
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('  Do not disturb this draft  ')
    page.locator('#taskDesc').fill('Uncommitted text across midnight\n第二行')
    before = read_workspace(page)
    after_minutes(page)
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#taskName')).to_have_value('  Do not disturb this draft  ')
    expect(page.locator('#taskDesc')).to_have_value('Uncommitted text across midnight\n第二行')
    expect(page.locator('#taskDesc')).to_be_focused()
    expect(page.locator('.task-item .task-name')).to_have_text(['Yesterday due search result'])
    page.locator('#cancelBtn').click()
    discard_task_draft(page)
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(page.locator('.task-item .task-name')).to_have_text(['New day due search result'])
    assert read_workspace(page) == before, 'Deferred refresh or discarded live draft wrote records'
    print('Time refresh passed: midnight preserves modal fields/focus, then applies the deferred view update on close', flush=True)


def verify_command_protection(page, url):
    clear_app_data(page, url)
    add_task(page, 'Command protected deadline', due_date=DAY, due_time='13:01', reminder_offset='-1')
    select_filter(page, 'overdue')
    page.keyboard.press('Control+p')
    page.locator('#commandPaletteInput').fill('Calendar')
    before = read_workspace(page)
    after_minutes(page)
    expect(page.locator('#commandPaletteInput')).to_have_value('Calendar')
    expect(page.locator('#commandPaletteInput')).to_be_focused()
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#commandPalette')).to_be_hidden()
    expect(task_locator(page, 'Command protected deadline')).to_have_count(1)
    assert read_workspace(page) == before, 'Deferred command-palette refresh wrote records'
    print('Time refresh passed: an open command palette retains its input/focus and deferred results appear after Escape', flush=True)


def verify_selection_protection(page, url):
    prepare_relative_search(page, url)
    before = read_workspace(page)
    page.locator('.task-item .task-name').evaluate("""node => {
        const range=document.createRange();
        const status=node.closest('.task-item').querySelector('.status-text');
        range.setStart(node.firstChild,0); range.setEnd(status.firstChild,status.textContent.length);
        const selection=window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    }""")
    selected = page.evaluate('window.getSelection().toString()')
    assert 'Yesterday due search result' in selected
    after_minutes(page)
    assert page.evaluate('window.getSelection().toString()') == selected, 'Timer destroyed selected task text'
    expect(page.locator('.task-item .task-name')).to_have_text(['Yesterday due search result'])
    page.evaluate('window.getSelection().removeAllRanges()')
    expect(page.locator('.task-item .task-name')).to_have_text(['New day due search result'])
    assert read_workspace(page) == before
    print('Time refresh passed: active text selection survives midnight; clearing it releases the deferred update', flush=True)


def verify_batch_protection(page, url):
    prepare_today_plan(page, url)
    page.locator('#batchModeBtn').click()
    selected = task_locator(page, 'Yesterday planned task').locator('.task-select-checkbox')
    selected.check()
    expect(page.locator('#batchSelectionSummary')).to_contain_text('1')
    before = read_workspace(page)
    after_minutes(page)
    expect(selected).to_be_checked()
    expect(page.locator('#batchSelectionSummary')).to_contain_text('1')
    expect(page.locator('.task-item .task-name')).to_have_text(['Yesterday planned task'])
    # This task is intentionally removed immediately after the real click. An
    # uncheck() postcondition would wait on the disappearing old locator.
    selected.click()
    expect(page.locator('.task-item .task-name')).to_have_text(['New day planned task'])
    expect(page.locator('#batchSelectionSummary')).to_contain_text('0')
    assert read_workspace(page) == before, 'Time refresh changed task selection by writing data'
    print('Time refresh passed: batch selection remains intact across midnight until the user clears it', flush=True)


def verify_stability_and_paging(page, url):
    clear_app_data(page, url)
    add_task(page, 'Minute-stable task', due_date='2026-11-10', due_time='13:01',
             reminder_offset='-1', subtasks=['Keep the open subtask controls'])
    summary = page.locator('.subtask-summary-bar')
    summary.click()
    page.evaluate('window.timeStableSummary=document.querySelector(".subtask-summary-bar")')
    before = read_workspace(page)
    after_minutes(page)
    assert page.evaluate('window.timeStableSummary===document.querySelector(".subtask-summary-bar")'), 'Ordinary minute ticks rebuilt task content'
    expect(page.locator('.subtasks-wrapper')).to_have_class(re.compile('expanded'))
    assert read_workspace(page) == before

    # Seed a bounded workspace with one imminent deadline and retain the second page.
    page.evaluate("""() => new Promise((resolve,reject) => {
        const request=indexedDB.open('TaskTrackerDB',2);
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
            const db=request.result,tx=db.transaction('tasks','readwrite'),store=tx.objectStore('tasks');
            const all=store.getAll();
            all.onsuccess=()=>{
                const template=all.result[0];store.clear();
                const due=new Date(Date.now()+60000).toISOString();
                for(let i=0;i<251;i++)store.put({...template,id:100000+i,name:`Timed page task ${String(i).padStart(3,'0')}`,
                    subtasks:[],project:'',dueAt:i===0?due:null,dueDate:i===0?due:null,
                    dueLocalDate:i===0?due.slice(0,10):null,dueLocalTime:i===0?due.slice(11,16):null,
                    dueTimeZone:i===0?'UTC':null,order:i*1000});
            };
            tx.oncomplete=()=>{db.close();resolve();};tx.onabort=()=>reject(tx.error);
        };
    })""")
    page.reload()
    wait_for_app_ready(page)
    expect(page.locator('.task-item')).to_have_count(100)
    page.locator('#loadMoreTasksBtn').click()
    expect(page.locator('.task-item')).to_have_count(200)
    active = page.evaluate("({taskId:document.activeElement.closest('.task-item')?.dataset.taskId,action:document.activeElement.dataset.action})")
    assert active['taskId'] and active['action']
    before = read_workspace(page)
    after_minutes(page)
    expect(page.locator('.task-item')).to_have_count(200)
    expect(page.locator('#taskPaginationSummary')).to_contain_text('200')
    assert page.evaluate("({taskId:document.activeElement.closest('.task-item')?.dataset.taskId,action:document.activeElement.dataset.action})") == active, 'Boundary refresh moved logical keyboard focus'
    expect(page.locator('.task-item[data-task-id="100000"]')).to_have_class(re.compile('status-overdue'))
    assert read_workspace(page) == before
    print('Time refresh passed: ordinary minutes keep existing controls; a real deadline preserves loaded pages and logical focus', flush=True)


def verify_visibility_and_clock_change(page, url):
    clear_app_data(page, url)
    add_task(page, 'Hidden deadline task', due_date=DAY, due_time='13:01', reminder_offset='-1')
    select_filter(page, 'overdue')
    before = read_workspace(page)
    # Explicitly controlled visibility covers the handler; this is not an OS suspension test.
    page.evaluate("""() => {
        window.syntheticTimePageHidden=true;
        Object.defineProperty(document,'hidden',{configurable:true,get:()=>window.syntheticTimePageHidden});
    }""")
    page.clock.set_system_time(datetime(2026,10,23,13,2,0,tzinfo=timezone.utc))
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    page.evaluate("window.syntheticTimePageHidden=false; document.dispatchEvent(new Event('visibilitychange'))")
    expect(task_locator(page, 'Hidden deadline task')).to_have_count(1)
    page.clock.set_system_time(datetime(2026,10,23,13,0,0,tzinfo=timezone.utc))
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    assert read_workspace(page) == before
    print('Time refresh passed: controlled foreground restoration and a backward clock correction immediately refresh the view', flush=True)


def verify_status_boundary(page, url, status, due):
    clear_app_data(page, url)
    name=f'Entering {status} search'
    add_task(page, name, due_date=due, due_time='13:01', reminder_offset='-1')
    page.locator('#searchInput').fill(f'status:{status}')
    expect(page.locator('#taskList .empty-state')).to_be_visible()
    before = read_workspace(page)
    after_minutes(page)
    expect(task_locator(page, name)).to_have_count(1)
    assert read_workspace(page) == before
    print(f'Time refresh passed: crossing the {status} status threshold updates its initially empty search', flush=True)


def run(engine, case):
    expect.set_options(timeout=5000)
    cases={'overdue':verify_overdue,'search':verify_midnight_search,
           'focus':verify_midnight_focus,'stats':verify_midnight_stats,
           'draft':verify_draft_protection,'command':verify_command_protection,
           'selection':verify_selection_protection,'batch':verify_batch_protection,
           'stability':verify_stability_and_paging,'visibility':verify_visibility_and_clock_change,
           'urgent':lambda page,url:verify_status_boundary(page,url,'urgent','2026-10-26'),
           'warning':lambda page,url:verify_status_boundary(page,url,'warning','2026-10-30')}
    selected=cases if case=='all' else {case:cases[case]}
    with local_server() as url,sync_playwright() as p:
        options=browser_launch_options() if engine=='chromium' else {'headless':True}
        browser=getattr(p,engine).launch(**options)
        try:
            for name,check in selected.items():
                context=browser.new_context(timezone_id='UTC',locale='en-US',reduced_motion='reduce')
                page=context.new_page()
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                start=datetime(2026,10,23,13,0,0,tzinfo=timezone.utc) if name in ('overdue','command','stability','visibility','urgent','warning') else datetime(2026,10,23,23,59,30,tzinfo=timezone.utc)
                page.clock.install(time=start)
                try:
                    check(page,url)
                    assert not errors,errors
                except Exception:
                    print(json.dumps({'case':name,'clock':page.evaluate('new Date().toISOString()'),
                        'visible_tasks':page.locator('.task-item .task-name').all_text_contents(),
                        'pageerrors':errors},ensure_ascii=False),flush=True)
                    raise
                finally:
                    context.close()
            print(json.dumps({'browser_engine':engine,'browser':browser.version,'case':case,'passed':True}),flush=True)
        finally:
            browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=('chromium','firefox','webkit'),default='chromium')
    parser.add_argument('--case',choices=('all','overdue','search','focus','stats','draft','command',
                                         'selection','batch','stability','visibility','urgent','warning'),default='all')
    args=parser.parse_args()
    run(args.browser,args.case)
