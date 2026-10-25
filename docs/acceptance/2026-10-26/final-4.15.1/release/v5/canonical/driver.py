"""Prepare a clean-commit package from the specified existing independent v5 clone."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,tempfile,time,uuid,zipfile
R=Path('/workspace/Task-Tracer');BASE=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/release-proof')
HEAD='6da3c7293f08c5d16ca73c7a63d8ff74e17358db';S='58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54';V='62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936'
assert len(sys.argv)==3,'Arguments: V5_CANDIDATE_ZIP V5_CANDIDATE_SHA256'
CAND=Path(sys.argv[1]);CSHA=sys.argv[2]
P=BASE/'canonical-prepared-v5'/str(uuid.uuid4());P.mkdir(parents=True)
sha=lambda data:hashlib.sha256(data).hexdigest();now=lambda:datetime.now(timezone.utc).isoformat()
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'}
record={'started_at':now(),'status':'running','passed':False,'completed':False,'scope':'clean-commit package prebuild only; not delivered, published, or a replacement for remaining whole-product/CI/production gates','steps':[],'error':None,'required_head':HEAD,'candidate_archive':{'path':str(CAND),'sha256':CSHA},'primary_dist_touched':False}
def save():
 temp=P/'.report.json.tmp';temp.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');os.replace(temp,P/'report.json')
def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo,text=True,env=env).strip()
def identity(repo):
 code="import sys,json;sys.path.insert(0,sys.argv[1]);from check import source_identity,verification_identity;print(json.dumps({'source':source_identity(),'verification':verification_identity()}))"
 return json.loads(subprocess.check_output([sys.executable,'-c',code,str(repo/'tools')],cwd=repo,text=True,env=env))
def validate_identity(i):
 assert i['source']['sha256']==S and i['verification']['sha256']==V and len(i['source']['files'])==23 and len(i['verification']['files'])==84
 return i
save();(P/'driver.py').write_bytes(Path(__file__).read_bytes());print(json.dumps({'output':str(P)}),flush=True)
try:
 assert git(R,'rev-parse','HEAD')==HEAD
 primary=validate_identity(identity(R));record['primary_initial']=primary;record['primary_vcs_initial']={'head':HEAD,'status':git(R,'status','--porcelain')};assert sha(CAND.read_bytes())==CSHA
 old=R/'dist/task-tracer-4.15.0.zip';old_sha=sha(old.read_bytes());assert old_sha=='02cc67c9ac2a454b9ca248c3a122f92060c674677914dfab567cd7de5f6fbca3'
 clone=Path('/tmp/task-tracer-final-stable-v5-20261026');record['temporary_clone']=str(clone);record['clone_reused_from_root']=True
 assert (clone/'.git').is_dir() and not (clone/'.git/commondir').exists() and not (clone/'.git/objects/info/alternates').exists()
 record['clone_independent_git_directory']=True;record['clone_no_shared_common_directory_or_alternates']=True;save()
 commands=[]
 for name,args,cwd in commands:
  started=now()
  with (P/(name+'.stdout.log')).open('x') as out,(P/(name+'.stderr.log')).open('x') as err:result=subprocess.run(args,cwd=cwd,env=env,stdout=out,stderr=err,timeout=300)
  record['steps'].append({'name':name,'args':args,'started_at':started,'finished_at':now(),'exit_code':result.returncode});save();assert result.returncode==0,name
 assert git(clone,'rev-parse','HEAD')==HEAD and not git(clone,'status','--porcelain')
 clone_before=validate_identity(identity(clone));assert clone_before==primary;record['clone_initial']=clone_before;record['clone_vcs_initial']={'head':git(clone,'rev-parse','HEAD'),'status':git(clone,'status','--porcelain')};save()
 archives=[]
 for name in ('one','two'):
  assert validate_identity(identity(clone))==primary and git(clone,'rev-parse','HEAD')==HEAD and not git(clone,'status','--porcelain')
  args=[sys.executable,'tools/build_release.py','--output-dir',str(P/name)];started=now()
  with (P/(name+'.stdout.log')).open('x') as out,(P/(name+'.stderr.log')).open('x') as err:result=subprocess.run(args,cwd=clone,env=env,stdout=out,stderr=err,timeout=300)
  record['steps'].append({'name':'build-'+name,'args':args,'cwd':str(clone),'started_at':started,'finished_at':now(),'exit_code':result.returncode});save();assert result.returncode==0,name
  archives.append(P/name/'task-tracer-4.15.1.zip')
  assert validate_identity(identity(clone))==primary and not git(clone,'status','--porcelain')
 assert archives[0].read_bytes()==archives[1].read_bytes()
 archive_sha=sha(archives[0].read_bytes());comparisons={}
 with zipfile.ZipFile(CAND) as candidate,zipfile.ZipFile(archives[0]) as clean:
  assert len(candidate.namelist())==len(clean.namelist())==24 and candidate.namelist()==clean.namelist()
  cm=json.loads(candidate.read('integrity.json'));fm=json.loads(clean.read('integrity.json'))
  assert cm['commit']==fm['commit']==HEAD and cm['working_tree_dirty'] is True and fm['working_tree_dirty'] is False
  difference={k:{'candidate':cm.get(k),'clean':fm.get(k)} for k in set(cm)|set(fm) if cm.get(k)!=fm.get(k)};assert difference=={'working_tree_dirty':{'candidate':True,'clean':False}}
  assert candidate.read('integrity.json').count(b'"working_tree_dirty": true')==1
  assert candidate.read('integrity.json').replace(b'"working_tree_dirty": true',b'"working_tree_dirty": false')==clean.read('integrity.json')
  for name in clean.namelist():
   ci=candidate.getinfo(name);fi=clean.getinfo(name)
   assert (ci.filename,ci.date_time,ci.external_attr,ci.compress_type)==(fi.filename,fi.date_time,fi.external_attr,fi.compress_type)
   if name=='integrity.json':continue
   a=candidate.read(name);b=clean.read(name);assert a==b and sha(b)==fm['files'][name]
   comparisons[name]={'identical_bytes':True,'bytes':len(b),'candidate_sha256':sha(a),'clean_sha256':sha(b)}
  assert len(comparisons)==23
  (P/'integrity.json').write_bytes(clean.read('integrity.json'));record['clean_manifest']=fm
 for archive in archives:assert archive.with_suffix('.zip.sha256').read_text()==archive_sha+'  '+archive.name+'\n'
 record['reverse_proof']={'all_23_payload_bytes_identical':True,'payload_comparisons':comparisons,'manifest_only_difference':difference,'manifest_bytes_match_after_only_true_to_false_replacement':True,'zip_entry_order_timestamp_permissions_compression_unchanged':True}
 record['archives']=[{'path':str(a),'bytes':a.stat().st_size,'sha256':sha(a.read_bytes()),'files':24} for a in archives];record['two_archives_byte_identical']=True
 record['clone_final']=validate_identity(identity(clone));record['primary_final']=validate_identity(identity(R));record['clone_vcs_final']={'head':git(clone,'rev-parse','HEAD'),'status':git(clone,'status','--porcelain')};record['primary_vcs_final']={'head':git(R,'rev-parse','HEAD'),'status':git(R,'status','--porcelain')}
 assert record['clone_final']==record['primary_final']==primary and record['clone_vcs_final']=={'head':HEAD,'status':''} and record['primary_vcs_final']['head']==HEAD
 assert sha(old.read_bytes())==old_sha;record['old_4_15_0_archive_unchanged']=True;record['status']='passed';record['passed']=True
except BaseException as error:
 import traceback
 record['status']='failed';record['error']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()};print(record['error']['traceback'],file=sys.stderr,flush=True)
finally:
 record['completed']=True;record['finished_at']=now();save();files={f.relative_to(P).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in P.rglob('*') if f.is_file()};(P/'files.json').write_text(json.dumps(files,indent=2)+'\n');print(json.dumps({'output':str(P),'status':record['status'],'passed':record['passed'],'archives':record.get('archives'),'clone':record.get('temporary_clone'),'error':record['error']}),flush=True)
if not record['passed']:sys.exit(1)
