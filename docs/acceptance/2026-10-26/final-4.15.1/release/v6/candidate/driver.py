from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,uuid,zipfile
R=Path('/workspace/Task-Tracer');sys.path.insert(0,str(R/'tools'))
from check import source_identity,verification_identity,atomic_report
from build_release import DISTRIBUTION_SOURCES,expected_distribution_files
assert len(sys.argv)==3,'Arguments: NATIVE_REPORT_JSON EXPECTED_HEAD'
report_path=Path(sys.argv[1]);head=sys.argv[2];rec=json.loads(report_path.read_text());assert rec['passed'] and rec['completed'] and rec['source_unchanged'] and rec['verification_unchanged']
s=source_identity();v=verification_identity();assert s==rec['source'] and v==rec['verification'] and rec['vcs_initial']['commit']==head
p=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/release-proof/v6/candidate-retained')/str(uuid.uuid4());p.mkdir(parents=True)
with (p/'build.stdout.log').open('x') as out,(p/'build.stderr.log').open('x') as err:result=subprocess.run([sys.executable,'tools/build_release.py','--output-dir',str(p/'archive')],cwd=R,stdout=out,stderr=err)
assert result.returncode==0
archive=p/'archive/task-tracer-4.15.1.zip';sha=hashlib.sha256(archive.read_bytes()).hexdigest();assert sha==rec['reproducible_archive_sha256']
with zipfile.ZipFile(archive) as z:
 assert len(z.namelist())==len(expected_distribution_files())==24 and set(z.namelist())==expected_distribution_files()
 m=json.loads(z.read('integrity.json'));assert m['version']=='4.15.1' and m['working_tree_dirty'] is True and m['commit']==head
 assert set(m['files'])==set(DISTRIBUTION_SOURCES)
 for target,source in DISTRIBUTION_SOURCES.items():
  data=(R/source).read_bytes()
  if target in ('README.md','README_zh_cn.md'):data=data.replace(b'](../LICENSE)',b'](LICENSE)')
  assert z.read(target)==data and hashlib.sha256(data).hexdigest()==m['files'][target]
 (p/'integrity.json').write_bytes(z.read('integrity.json'))
assert source_identity()==s and verification_identity()==v
summary={'captured_at':datetime.now(timezone.utc).isoformat(),'passed':True,'native_report':str(report_path),'native_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),'source':s,'verification':v,'index_sha256':s['files']['index.html'],'archive':{'path':str(archive),'sha256':sha,'bytes':archive.stat().st_size,'files':24,'identical_to_native_double_build':True},'manifest':m,'all_23_packaged_payloads_match_frozen_sources':True,'source_unchanged':True,'verification_unchanged':True,'scope':'candidate packaging/upgrade acceptance; dirty=true due untracked acceptance archive; not the clean canonical distribution','native_steps':rec['steps'],'limitations':rec['scope_limitations']}
atomic_report(p/'summary.json',summary);(p/'driver.py').write_bytes(Path(__file__).read_bytes())
atomic_report(p/'files.json',{f.relative_to(p).as_posix():{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in p.rglob('*') if f.is_file()})
print(json.dumps({'summary':str(p/'summary.json'),'native_report_sha256':summary['native_report_sha256'],'archive':summary['archive'],'manifest_commit':m['commit'],'manifest_dirty':m['working_tree_dirty'],'source_unchanged':True,'verification_unchanged':True}),flush=True)
