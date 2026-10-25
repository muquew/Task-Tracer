#!/usr/bin/env python3
"""Keep quick-add civil dates aligned with the complete task form and saved UI."""
from __future__ import annotations

from smoke_playwright import ensure_capture

import argparse
from datetime import datetime, timezone
import json

from playwright.sync_api import expect, sync_playwright

from performance_playwright import read_workspace
from smoke_playwright import click_task_action
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, local_server, task_locator,
)


DUE_FIELDS=('dueLocalDate','dueLocalTime','dueTimeZone','dueAt','dueDate')


def revision(snapshot):
    return next((entry['value'] for entry in snapshot['config'] if entry['key']=='taskRevision'),0)


def assert_task_ui(page, record):
    task=task_locator(page,record['name'])
    expect(task).to_have_count(1)
    if record['dueAt']:
        label=page.evaluate("""task=>new Intl.DateTimeFormat(document.documentElement.lang || 'en',{
            year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:task.dueTimeZone
        }).format(new Date(task.dueAt))""",record)
        expect(task.locator('.task-date')).to_contain_text(label)
    else:
        expect(task.locator('.task-date')).to_be_hidden()
    before=read_workspace(page)
    click_task_action(task, 'edit')
    if record['dueAt']:
        expect(page.locator('#dueDate')).to_have_value(record['dueLocalDate'])
        expect(page.locator('#dueTime')).to_have_value(record['dueLocalTime'])
    else:
        expect(page.locator('#noDeadline')).to_be_checked()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert read_workspace(page)==before,'Inspecting/cancelling a quick-added task changed database data'


def quick(page,raw,name,expected_date,expected_time,expected_zone='UTC',project='Inbox',tags=None):
    before=read_workspace(page)
    ensure_capture(page)
    page.locator('#quickAddInput').fill(raw)
    ensure_capture(page)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    after=read_workspace(page)
    originals={task['id']:task for task in before['tasks']}
    assert {task['id']:task for task in after['tasks'] if task['id'] in originals}==originals,'Quick add changed an unrelated task'
    added=[task for task in after['tasks'] if task['id'] not in originals]
    assert len(added)==1 and len(after['tasks'])==len(before['tasks'])+1,'One submission added zero or duplicate tasks'
    record=added[0]
    assert record['name']==name,(raw,record['name'])
    assert record['dueLocalDate']==expected_date,(raw,record['dueLocalDate'],expected_date)
    assert record['dueLocalTime']==expected_time,(raw,record['dueLocalTime'],expected_time)
    assert record['dueTimeZone']==(expected_zone if expected_date else None),(raw,record['dueTimeZone'])
    assert record['project']==project and record['tags']==(tags or []),(record['project'],record['tags'])
    assert revision(after)==revision(before)+1,'Quick add did not make exactly one task revision'
    untouched=lambda snap:[entry for entry in snap['config'] if entry['key'] not in ('taskRevision','recoveryHistory')]
    assert untouched(after)==untouched(before),'Quick add changed unrelated config or backup metadata'
    assert_task_ui(page,record)
    return record


def compare_form(page,quick_record,input_date,input_time,suffix):
    name='Full date comparison '+suffix
    add_task(page,name,due_date=input_date,due_time=input_time,reminder_offset='-1')
    record=next(task for task in read_workspace(page)['tasks'] if task['name']==name)
    assert {key:record[key] for key in DUE_FIELDS}=={key:quick_record[key] for key in DUE_FIELDS},'Quick add and the complete form resolved different due fields'
    assert_task_ui(page,record)


def yearless(page,url):
    clear_app_data(page,url)
    add_task(page,'Existing date-parser baseline',no_deadline=True)
    cases=[
        ('2024-03-01T12:00:00+00:00','2/29','2028-02-29'),
        ('2026-03-01T12:00:00+00:00','02-29','2028-02-29'),
        ('2097-03-01T12:00:00+00:00','2月29日','2104-02-29'),
        ('2099-03-01T12:00:00+00:00','2/29','2104-02-29'),
        ('2028-02-29T12:00:00+00:00','2月29','2028-02-29'),
        ('2026-12-31T12:00:00+00:00','1/1','2027-01-01'),
    ]
    for index,(now,token,expected) in enumerate(cases):
        page.clock.set_system_time(datetime.fromisoformat(now))
        name=f'Yearless civil case {index}'
        record=quick(page,f'{token} 09:00 {name} #dates /DateLab',name,expected,'09:00',project='DateLab',tags=['dates'])
        compare_form(page,record,expected,'09:00',f'yearless {index}')
    print('Quick-add dates passed: nearest valid month/day, leap centuries, Chinese/separator forms, same-day dates and ordinary year rollover match full forms',flush=True)


