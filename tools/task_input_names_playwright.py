#!/usr/bin/env python3
"""Verify project/tag names across the editor, capture and structured search."""
import json
import argparse
import os
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright
from smoke_playwright import (
    add_task, browser_launch_options, ensure_capture, get_task_records,
    local_server, return_to_task_workspace, wait_for_app_ready,
)


def main(args):
    output = Path(tempfile.mkdtemp(prefix='task-tracer-input-names-'))
    errors = []
    with local_server() as url, sync_playwright() as p:
        launch = browser_launch_options(args.browser)
        browser = getattr(p, args.browser).launch(**launch)
        context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='zh-CN')
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(os.environ.get('TASK_TRACER_URL', url))
        wait_for_app_ready(page)
        add_task(page, '项目内阅读', description='', no_deadline=True,
                 project='个人 学习', tags=['深度 工作'])
        add_task(page, '短名称项目', description='', no_deadline=True, project='个人')
        add_task(page, '更长名称项目', description='', no_deadline=True, project='个人 学习 延伸')
        add_task(page, 'API review', description='', no_deadline=True, project='Phase 2: API')
        add_task(page, 'Uppercase project', description='', no_deadline=True, project='Alpha Beta')
        add_task(page, 'Lowercase project', description='', no_deadline=True, project='alpha beta')
        return_to_task_workspace(page)

        def capture(raw):
            before = {task['id'] for task in get_task_records(page)}
            ensure_capture(page)
            field = page.locator('#quickAddInput')
            field.fill(raw)
            field.press('Enter')
            expect(field).to_have_value('')
            created = [task for task in get_task_records(page) if task['id'] not in before]
            assert len(created) == 1, 'Capture must save exactly one task'
            return created[0]

        task = capture('明天 20:00 完成阅读 /个人 学习 #深度 工作')
        assert task['name'] == '完成阅读'
        assert task['project'] == '个人 学习' and task['tags'] == ['深度 工作']
        assert task['dueAt'] and task['dueLocalTime'] == '20:00'
        page.screenshot(path=str(output / '01-existing-multiword-name.png'), animations='disabled')

        search = page.locator('#searchInput')
        for query in ['project:个人 学习', 'p:"个人 学习"', '#深度 工作', 'tag:"深度 工作"']:
            search.fill(query)
            expect(page.locator('#taskList .task-item')).to_have_count(2)
            expect(page.locator('#taskList')).not_to_contain_text('更长名称项目')
            expect(page.locator('#taskList')).not_to_contain_text('短名称项目')
        page.screenshot(path=str(output / '02-exact-name-search.png'), animations='disabled')
        search.fill('')

        task = capture('新任务 /"新 项目" #"新 标签"')
        assert task['name'] == '新任务' and task['project'] == '新 项目'
        assert task['tags'] == ['新 标签']
        search.fill('project:"新 项目" tag:"新 标签"')
        expect(page.locator('#taskList .task-item')).to_have_count(1)
        expect(page.locator('#taskList')).to_contain_text('新任务')
        page.reload(wait_until='domcontentloaded')
        wait_for_app_ready(page)
        return_to_task_workspace(page)
        search = page.locator('#searchInput')
        search.fill('project:新 项目')
        expect(page.locator('#taskList .task-item')).to_have_count(1)
        search.fill('')

        raw = '保留原始文字 /"未闭合 项目'
        task = capture(raw)
        assert task['name'] == raw and task['project'] == '', 'Unclosed quotes must not consume title text'
        task = capture('常规记录 #工作 /默认')
        assert task['name'] == '常规记录' and task['project'] == '默认' and task['tags'] == ['工作']
        task = capture('Measure 6" pipe tomorrow /Home')
        assert task['name'] == 'Measure 6" pipe' and task['project'] == 'Home' and task['dueAt']
        task = capture('Inspect endpoint /Phase 2: API')
        assert task['name'] == 'Inspect endpoint' and task['project'] == 'Phase 2: API'
        search.fill('project:Phase 2: API')
        expect(page.locator('#taskList .task-item')).to_have_count(2)
        search.fill('')
        for project in ['Alpha Beta', 'alpha beta']:
            task = capture('Case-sensitive assignment /' + project)
            assert task['project'] == project, 'Existing exact-case project names must win over case-insensitive matches'
        assert not errors, errors
        (output / 'result.json').write_text(json.dumps({'page_errors': errors, 'passed': True,
            'browser': args.browser, 'browser_version': browser.version}, indent=2))
        print('Browser:', args.browser, browser.version)
        print('Input names passed: editor/capture/search agreement, longest known names, quoted new names, refresh and incomplete quotes.')
        print('Artifacts:', output)
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    main(parser.parse_args())
