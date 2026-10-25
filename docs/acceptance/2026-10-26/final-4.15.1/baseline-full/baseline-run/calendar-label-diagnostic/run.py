from pathlib import Path
import sys,json,hashlib,traceback
ROOT=Path('/workspace/task-tracer-final-baseline');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import accessibility_i18n_audit as audit
from smoke_playwright import local_server,browser_launch_options
from playwright.sync_api import sync_playwright
original=audit.run_axe
observations=[]
def observed(page,source,label):
    if 'calendar day pagination' in label:
        rows=page.locator('#calendarDayTasks .calendar-detail-task')
        observation={'label':label,'count':rows.count(),'source_sha256':hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest(),'rows':rows.evaluate_all("nodes => nodes.slice(0,10).map(e=>({taskId:e.dataset.calendarTaskId,innerText:e.innerText,textContent:e.textContent,ariaLabel:e.getAttribute('aria-label'),time:e.querySelector('.calendar-detail-task-time')?.innerText,name:e.querySelector('.calendar-detail-task-name')?.innerText,status:e.querySelector('.calendar-detail-task-status')?.innerText}))")}
        (OUT/'nodes.json').write_text(json.dumps(observation,ensure_ascii=False,indent=2)+'\n')
        page.screenshot(path=str(OUT/'calendar-day-label-mismatch.png'),animations='allow')
        (OUT/'aria-snapshot.txt').write_text(page.locator('#calendarDayTasks').aria_snapshot())
        observations.append(observation)
    return original(page,source,label)
audit.run_axe=observed
with local_server() as url:
    with sync_playwright() as p:
        browser=p.chromium.launch(**browser_launch_options())
        try:
            audit.audit_scaled_surfaces(browser,url,audit.find_axe_source().read_text(),{'width':1280,'height':720})
        except AssertionError:
            (OUT/'native-error.txt').write_text(traceback.format_exc())
            print('Observed original scaled audit failure; nodes/screenshots saved.')
        finally:
            browser.close()
(OUT/'session.json').write_text(json.dumps({'browser_closed':True,'server_closed':True,'calendar_day_observed':len(observations),'scope':'Exact original audit_scaled_surfaces; wrapper observes DOM and screenshot before original run_axe unchanged; original HTTP/motion.'},indent=2)+'\n')