def explicit(page,url):
    clear_app_data(page,url)
    page.clock.set_system_time(datetime(2026,6,1,12,tzinfo=timezone.utc))
    add_task(page,'Existing explicit-date baseline',no_deadline=True)
    zone=page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone')
    if zone=='Pacific/Apia':
        record=quick(page,'2011-12-30 12:00 Skipped civil parser case','Skipped civil parser case','2011-12-31','12:00',zone)
        compare_form(page,record,'2011-12-30','12:00','Apia skipped-day')
        assert record['dueAt']=='2011-12-30T22:00:00.000Z'
    elif zone=='America/New_York':
        record=quick(page,'2026-03-08 02:30 DST parser case','DST parser case','2026-03-08','03:30',zone)
        compare_form(page,record,'2026-03-08','02:30','DST gap')
        assert record['dueAt']=='2026-03-08T07:30:00.000Z'
    else:
        record=quick(page,'2020/2/29 08:00 Explicit past parser case','Explicit past parser case','2020-02-29','08:00',zone)
        compare_form(page,record,'2020-02-29','08:00','explicit past')
    print(f'Quick-add dates passed: explicit civil dates in {zone} match the full form and its existing forward-gap policy',flush=True)


def invalid(page,url):
    clear_app_data(page,url)
    page.clock.set_system_time(datetime(2026,3,1,12,tzinfo=timezone.utc))
    quick(page,'2/30 Invalid calendar token','2/30 Invalid calendar token',None,None)
    quick(page,'2100-02-29 Invalid century token','2100-02-29 Invalid century token',None,None)
    quick(page,'2100-02-29 09:00 Invalid token with time','2100-02-29 Invalid token with time','2026-03-01','09:00')
    page.clock.set_system_time(datetime(9999,12,31,12,tzinfo=timezone.utc))
    quick(page,'1/1 Upper year boundary','1/1 Upper year boundary',None,None)
    print('Quick-add dates passed: impossible dates remain title text; independent time-only behavior and the supported upper year bound are preserved',flush=True)


def relative(page,url,now,before_tomorrow,after_today,after_tomorrow):
    clear_app_data(page,url)
    page.clock.set_system_time(datetime.fromisoformat(now))
    quick(page,'tomorrow 10:00 Before midnight parser case','Before midnight parser case',before_tomorrow,'10:00')
    ensure_capture(page)
    page.locator('#quickAddInput').fill('今天 10:00 Submitted after midnight parser case')
    page.clock.fast_forward(30000)
    before=read_workspace(page)
    ensure_capture(page)
    page.locator('#quickAddInput').press('Enter')
    expect(page.locator('#quickAddInput')).to_have_value('')
    after=read_workspace(page)
    prior={task['id']:task for task in before['tasks']}
    added=[task for task in after['tasks'] if task['id'] not in prior]
    assert len(added)==1 and added[0]['dueLocalDate']==after_today,added
    assert {task['id']:task for task in after['tasks'] if task['id'] in prior}==prior
    assert revision(after)==revision(before)+1
    assert_task_ui(page,added[0])
    quick(page,'明天 10:00 After midnight parser case','After midnight parser case',after_tomorrow,'10:00')
    print('Quick-add dates passed: relative words resolve on submission across leap/year midnight; saved cards and edit fields show the actual date',flush=True)


