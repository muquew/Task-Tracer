from pathlib import Path
from datetime import datetime,timezone
import hashlib,io,json,os,subprocess,sys,uuid,zipfile
R=Path('/workspace/Task-Tracer-craft');sys.path.insert(0,str(R/'tools'));from check import atomic_report,source_identity,verification_identity
from build_release import DISTRIBUTION_SOURCES,FIXED_TIME
sha=lambda raw:hashlib.sha256(raw).hexdigest();now=lambda:datetime.now(timezone.utc).isoformat()
T=Path('/tmp/task-tracer-4.12.0-release/fb36515b-e7d5-452b-aeb0-c39a2140b18b/report.json');tested=json.loads(T.read_text());source=source_identity();verification=verification_identity();assert source==tested['source']==tested['source_final'];assert verification==tested['verification']==tested['verification_final'];assert tested['status']=='passed' and tested['passed']
P=Path('/tmp/task-tracer-4.12.0-release')/('canonical-'+str(uuid.uuid4()));P.mkdir(parents=True,exist_ok=False)
d={'schema_version':1,'started_at':now(),'status':'running','passed':False,'tested_report':str(T),'tested_report_sha256':sha(T.read_bytes()),'source':source,'verification':verification,'expected_canonical_commit':'2f3e8ee716a6807f4e6dd35ce4597bbc61a6c39d','expected_canonical_dirty':False,'error':None};atomic_report(P/'comparison.json',d);(P/'runner.py').write_bytes(Path(__file__).read_bytes())
try:
 with (P/'build.stdout.log').open('x') as out,(P/'build.stderr.log').open('x') as err:r=subprocess.run([sys.executable,'tools/build_release.py'],cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'},stdout=out,stderr=err)
 d['native_build_exit_code']=r.returncode
 if r.returncode:raise RuntimeError('Native canonical build returned '+str(r.returncode))
 A=R/'dist/task-tracer-4.12.0.zip';raw=A.read_bytes();d['artifact']={'path':str(A),'bytes':len(raw),'sha256':sha(raw),'files':None};assert A.with_suffix('.zip.sha256').read_text()==f'{sha(raw)}  {A.name}\n'
 with zipfile.ZipFile(A) as z:
  names=z.namelist();assert len(names)==len(set(names))==len(DISTRIBUTION_SOURCES)+1 and set(names)==set(DISTRIBUTION_SOURCES)|{'integrity.json'};payload={name:z.read(name) for name in names};manifest=json.loads(payload['integrity.json']);d['artifact']['files']=len(names);d['canonical_manifest']={'version':manifest['version'],'commit':manifest['commit'],'working_tree_dirty':manifest['working_tree_dirty']};assert manifest['version']=='4.12.0';d['payload_comparison']=[]
  for target,source_name in DISTRIBUTION_SOURCES.items():
   data=(R/source_name).read_bytes();assert sha(data)==tested['source']['files'][source_name]
   if target in ('README.md','README_zh_cn.md'):data=data.replace(b'](../LICENSE)',b'](LICENSE)')
   matches=payload[target]==data and manifest['files'][target]==sha(data);d['payload_comparison'].append({'target':target,'source':source_name,'payload_sha256':sha(payload[target]),'frozen_source_sha256':tested['source']['files'][source_name],'matches_frozen_payload':matches});assert matches,target
 assert manifest['commit']==d['expected_canonical_commit'] and manifest['working_tree_dirty'] is False,d['canonical_manifest']
 def serialize(entries):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
   for name,data in sorted(entries.items()):
    info=zipfile.ZipInfo(name,FIXED_TIME);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,data)
  return buf.getvalue()
 assert serialize(payload)==raw,'Original build serializer did not reproduce current canonical archive'
 old_manifest=dict(manifest);old_manifest['commit']=tested['vcs_initial']['commit'];old_manifest['working_tree_dirty']=tested['vcs_initial']['working_tree_dirty'];old_payload=dict(payload);old_payload['integrity.json']=(json.dumps(old_manifest,indent=2,ensure_ascii=False)+'\n').encode();old_rebuilt=serialize(old_payload);old_sha=sha(old_rebuilt)
 d['metadata_comparison']={'test_era_identity':tested['vcs_initial'],'canonical_identity':d['canonical_manifest'],'only_changed_manifest_keys':['commit','working_tree_dirty'],'reconstructed_test_zip_sha256':old_sha,'original_native_test_zip_sha256':tested['reproducible_archive_sha256'],'matches_original_test_sha':old_sha==tested['reproducible_archive_sha256'],'method':'Reconstructed test-era ZIP from unchanged canonical payload using the original build serializer and recorded test-era Git metadata; original temporary ZIPs were not retained.'};assert d['metadata_comparison']['matches_original_test_sha']
 d['source_final']=source_identity();d['verification_final']=verification_identity();d['source_unchanged']=d['source_final']==source;d['verification_unchanged']=d['verification_final']==verification;assert d['source_unchanged'] and d['verification_unchanged'];d['status']='passed';d['passed']=True
except BaseException as error:d['status']='failed';d['error']=f'{type(error).__name__}: {error}'
finally:
 d['finished_at']=now();atomic_report(P/'comparison.json',d);files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file()};atomic_report(P/'files.json',files);print(json.dumps({'output':str(P),'status':d['status'],'passed':d['passed'],'artifact':d.get('artifact'),'manifest':d.get('canonical_manifest'),'metadata_comparison':d.get('metadata_comparison'),'error':d['error']},ensure_ascii=False),flush=True)
