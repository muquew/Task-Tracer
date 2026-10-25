"""Pure local socketpair control: a half-closed request must still receive its response."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import threading
import traceback
import uuid

ROOT=Path('/workspace/Task-Tracer')
OLD=ROOT/'docs/acceptance/2026-10-25/production-compatibility/transport-control/07a254e0-a019-4112-b897-f707ce245725/proxy_forwarder.py'
NEW=Path('/tmp/task_tracer_session_proxy_forwarder.py')

def check(path):
    spec=importlib.util.spec_from_file_location('relay_'+uuid.uuid4().hex,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    relay=module.SessionProxyForwarder()
    client,left=socket.socketpair();right,server=socket.socketpair()
    for item in (client,left,right,server):item.settimeout(3 if item in (client,server) else 0.2)
    request=b'half-closed-local-request\n';expected=bytes(range(256))*4096
    state={'module_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'expected_response_bytes':len(expected),'expected_response_sha256':hashlib.sha256(expected).hexdigest(),'errors':[]}
    def upstream():
        try:
            seen=b''
            while True:
                part=server.recv(65536)
                if not part:break
                seen+=part
            state['request_received_exactly']=seen==request
            server.sendall(expected);server.shutdown(socket.SHUT_WR)
        except BaseException as exc:state['errors'].append({'where':'controlled_upstream','error':repr(exc)})
    threads=[threading.Thread(target=relay._pump,args=(left,right,'bytes_to_upstream'),daemon=True),threading.Thread(target=relay._pump,args=(right,left,'bytes_to_client'),daemon=True),threading.Thread(target=upstream,daemon=True)]
    try:
        for thread in threads:thread.start()
        client.sendall(request);client.shutdown(socket.SHUT_WR)
        actual=b''
        while True:
            part=client.recv(65536)
            if not part:break
            actual+=part
        state['actual_response_bytes']=len(actual);state['actual_response_sha256']=hashlib.sha256(actual).hexdigest();state['full_response_received']=actual==expected
    except BaseException as exc:
        state['errors'].append({'where':'controlled_client','error':repr(exc)});state['full_response_received']=False
    finally:
        relay._stop.set()
        for item in (client,left,right,server):relay._close(item)
        for thread in threads:thread.join(timeout=3)
        state['all_fixture_threads_stopped']=all(not thread.is_alive() for thread in threads)
    return state

out=ROOT/'docs/acceptance/2026-10-25/production-compatibility/transport-control'/('halfclose-'+str(uuid.uuid4()));out.mkdir(parents=True)
(out/'runner.py').write_bytes(Path(__file__).read_bytes());(out/'old-forwarder.py').write_bytes(OLD.read_bytes());(out/'new-forwarder.py').write_bytes(NEW.read_bytes())
result={'scope':'Pure local socketpairs only, no network listeners, proxy environment mutation, external traffic or application source reads. The simulated peer receives a half-closed request before returning a 1 MiB response.','started_at':datetime.now(timezone.utc).isoformat(),'red_original':check(OLD),'green_repaired':check(NEW)}
assert result['red_original']['full_response_received'] is False,'Original truncation was not reproduced'
assert result['green_repaired']['full_response_received'] and result['green_repaired']['request_received_exactly'] and not result['green_repaired']['errors']
assert result['red_original']['all_fixture_threads_stopped'] and result['green_repaired']['all_fixture_threads_stopped']
result['status']='passed';result['completed']=True;result['finished_at']=datetime.now(timezone.utc).isoformat();(out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
print('HALFCLOSE_CONTROL='+str(out));print(json.dumps(result,indent=2))
