from pathlib import Path
import sys,json,hashlib,traceback,time
ROOT=Path('/workspace/Task-Tracer');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import accessibility_i18n_audit as audit
from smoke_playwright import local_server,browser_launch_options
from recovery_management_playwright import stored
from playwright.sync_api import sync_playwright
before={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['index.html','tools/accessibility_i18n_audit.py']}
original=audit.audit_page_state;observations=[]
def observed(page,source,label):
    original(page,source,label)
    if label.endswith(' calendar pagination'):
        day=page.evaluate("() => {const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}")
        all_entries=page.locator(f'[data-calendar-detail-date="{day}"]')
        button=all_entries.filter(visible=True)
        item={'label':label,'all_dom_entry_count':all_entries.count(),'entry_count':button.count(),'entry_visible':button.is_visible(),'entry_text':button.inner_text(),'entry_aria_label':button.get_attribute('aria-label'),'entry_class':button.get_attribute('class'),'database_before':stored(page)}
        observations.append(item)
        assert item['entry_count']==1 and item['entry_visible']
    elif label.endswith(' calendar day pagination'):
        assert page.locator('#calendarDayTasks .calendar-detail-task').count()==100
        observations[-1]['detail_opened_task_count']=100
        observations[-1]['database_unchanged']=observations[-1]['database_before']==stored(page)
        assert observations[-1]['database_unchanged']
        del observations[-1]['database_before']
        if ' light ' in label:page.screenshot(path=str(OUT/f"scaled-{page.viewport_size['width']}-detail.png"),animations='allow')
audit.audit_page_state=observed
started=time.monotonic();passed=False
try:
    with local_server() as url:
        with sync_playwright() as p:
            browser=p.chromium.launch(**browser_launch_options())
            try:
                for viewport in [{'width':1280,'height':720},{'width':390,'height':844}]:
                    audit.audit_scaled_surfaces(browser,url,audit.find_axe_source().read_text(),viewport)
                passed=True
            finally:browser.close()
except Exception:
    (OUT/'scaled-preflight-error.txt').write_text(traceback.format_exc())
after={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in before}
report={'passed':passed and before==after and len(observations)==4,'observations':observations,'duration_seconds':round(time.monotonic()-started,3),'before':before,'after':after,'unchanged':before==after,'browser_closed':True,'server_closed':True,'scope':'Original audit_scaled_surfaces bothviewport×lightdark; only captures the unique actually visible dayentry and original 100-row postclick assertion; all original axe/focus/data assertions retained'}
(OUT/'scaled-preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['passed'] else 1)
