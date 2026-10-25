#!/usr/bin/env python3
"""Keep calendar civil dates stable through skipped days and live device-zone changes."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json

from playwright.sync_api import expect, sync_playwright

from performance_playwright import read_workspace
from smoke_playwright import (
    add_task, browser_launch_options, calendar_month_title, clear_app_data,
    get_task_records, local_server, select_view, task_locator, wait_for_app_ready,
)


def seed_civil_tasks(page, url):
    clear_app_data(page, url)
    add_task(page, 'Calendar civil seed', no_deadline=True)
    page.evaluate("""() => new Promise((resolve,reject) => {
        const request=indexedDB.open('TaskTrackerDB',2);
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
            const db=request.result,tx=db.transaction('tasks','readwrite'),store=tx.objectStore('tasks');
            const all=store.getAll();
            all.onsuccess=()=>{
                const template=all.result[0];store.clear();
                for(const [id,name,key] of [[10001,'Apia skipped civil day','2011-12-30'],
                                           [10002,'Leap February calendar target','2024-02-29']]){
                    const instant=key+'T12:00:00.000Z';
                    store.put({...template,id,name,description:'Synthetic civil calendar task',
                        dueAt:instant,dueDate:instant,dueLocalDate:key,dueLocalTime:'12:00',dueTimeZone:'UTC',
                        reminderOffset:-1,reminderRepeat:-1,order:id*1000});
                }
            };
            tx.oncomplete=()=>{db.close();resolve();};tx.onabort=()=>reject(tx.error);
        };
    })""")
    page.reload()
    wait_for_app_ready(page)


def assert_grid(page, year, month):
    expect(page.locator('.calendar-title')).to_have_text(calendar_month_title(page, year, month-1))
    keys=page.locator('[data-calendar-add-date]').evaluate_all('nodes=>nodes.map(node=>node.dataset.calendarAddDate)')
    assert len(keys)==42 and len(set(keys))==42, f'Calendar duplicated or omitted a civil date: {keys}'
    first=date.fromisoformat(keys[0])
    assert keys==[(first+timedelta(days=i)).isoformat() for i in range(42)], 'Calendar dates are not 42 consecutive civil days'
    in_month=page.locator('.calendar-day:not(.outside-month) [data-calendar-add-date]').evaluate_all('nodes=>nodes.map(node=>node.dataset.calendarAddDate)')
    assert in_month and all(key.startswith(f'{year:04d}-{month:02d}-') for key in in_month), in_month
    labels=page.locator('[data-calendar-add-date]').evaluate_all('nodes=>nodes.map(node=>[node.dataset.calendarAddDate,node.textContent])')
    assert all(int(key[-2:])==int(label) for key,label in labels), 'Date labels differ from their civil keys'


def verify_static_civil_dates(page, url):
    seed_civil_tasks(page,url)
    before=read_workspace(page)
    select_view(page,'calendar')
    assert_grid(page,2011,12)
    skipped=page.locator('[data-calendar-add-date="2011-12-30"]')
    expect(skipped).to_have_count(1)
    expect(page.locator('.calendar-day').filter(has=skipped).locator('.calendar-task')).to_have_text('Apia skipped civil day')
    skipped.click()
    expect(page.locator('#dueDate')).to_have_value('2011-12-30')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('#searchInput').fill('Leap February calendar target')
    expect(page.locator('.calendar-task')).to_have_text('Leap February calendar target')
    assert_grid(page,2024,2)
    leap=page.locator('[data-calendar-add-date="2024-02-29"]')
    expect(leap).to_have_count(1)
    leap.click()
    expect(page.locator('#dueDate')).to_have_value('2024-02-29')
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    page.locator('#searchInput').fill('')
    expect(page.locator('.calendar-task')).to_have_text('Leap February calendar target')
    page.locator('[data-calendar-action="next"]').click()
    assert_grid(page,2024,3)
    page.locator('[data-calendar-action="prev"]').click()
    assert_grid(page,2024,2)
    assert read_workspace(page)==before, 'Civil-date calendar rendering/search/new-form cancellation wrote task/config data'
    print('Calendar timezone passed: skipped civil day appears once, leap/search/month navigation and add-form date keys remain exact without writes',flush=True)


def verify_skipped_day_add_policy(page,url):
    seed_civil_tasks(page,url)
    before={task['id']:task for task in get_task_records(page)}
    select_view(page,'calendar')
    page.locator('[data-calendar-add-date="2011-12-30"]').click()
    expect(page.locator('#dueDate')).to_have_value('2011-12-30')
    page.locator('#taskName').fill('Explicit Apia skipped-day add')
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    after={task['id']:task for task in get_task_records(page)}
    assert {key:value for key,value in after.items() if key in before}==before, 'Adding a calendar task changed an existing record'
    added=[task for key,task in after.items() if key not in before]
    assert len(added)==1 and added[0]['name']=='Explicit Apia skipped-day add', added
    assert (added[0]['dueLocalDate'],added[0]['dueLocalTime'],added[0]['dueTimeZone'])==('2011-12-31','23:59','Pacific/Apia'), added[0]
    assert added[0]['dueAt']=='2011-12-31T09:59:00.000Z', added[0]
    print('Calendar timezone passed: Apia skipped-day add uses the existing forward-gap policy (30→31), preserving existing records',flush=True)


def apply_zone(client,page,zone):
    client.send('Emulation.setTimezoneOverride',{'timezoneId':zone})
    assert page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone')==zone
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")


def verify_live_month(page,url,client,source,target,due,time,shift,year,month):
    client.send('Emulation.setTimezoneOverride',{'timezoneId':source})
    clear_app_data(page,url)
    name=f'Live zone calendar {source} to {target}'
    add_task(page,name,due_date=due,due_time=time,reminder_offset='-1')
    due_before=task_locator(page,name).locator('.task-date').inner_text()
    select_view(page,'calendar')
    if shift:page.locator('[data-calendar-action="next"]').click()
    assert_grid(page,year,month)
    before=read_workspace(page)
    apply_zone(client,page,target)
    assert_grid(page,year,month)
    page.locator('[data-calendar-action="next"]').click()
    next_month=month+1;next_year=year
    if next_month==13:next_month=1;next_year+=1
    assert_grid(page,next_year,next_month)
    page.locator('[data-calendar-action="prev"]').click()
    assert_grid(page,year,month)
    page.locator('[data-calendar-action="next-year"]').click()
    assert_grid(page,year+1,month)
    page.locator('[data-calendar-action="prev-year"]').click()
    assert_grid(page,year,month)
    page.locator('[data-calendar-action="today"]').click()
    today=page.evaluate("[new Date().getFullYear(),String(new Date().getMonth()+1).padStart(2,'0'),String(new Date().getDate()).padStart(2,'0')].join('-')")
    expect(page.locator('.calendar-day.today [data-calendar-add-date]')).to_have_attribute('data-calendar-add-date',today)
    assert_grid(page,int(today[:4]),int(today[5:7]))
    select_view(page,'list')
    expect(task_locator(page,name).locator('.task-date')).to_have_text(due_before)
    assert read_workspace(page)==before, 'Live device-zone change or calendar navigation modified tasks/config'
    print(f'Calendar timezone passed: live {source}→{target} retains civil month, next/year navigation, local Today and stored task-date display',flush=True)


def verify_live_today_plan(page,url,client):
    client.send('Emulation.setTimezoneOverride',{'timezoneId':'UTC'})
    clear_app_data(page,url)
    add_task(page,'UTC day planned task',no_deadline=True)
    add_task(page,'Changed zone day planned task',no_deadline=True)
    target=page.evaluate("new Date().getUTCHours()<12?'Etc/GMT+12':'Pacific/Kiritimati'")
    dates=page.evaluate("""zone=>({utc:new Intl.DateTimeFormat('sv-SE',{timeZone:'UTC'}).format(new Date()),
        target:new Intl.DateTimeFormat('sv-SE',{timeZone:zone}).format(new Date())})""",target)
    assert dates['utc']!=dates['target']
    page.evaluate("""dates=>new Promise((resolve,reject)=>{const q=indexedDB.open('TaskTrackerDB',2);q.onsuccess=()=>{
        const db=q.result,tx=db.transaction('tasks','readwrite'),s=tx.objectStore('tasks'),a=s.getAll();
        a.onsuccess=()=>a.result.forEach(t=>s.put({...t,focusDate:t.name.startsWith('UTC')?dates.utc:dates.target}));
        tx.oncomplete=()=>{db.close();resolve();};tx.onabort=()=>reject(tx.error);};q.onerror=()=>reject(q.error);})""",dates)
    page.reload();wait_for_app_ready(page)
    page.locator('#focusModeToggleBtn').click()
    expect(page.locator('.task-item .task-name')).to_have_text(['UTC day planned task'])
    before=read_workspace(page)
    apply_zone(client,page,target)
    expect(page.locator('.task-item .task-name')).to_have_text(['Changed zone day planned task'])
    assert read_workspace(page)==before,'Live timezone Today Plan refresh rewrote task focus dates/config'
    print('Calendar timezone passed: Today Plan follows a real device-local date change without changing stored focus dates',flush=True)


def run(engine,case):
    expect.set_options(timeout=10000)
    with local_server() as url,sync_playwright() as p:
        options=browser_launch_options() if engine=='chromium' else {'headless':True}
        browser=getattr(p,engine).launch(**options)
        try:
            if case in ('all','static','add'):
                context=browser.new_context(timezone_id='Pacific/Apia',locale='en-US',reduced_motion='reduce')
                page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                try:
                    if case in ('all','static'):verify_static_civil_dates(page,url)
                    if case in ('all','add'):verify_skipped_day_add_policy(page,url)
                    assert not errors,errors
                finally:context.close()
            if case in ('all','live') and engine=='chromium':
                for source,target,due,time,shift,year,month in [
                    ('UTC','America/Los_Angeles','2039-01-15','00:30',1,2039,2),
                    ('UTC','Pacific/Kiritimati','2039-01-31','23:30',0,2039,1),
                    ('Pacific/Kiritimati','UTC','2039-03-15','00:30',1,2039,4),
                ]:
                    context=browser.new_context(locale='en-US',reduced_motion='reduce')
                    page=context.new_page();client=context.new_cdp_session(page)
                    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                    try:
                        verify_live_month(page,url,client,source,target,due,time,shift,year,month)
                        assert not errors,errors
                    finally:context.close()
                context=browser.new_context(locale='en-US',reduced_motion='reduce')
                page=context.new_page();client=context.new_cdp_session(page)
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                try:
                    verify_live_today_plan(page,url,client)
                    assert not errors,errors
                finally:context.close()
            print(json.dumps({'browser_engine':engine,'browser':browser.version,'case':case,
                'live_zone_coverage':'Chromium CDP' if engine=='chromium' and case in ('all','live') else 'not run; static-zone coverage only',
                'passed':True}),flush=True)
        finally:browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=('chromium','firefox','webkit'),default='chromium')
    parser.add_argument('--case',choices=('all','static','add','live'),default='all')
    args=parser.parse_args()
    if args.case=='live' and args.browser!='chromium':parser.error('--case live requires Chromium CDP')
    run(args.browser,args.case)
