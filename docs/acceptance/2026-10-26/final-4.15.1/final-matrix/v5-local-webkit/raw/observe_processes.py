from pathlib import Path
from datetime import datetime,timezone
import json
O=Path(__file__).resolve().parent;worker=json.loads((O/'worker.json').read_text());rows={}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  raw=(p/'stat').read_text();end=raw.rfind(')');v=raw[end+2:].split();pid=int(p.name)
  rows[pid]={'pid':pid,'comm':raw[raw.find('(')+1:end],'state':v[0],'ppid':int(v[1]),'process_group':int(v[2]),'start_ticks':int(v[19])}
 except (OSError,ValueError,IndexError):pass
owned={worker['pid']};prior=None
while owned!=prior:
 prior=owned.copy();owned|={pid for pid,row in rows.items() if row['ppid'] in owned}
record={'at':datetime.now(timezone.utc).isoformat(),'worker':worker,'processes':[rows[pid] for pid in sorted(owned) if pid in rows]}
with (O/'process-observations.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
print('observed current owned processes',len(record['processes']))
