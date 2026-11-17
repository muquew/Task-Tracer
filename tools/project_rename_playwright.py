#!/usr/bin/env python3
"""Rename derived projects, preserve scopes and roll back tasks/views atomically."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from recovery_management_playwright import stored
from smoke_playwright import (
    add_task, browser_launch_options, get_task_records, local_server,
    navigate_workbench, select_filter, select_project, wait_for_app_ready,
)
from workbench_navigation_playwright import capture


SOURCE = 'Research Plan'
TARGET = 'Client "Next": Alpha'


def config(snapshot):
    return {item['key']: item['value'] for item in snapshot['config']}


def prepare(page, url):
    page.goto(url, wait_until='domcontentloaded')
    wait_for_app_ready(page)
    add_task(page, 'Rename fixture template', project=SOURCE, tags=['focus'],
             description='Keep description and dates', due_date='2034-04-09',
             due_time='09:00', repeat_type='daily', reminder_offset='-1',
             subtasks=['Keep checklist'])
    template = get_task_records(page)[0]
    tasks = []
    for identity, name, project, completed, archived in [
        (100, 'Project active task', SOURCE, False, False),
        (101, 'Project completed task', SOURCE, True, False),
        (102, 'Project archived task', SOURCE, True, True),
        (103, 'Existing project task', 'Existing', False, False),
        (104, 'Unassigned task', '', False, False),
    ]:
        tasks.append({**template, 'id': identity, 'name': name, 'project': project,
                      'completed': completed, 'completedAt': '2034-04-08T10:00:00.000Z' if completed else None,
                      'archived': archived, 'archivedAt': '2034-04-08T11:00:00.000Z' if archived else None,
                      'focusDate': '2034-04-08' if identity == 100 else None, 'order': identity * 1000})
    views = [
        {'id': 'scoped', 'name': 'Keep custom label', 'projectFilter': {'kind': 'project', 'name': SOURCE},
         'searchQuery': f'project:"{SOURCE}" tag:focus', 'filter': 'all', 'sort': 'smart', 'viewMode': 'list', 'sentinel': 'preserve raw field'},
        {'id': 'query', 'name': 'Project query', 'projectFilter': {'kind': 'all'},
         'searchQuery': f'p:{SOURCE}', 'filter': 'all', 'sort': 'smart', 'viewMode': 'stats'},
        {'id': 'literal', 'name': SOURCE, 'projectFilter': {'kind': 'all'},
         'searchQuery': f'"{SOURCE}" tag:focus', 'filter': 'all', 'sort': 'smart', 'viewMode': 'list'},
        {'id': 'other', 'name': 'Unrelated view', 'projectFilter': {'kind': 'project', 'name': 'Existing'},
         'searchQuery': '', 'filter': 'all', 'sort': 'smart', 'viewMode': 'list'},
    ]
    page.evaluate("""({tasks, views}) => new Promise((resolve,reject) => {
        const request=indexedDB.open('TaskTrackerDB',2);
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
            const db=request.result;
            const tx=db.transaction(['tasks','config'],'readwrite');
            const store=tx.objectStore('tasks'); store.clear(); tasks.forEach(task=>store.put(task));
            const settings=tx.objectStore('config');
            const revision=settings.get('taskRevision');
            revision.onsuccess=()=>settings.put({key:'taskRevision',value:(revision.result?.value||0)+1});
            settings.put({key:'savedViews',value:views});
            settings.put({key:'projectRenameSentinel',value:{keep:'unchanged'}});
            tx.oncomplete=()=>{db.close();resolve();}; tx.onabort=()=>reject(tx.error);
        };
    })""", {'tasks': tasks, 'views': views})
    page.reload()
    wait_for_app_ready(page)
    navigate_workbench(page, 'tasks')
    select_filter(page, 'all')
    select_project(page, SOURCE)
    page.locator('#searchInput').fill(f'project:"{SOURCE}" tag:focus')
    expect(page.locator('.task-item')).to_have_count(2)
    navigate_workbench(page, 'review')
    select_project(page, SOURCE)
    page.locator('#searchInput').fill(f'p:{SOURCE} tag:focus')
    expect(page.locator('.stats-review-total')).to_have_text('2 tasks completed')
    navigate_workbench(page, 'projects')
    page.locator('#workbench-project-search').fill('Research')
    return stored(page)


def rename_button(page, name):
    return page.get_by_role('button', name=f'Rename project: {name}', exact=True)


def open_rename(page, name=SOURCE):
    rename_button(page, name).click()
    expect(page.locator('#taskModal')).to_be_visible()
    field = page.locator('#projectRenameInput')
    expect(field).to_be_focused()
    expect(field).to_have_value(name)
    return field


def change_views(page, operation):
    page.evaluate("""operation => new Promise((resolve,reject)=>{
        const open=indexedDB.open('TaskTrackerDB',2);
        open.onerror=()=>reject(open.error);
        open.onsuccess=()=>{
            const db=open.result;const tx=db.transaction('config','readwrite');const store=tx.objectStore('config');
            const read=store.get('savedViews');read.onsuccess=()=>{
                const views=read.result.value;
                if(operation==='unrelated') views.push({id:'new-unrelated',name:'A newer unrelated view',
                    projectFilter:{kind:'project',name:'Existing'},searchQuery:'tag:focus',filter:'active',sort:'smart',viewMode:'list'});
                if(operation==='edit-unrelated') views.find(view=>view.id==='other').name='Updated independently';
                if(operation==='edit-related') views.find(view=>view.id==='scoped').name='Do not overwrite this remote edit';
                if(operation==='new-related') views.push({id:'new-related',name:'New renamed-project view',
                    projectFilter:{kind:'project',name:'Client "Next": Alpha'},searchQuery:'',filter:'all',sort:'smart',viewMode:'list'});
                store.put({key:'savedViews',value:views});
            };
            tx.oncomplete=()=>{db.close();resolve();};tx.onabort=()=>reject(tx.error);
        };
    })""", operation)


def assert_renamed(before, after):
    original = {task['id']: task for task in before['tasks']}
    assert len(after['tasks']) == len(original)
    for task in after['tasks']:
        expected = {**original[task['id']], 'project': TARGET} if original[task['id']]['project'] == SOURCE else original[task['id']]
        assert task == expected, f'Rename changed task fields other than project: {task["name"]}'
    old_config, new_config = config(before), config(after)
    assert new_config['taskRevision'] == old_config['taskRevision'] + 1
    for key, value in old_config.items():
        if key not in ('taskRevision', 'recoveryHistory', 'savedViews'):
            assert new_config[key] == value, f'Rename changed unrelated configuration: {key}'


def verify_flow(page, url, output):
    before = prepare(page, url)
    expect(page.locator('.project-card button button')).to_have_count(0)
    field = open_rename(page)
    capture(page, output, '01-rename-project-dialog')
    field.fill('   ')
    page.locator('#submitBtn').click()
    expect(field).to_have_attribute('aria-invalid', 'true')
    assert stored(page) == before
    field.fill('Existing')
    page.locator('#submitBtn').click()
    expect(page.locator('#projectRenameError')).to_have_text('A project with this name already exists.')
    assert stored(page) == before, 'Duplicate name merged projects or wrote a checkpoint'
    field.fill(SOURCE)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(rename_button(page, SOURCE)).to_be_focused()
    assert stored(page) == before, 'Unchanged project name performed a write'
    field = open_rename(page)
    field.fill(TARGET)
    page.locator('#cancelBtn').click()
    assert stored(page) == before
    change_views(page, 'unrelated')
    field = open_rename(page)
    field.fill(TARGET)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(rename_button(page, TARGET)).to_be_focused()
    after = stored(page)
    assert_renamed(before, after)
    views = {view['id']: view for view in config(after)['savedViews']}
    assert views['scoped']['projectFilter'] == {'kind': 'project', 'name': TARGET}
    assert views['scoped']['searchQuery'] == f'project:{json.dumps(TARGET, ensure_ascii=False)} tag:focus'.lower()
    assert views['scoped']['name'] == 'Keep custom label' and views['scoped']['sentinel'] == 'preserve raw field'
    assert views['literal'] == next(view for view in config(before)['savedViews'] if view['id'] == 'literal')
    assert 'new-unrelated' in views, 'Rename overwrote a newer configuration-only addition'
    capture(page, output, '02-renamed-project-card')
    navigate_workbench(page, 'tasks')
    expect(page.locator('#projectFilterBtn')).to_have_attribute('aria-label', re.compile('Client'))
    expect(page.locator('#searchInput')).to_have_value(f'project:{json.dumps(TARGET, ensure_ascii=False)} tag:focus')
    expect(page.locator('.task-item')).to_have_count(2)
    navigate_workbench(page, 'review')
    expect(page.locator('#searchInput')).to_have_value(f'p:{json.dumps(TARGET, ensure_ascii=False)} tag:focus')
    expect(page.locator('.stats-review-total')).to_have_text('2 tasks completed')
    navigate_workbench(page, 'projects')
    change_views(page, 'edit-unrelated')
    page.locator('#undoBtn').click()
    expect(rename_button(page, SOURCE)).to_be_focused()
    undone = stored(page)
    assert undone['tasks'] == before['tasks'], 'Undo failed to restore exact original task records'
    undone_views = {view['id']: view for view in config(undone)['savedViews']}
    for view in config(before)['savedViews']:
        expected = {**view, 'name': 'Updated independently'} if view['id'] == 'other' else view
        assert undone_views[view['id']] == expected, 'Undo did not restore project views or lost an unrelated edit'
    assert 'new-unrelated' in undone_views
    navigate_workbench(page, 'review')
    expect(page.locator('#searchInput')).to_have_value(f'p:{SOURCE} tag:focus')
    navigate_workbench(page, 'tasks')
    expect(page.locator('#searchInput')).to_have_value(f'project:"{SOURCE}" tag:focus')
    expect(page.locator('.task-item')).to_have_count(2)
    navigate_workbench(page, 'projects')
    capture(page, output, '03-project-rename-undone')
    assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')


def verify_failure_and_conflict(page, url, output, conflict):
    before = prepare(page, url)
    field = open_rename(page)
    field.fill(TARGET)
    page.evaluate("""target=>{
        const put=IDBObjectStore.prototype.put;let matched=0;
        IDBObjectStore.prototype.put=function(value,...rest){
            if(this.name==='tasks'&&value.project===target&&++matched===2){
                IDBObjectStore.prototype.put=put;
                throw new DOMException('Synthetic second project write failure','DataError');
            }
            return put.call(this,value,...rest);
        };
    }""", TARGET)
    page.locator('#submitBtn').click()
    expect(page.locator('#notificationText')).to_have_text('The project could not be renamed. Try again.')
    expect(field).to_have_value(TARGET)
    assert stored(page) == before, 'An aborted rename partially wrote tasks, views, revision or recovery history'
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_renamed(before, stored(page))
    change_views(page, conflict)
    reviewed = stored(page)
    page.locator('#undoBtn').click()
    expect(page.locator('#undoBtn')).to_be_disabled()
    assert stored(page) == reviewed, 'Conflicting Undo partly restored tasks or overwrote newer view data'
    capture(page, output, f'04-undo-{conflict}-refused')


def run(args):
    output = args.output / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    report = {'passed': False, 'browser_engine': args.browser, 'scope': 'Fresh synthetic localhost profiles', 'viewports': []}
    try:
        with local_server() as url, sync_playwright() as playwright:
            browser = getattr(playwright, args.browser).launch(**browser_launch_options(args.browser))
            report['browser_version'] = browser.version
            try:
                for width in args.widths:
                    folder = output / str(width)
                    folder.mkdir()
                    context = browser.new_context(viewport={'width': width, 'height': 960 if width > 779 else 844},
                                                  locale='en-US', timezone_id='UTC', reduced_motion='reduce')
                    page = context.new_page()
                    page.clock.install(time=datetime(2034, 4, 8, 12, tzinfo=timezone.utc))
                    errors = []
                    page.on('pageerror', lambda error, sink=errors: sink.append(str(error)))
                    entry = {'width': width, 'passed': False, 'page_errors': errors}
                    report['viewports'].append(entry)
                    try:
                        verify_flow(page, url, folder)
                        assert not errors, errors
                        entry['passed'] = True
                    except Exception:
                        page.screenshot(path=str(folder / 'failure.png'))
                        raise
                    finally:
                        context.close()
                    print(f'Project rename {args.browser} {width}px passed', flush=True)
                for conflict in ('edit-related', 'new-related'):
                    folder = output / conflict
                    folder.mkdir()
                    context = browser.new_context(viewport={'width': 1440, 'height': 960}, locale='en-US', timezone_id='UTC', reduced_motion='reduce')
                    page = context.new_page()
                    page.clock.install(time=datetime(2034, 4, 8, 12, tzinfo=timezone.utc))
                    try:
                        verify_failure_and_conflict(page, url, folder, conflict)
                    except Exception:
                        page.screenshot(path=str(folder / 'failure.png'))
                        raise
                    finally:
                        context.close()
                report['atomic_failure_and_conflict_passed'] = True
            finally:
                browser.close()
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': report['passed'], 'report': str(output / 'report.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--widths', type=int, nargs='+', default=[1440, 390])
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-project-rename'))
    run(parser.parse_args())
