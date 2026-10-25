from pathlib import Path
import hashlib,json
D=Path('/workspace/Task-Tracer/docs/acceptance/2026-10-26/final-4.15.1/final-matrix/remote-ci-webkit-diagnostic-cfe');sha=lambda b:hashlib.sha256(b).hexdigest()
p=D/'README.md';text=p.read_text();old='[公开run](https://github.com/muquew/Task-Tracer/actions/runs/40235171022)／[唯一WebKit job](https://github.com/muquew/Task-Tracer/actions/runs/40235171022/job/121295077000)已公开succeeded。';new='[公开run](https://github.com/muquew/Task-Tracer/actions/runs/40235171022)直接显示 `Status: Success`、总耗时22m 1s；workflow只定义[一个WebKit job](https://github.com/muquew/Task-Tracer/actions/runs/40235171022/job/121295077000)，因此监控将其映射为job succeeded。该映射不是直接取得job footer或native报告；本次匿名SSR没有匹配单独的job footer终态。';assert old in text;p.write_text(text.replace(old,new))
p=D/'public-terminal-witness.json';v=json.loads(p.read_text());assert v['public_job_footer_status'] is None and v['public_run_status']=='Success';v['direct_public_terminal_field']='single-job run Status: Success';v['monitor_job_succeeded_is_mapped_from_single_job_run_success']=True;p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
raw=Path(__file__).read_bytes();(D/'terminal-source-clarification-driver.py').write_bytes(raw)
p=D/'source-origins.json';o=json.loads(p.read_text());o['copied_files']['terminal-source-clarification-driver.py']={'source':str(Path(__file__)),'bytes':len(raw),'sha256':sha(raw),'byte_identical':True}
for name in ('README.md','public-terminal-witness.json'):o['derived_files'][name]['derived_from'].append(str(Path(__file__)));o['derived_files'][name]['terminal_source_clarification']='Direct field is run Status: Success; single-job success is inferred, not directly parsed from the job footer.'
p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
p=D/'manifest.json';m=json.loads(p.read_text());m['files']={f.relative_to(D).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in D.rglob('*') if f.is_file() and f!=p};p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
for name,meta in m['files'].items():assert sha((D/name).read_bytes())==meta['sha256']
for name,meta in o['copied_files'].items():assert (D/name).read_bytes()==Path(meta['source']).read_bytes()
print(json.dumps({'direct_public_field':'run Status: Success (22m 1s)','job_success_mapped_from_unique_job':True,'raw_original_metadata_unchanged':True,'files':len(m['files'])+1,'bytes':sum(f.stat().st_size for f in D.rglob('*') if f.is_file()),'manifest_sha256':sha(p.read_bytes()),'source_origins_sha256':sha((D/'source-origins.json').read_bytes())}))
