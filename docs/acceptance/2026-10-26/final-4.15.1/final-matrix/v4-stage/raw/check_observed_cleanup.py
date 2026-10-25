from pathlib import Path
from datetime import datetime,timezone
import json
OUT=Path(__file__).resolve().parent
seen={e:{} for e in ('chromium','firefox','webkit')}
for line in (OUT/'process-observations.jsonl').read_text().splitlines():
 item=json.loads(line)
 for engine in seen:
  for row in item['engines'].get(engine,{}).get('observed_processes',[]):seen[engine][(row['pid'],row['start_ticks'])]=row
checks={}
for engine,instances in seen.items():
 native=json.loads((OUT/engine/'native-report.json').read_text())
 assert native['status']!='running',engine
 active=[];zombies=[];gone=0
 for (pid,start),row in instances.items():
  try:
   text=(Path('/proc')/str(pid)/'stat').read_text();values=text[text.rfind(')')+2:].split()
   if int(values[19])!=start:gone+=1;continue
   present={'pid':pid,'start_ticks':start,'comm':row['comm'],'state':values[0],'ppid':int(values[1])}
   (zombies if values[0]=='Z' else active).append(present)
  except (OSError,ValueError,IndexError):gone+=1
 checks[engine]={'unique_observed_process_instances':len(instances),'gone_instances':gone,'active_instances':active,'exited_zombie_instances':zombies}
 assert not active,(engine,active)
report={'at':datetime.now(timezone.utc).isoformat(),'scope':'Only actual descendant process instances sampled from this run native matrix workers; PID+start_ticks prevents PID reuse false attribution. Sampling started after early programs, so this is not a complete process trace.','no_active_observed_instances':True,'container_reaping_note':'Z state means exited, not a running browser/server. Remaining exited zombie process records require their parent/supervisor reaping and cannot be killed; no system-wide or other-agent processes were signaled.','engines':checks}
(OUT/'observed-process-cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
print({e:{'observed':v['unique_observed_process_instances'],'active':len(v['active_instances']),'exited_zombies':len(v['exited_zombie_instances'])} for e,v in checks.items()})
