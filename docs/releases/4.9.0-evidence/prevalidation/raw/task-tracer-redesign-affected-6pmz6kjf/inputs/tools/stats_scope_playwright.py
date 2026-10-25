#!/usr/bin/env python3
"""Verify ongoing-overdue statistics, scope filters, and read-only calculations."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from playwright.sync_api import expect, sync_playwright

from recovery_management_playwright import stored
from smoke_playwright import (
    add_task, browser_launch_options, clear_app_data, get_task_records,
    local_server, select_project, select_view, wait_for_app_ready,
)


def seed(page, records):
    page.evaluate("""records => new Promise((resolve,reject) => {
        const request=indexedDB.open('TaskTrackerDB',2);
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
            const db=request.result;
            const tx=db.transaction('tasks','readwrite');
            const store=tx.objectStore('tasks');
            store.clear();
            records.forEach(record=>store.put(record));
            tx.oncomplete=()=>{db.close();resolve();};
            tx.onabort=()=>reject(tx.error);
        };
    })""", records)
    page.reload()
    wait_for_app_ready(page)
    select_view(page,'stats')
    return stored(page)


def assert_stats(page, before, percent, overdue, denominator, completion=None):
    card=page.locator('.stat-card').nth(1)
    expect(card.locator('.stat-value')).to_have_text(percent)
    expect(card.locator('.stat-detail')).to_contain_text(f'{overdue}/{denominator}')
    if completion is not None:
        expect(page.locator('.stat-card').nth(0).locator('.stat-value')).to_have_text(completion)
    assert stored(page)==before,'Statistics or scope navigation changed persisted task/configuration data'


def run(browser_name):
    with local_server() as url,sync_playwright() as playwright:
        options=browser_launch_options() if browser_name=='chromium' else {'headless':True}
        browser=getattr(playwright,browser_name).launch(**options)
        context=browser.new_context(timezone_id='UTC',reduced_motion='reduce')
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            clear_app_data(page,url)
            add_task(page,'Statistics fixture seed',no_deadline=True)
            template=get_task_records(page)[0]
            now=datetime.now(timezone.utc)

            def task(identity,name,day_offset=None,completed=False,archived=False,project='Work',tag='focus'):
                date=(now+timedelta(days=day_offset or 0)).replace(hour=12,minute=0,second=0,microsecond=0)
                due=date.isoformat(timespec='milliseconds').replace('+00:00','Z') if day_offset is not None else None
                return {**template,'id':identity,'name':name,'description':'Synthetic statistics scope fixture',
                    'project':project,'tags':[tag],'order':identity*1000,
                    'completed':completed,'completedAt':now.isoformat().replace('+00:00','Z') if completed else None,
                    'archived':archived,'archivedAt':now.isoformat().replace('+00:00','Z') if archived else None,
                    'dueDate':due,'dueAt':due,'dueLocalDate':date.strftime('%Y-%m-%d') if due else None,
                    'dueLocalTime':'12:00' if due else None,'dueTimeZone':'UTC' if due else None,
                    'reminderOffset':-1,'reminderRepeat':-1}

            overdue=task(100,'Ongoing overdue',-2)
            completed=[task(101+i,f'Completed dated {i}',-2,completed=True) for i in range(9)]
            base=[overdue,*completed]
            before=seed(page,base)
            assert_stats(page,before,'100%',1,1,completion='90%')
            print(f'{browser_name} {browser.version}: one ongoing overdue + nine completed dated tasks gives 100%',flush=True)

            future=task(200,'Ongoing future',2)
            before=seed(page,[*base,future])
            assert_stats(page,before,'50%',1,2,completion='82%')
            archived=task(201,'Archived overdue',-2,archived=True)
            undated=task(202,'Ongoing no deadline')
            before=seed(page,[*base,future,archived,undated])
            assert_stats(page,before,'50%',1,2,completion='75%')
            expect(page.locator('.stats-mini[data-stats-filter="archived"] strong')).to_have_text('1')

            personal=task(203,'Personal overdue',-2,project='Personal',tag='personal')
            before=seed(page,[*base,future,archived,undated,personal])
            assert_stats(page,before,'67%',2,3,completion='69%')
            select_project(page,'Work')
            assert_stats(page,before,'50%',1,2,completion='75%')
            page.locator('#searchInput').fill('tag:focus')
            assert_stats(page,before,'50%',1,2)
            page.locator('#searchInput').fill('status:completed')
            assert_stats(page,before,'0%',0,0,completion='100%')
            page.locator('#searchInput').fill('project:Personal')
            assert_stats(page,before,'0%',0,0,completion='0%')
            select_project(page,'all')
            assert_stats(page,before,'100%',1,1,completion='0%')
            page.locator('#searchInput').fill('status:no-deadline')
            assert_stats(page,before,'0%',0,0,completion='0%')

            page.locator('#searchInput').fill('')
            before=seed(page,[*completed,archived,undated])
            assert_stats(page,before,'0%',0,0,completion='90%')
            before=seed(page,[])
            expect(page.locator('#taskList .empty-state')).to_be_visible()
            expect(page.locator('.stat-card')).to_have_count(0)
            assert stored(page)==before,'Empty statistics view changed persisted data'
            assert not errors,errors
            print('Ongoing denominator, future/archived/undated/empty cases, project and search intersections, unchanged completion metrics and full IndexedDB read-only checks passed',flush=True)
        finally:
            context.close()
            browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=('chromium','firefox','webkit'),default='chromium')
    run(parser.parse_args().browser)
