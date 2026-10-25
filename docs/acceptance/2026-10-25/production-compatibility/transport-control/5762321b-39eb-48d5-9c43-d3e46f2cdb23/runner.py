"""Validate only the disposable transport bridge, without reading application source."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import traceback
import uuid
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
from task_tracer_session_proxy_forwarder import SessionProxyForwarder

ROOT = Path('/workspace/Task-Tracer')

def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def main():
    ident = str(uuid.uuid4())
    out = ROOT / 'docs/acceptance/2026-10-25/production-compatibility/transport-control' / ident
    out.mkdir(parents=True, exist_ok=False)
    module_path = Path('/tmp/task_tracer_session_proxy_forwarder.py')
    (out/'proxy_forwarder.py').write_bytes(module_path.read_bytes())
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    report = {'schema_version':1,'run_id':ident,'status':'running','completed':False,'passed':False,
        'started_at':now(),'finished_at':None,'scope':'Transport control only: a cache-busted public manifest HTTPS request through an opaque local relay to the inherited platform proxy. No application HTML, code, task data, app source or service worker is read or exercised.',
        'module_sha256':hashlib.sha256(module_path.read_bytes()).hexdigest(),
        'tls_verification_enabled':True,'tls_decrypted_by_local_relay':False,
        'direct_destination_connection_by_local_relay':False,'headers_or_body_logged_by_relay':False,
        'browser_engine':'webkit','browser_version':None,'request_failures':[],'error':None,'traceback':None}
    def save():
        temporary=out/'report.json.tmp';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(out/'report.json')
    save();print('EVIDENCE_DIRECTORY='+str(out),flush=True)
    forwarder = SessionProxyForwarder()
    proxy_url = forwarder.start()
    report['forwarder_initial'] = forwarder.snapshot();save()
    raw = None
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch(headless=True,timeout=30000,
                proxy={'server':proxy_url,'bypass':'127.0.0.1,localhost'})
            report['browser_version']=browser.version
            context=browser.new_context(ignore_https_errors=False,locale='en-US',viewport={'width':1280,'height':800},
                extra_http_headers={'Cache-Control':'no-cache','Pragma':'no-cache'})
            try:
                page=context.new_page()
                page.on('requestfailed',lambda req:report['request_failures'].append({'url':req.url,'failure':req.failure}))
                online_url='https://todo.muquew.com/manifest.json?'+urlencode({'transport-control':ident,'phase':'online'})
                response=page.goto(online_url,wait_until='domcontentloaded')
                assert response is not None and response.status==200
                body=response.body();json.loads(body);(out/'online-manifest.json').write_bytes(body)
                report['online']={'url':response.url,'status':response.status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'from_service_worker':response.from_service_worker}
                assert not response.from_service_worker
                page.screenshot(path=out/'01-online-public-manifest.png',animations='disabled')
                raw=socket.create_connection((forwarder.host,forwarder.port),timeout=5)
                raw.sendall(b'CONNECT todo.muquew.com:443 HTTP/1.1\r\nHost: todo.muquew.com:443\r\n\r\n')
                header=b''
                while b'\r\n\r\n' not in header:
                    chunk=raw.recv(4096)
                    assert chunk,'Upstream tunnel ended before CONNECT status'
                    header+=chunk
                    assert len(header)<65536
                status=header.split(b'\r\n',1)[0].decode('ascii','replace')
                assert status.split()[1]=='200',status
                report['idle_tunnel']={'public_target':'todo.muquew.com:443','connect_status_line':status,'headers_retained':False}
                report['before_stop']=forwarder.snapshot()
                assert report['before_stop']['upstream_connections_opened']>=2
                assert report['before_stop']['active_sockets']>=2
                report['after_stop']=forwarder.stop()
                assert report['after_stop']['stopped'] and not report['after_stop']['listener_open']
                assert report['after_stop']['active_sockets']==report['after_stop']['active_worker_threads']==0
                assert not report['after_stop']['accept_thread_alive']
                try:
                    closed_data=raw.recv(1)
                    assert closed_data==b'', 'An established tunnel remained readable/open after stop'
                    report['idle_tunnel_after_stop']='EOF'
                except (ConnectionResetError,BrokenPipeError):
                    report['idle_tunnel_after_stop']='connection reset/closed'
                try:
                    unexpected=socket.create_connection((forwarder.host,forwarder.port),timeout=1)
                except OSError as exc:
                    report['new_connection_after_stop']={'failed':True,'error':repr(exc)}
                else:
                    unexpected.close();raise AssertionError('Listener accepted a new connection after stop')
                negative_url='https://todo.muquew.com/manifest.json?'+urlencode({'transport-control':ident,'phase':'after-stop-new-uncached-request'})
                try:
                    result=page.goto(negative_url,wait_until='domcontentloaded',timeout=10000)
                except Exception as exc:
                    report['browser_request_after_stop']={'failed':True,'url':negative_url,'error':repr(exc)}
                else:
                    raise AssertionError(f'Fresh uncached browser request succeeded after stop: {result.status if result else None}')
                try:
                    page.screenshot(path=out/'02-failed-new-request-old-document.png',timeout=5000)
                except Exception as capture_error:report['negative_screenshot_error']=repr(capture_error)
                report['after_negative']=forwarder.snapshot()
                for name in ('accepted_clients','upstream_connections_opened','bytes_to_upstream','bytes_to_client'):
                    assert report['after_negative'][name]==report['after_stop'][name],name
                report['status']='passed';report['passed']=True
            finally:
                context.close();browser.close()
    except BaseException as exc:
        report['status']='failed';report['passed']=False;report['error']=repr(exc);report['traceback']=traceback.format_exc();print(report['traceback'],flush=True)
    finally:
        if raw is not None:raw.close()
        try:report['final_transport_state']=forwarder.stop()
        except BaseException as stop_error:
            report['status']='failed';report['passed']=False;report['stop_error']=repr(stop_error)
        assert hashlib.sha256(module_path.read_bytes()).hexdigest()==report['module_sha256']
        report['completed']=True;report['finished_at']=now();save()
        inventory={}
        for path in sorted(out.rglob('*')):
            if path.is_file():
                data=path.read_bytes();inventory[str(path.relative_to(out))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        (out/'evidence-sha256.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print('TRANSPORT_CONTROL_STATUS='+report['status'],flush=True)
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