def past_relative(page, url):
    clear_app_data(page, url)
    cases = (
        ('2024-03-01T12:00:00+00:00', '昨天', '2024-02-29'),
        ('2026-01-01T12:00:00+00:00', 'YESTERDAY', '2025-12-31'),
        ('2026-03-01T12:00:00+00:00', '昨日', '2026-02-28'),
        ('2024-03-01T12:00:00+00:00', '前天', '2024-02-28'),
        ('2026-01-01T12:00:00+00:00', '前天', '2025-12-30'),
    )
    for index, (now, token, expected_date) in enumerate(cases):
        page.clock.set_system_time(datetime.fromisoformat(now))
        name = f'Past relative civil case {index}'
        record = quick(page, f'{token} 15:00 {name} #past /History', name,
                       expected_date, '15:00', project='History', tags=['past'])
        compare_form(page, record, expected_date, '15:00', f'past relative {index}')
    page.clock.set_system_time(datetime(2026, 3, 1, 12, tzinfo=timezone.utc))
    quick(page, '15:00 Standalone clock control', 'Standalone clock control',
          '2026-03-01', '15:00')
    quick(page, 'yesteryear 15:00 Ordinary word remains title',
          'yesteryear Ordinary word remains title', '2026-03-01', '15:00')
    print('Quick-add past-relative dates passed: Chinese yesterday/day-before-yesterday and English yesterday cross leap/month/year boundaries, match full forms, and preserve time-only/ordinary-word behavior', flush=True)


def weekdays(page, url):
    clear_app_data(page, url)
    page.clock.set_system_time(datetime(2026, 10, 25, 12, tzinfo=timezone.utc))
    for index, (token, date, clock) in enumerate((
        ('周三', '2026-10-28', '14:00'),
        ('星期三', '2026-10-28', '14:00'),
        ('礼拜三', '2026-10-28', '14:00'),
        ('本周三', '2026-10-21', '14:00'),
        ('这周三', '2026-10-21', '14:00'),
        ('下周日', '2026-11-01', '09:00'),
        ('周日', '2026-10-25', '09:00'),
    )):
        name = f'Weekday civil capture {index}'
        record = quick(page, f'{token} {clock} {name}', name, date, clock)
        compare_form(page, record, date, clock, f'weekday {index}')
    for now, token, date in (
        ('2026-11-30T12:00:00+00:00', '周五', '2026-12-04'),
        ('2026-12-31T12:00:00+00:00', '下周一', '2027-01-04'),
    ):
        page.clock.set_system_time(datetime.fromisoformat(now))
        name = 'Weekday boundary ' + date
        quick(page, f'{token} 14:00 {name}', name, date, '14:00')
    print('Quick-add weekdays passed: nearest day including today, explicit current/next Monday-based week, and month/year rollover match complete forms', flush=True)


def run(engine,selected):
    expect.set_options(timeout=10000)
    cases=[('past-relative','UTC',past_relative),('weekday','UTC',weekdays),('yearless','UTC',yearless),('explicit','UTC',explicit),
           ('apia','Pacific/Apia',explicit),('gap','America/New_York',explicit),('invalid','UTC',invalid),
           ('midnight','UTC',lambda page,url:relative(page,url,'2024-02-28T23:59:40+00:00','2024-02-29','2024-02-29','2024-03-01')),
           ('yearend','UTC',lambda page,url:relative(page,url,'2026-12-31T23:59:40+00:00','2027-01-01','2027-01-01','2027-01-02'))]
    with local_server() as url,sync_playwright() as p:
        options=browser_launch_options() if engine=='chromium' else {'headless':True}
        browser=getattr(p,engine).launch(**options)
        try:
            for name,zone,check in cases:
                if selected not in ('all',name):continue
                context=browser.new_context(timezone_id=zone,locale='en-US',reduced_motion='reduce')
                page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.clock.install(time=datetime(2026,3,1,12,tzinfo=timezone.utc))
                try:
                    check(page,url)
                    assert not errors,errors
                except Exception:
                    print(json.dumps({'case':name,'zone':zone,'clock':page.evaluate('new Date().toISOString()'),'pageerrors':errors},ensure_ascii=False),flush=True)
                    raise
                finally:context.close()
            print(json.dumps({'browser_engine':engine,'browser':browser.version,'case':selected,'passed':True}),flush=True)
        finally:browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=('chromium','firefox','webkit'),default='chromium')
    parser.add_argument('--case',choices=('all','past-relative','weekday','yearless','explicit','apia','gap','invalid','midnight','yearend'),default='all')
    args=parser.parse_args()
    run(args.browser,args.case)
