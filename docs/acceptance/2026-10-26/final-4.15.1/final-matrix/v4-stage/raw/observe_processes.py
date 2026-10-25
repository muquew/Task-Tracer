from pathlib import Path
from datetime import datetime,timezone
import json
OUT=Path(__file__).resolve().parent
rows={}
for path in Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  text=(path/'stat').read_text();end=text.rfind(')');parts=text[end+2:].split()
  rows[int(path.name)]={'pid':int(path.name),'comm':text[text.find('(')+1:end],'state':parts[0],'ppid':int(parts[1]),'process_group':int(parts[2]),'start_ticks':int(parts[19])}
 except (OSError,ValueError,IndexError):pass
engines={}
for engine in ('chromium','firefox','webkit'):
 w=OUT/engine/'worker.json'
 if not w.exists():continue
 worker=json.loads(w.read_text());owned={worker['pid']};prev=None
 while prev!=owned:
  prev=owned.copy();owned|={pid for pid,r in rows.items() if r['ppid'] in owned}
 engines[engine]={'worker':worker,'observed_processes':[rows[pid] for pid in sorted(owned) if pid in rows]}
with (OUT/'process-observations.jsonl').open('a') as f:f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'engines':engines})+'\n')
print({e:len(v['observed_processes']) for e,v in engines.items()})
