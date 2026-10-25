"""Archive only completed v5 release and scale evidence, never product payloads."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,zipfile
R=Path('/workspace/Task-Tracer');sys.path.insert(0,str(R/'tools'))
from check import source_identity,verification_identity
B=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/release-proof')
D=R/'docs/acceptance/2026-10-26/final-4.15.1/release/v5'
HEAD='6da3c7293f08c5d16ca73c7a63d8ff74e17358db';S='58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54';V='62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936'
roots={'native':B/'native/2a2229e0-1f4b-40f1-b72a-627199b7df75','candidate':B/'candidate-retained/019456e1-bcee-4647-953b-02da5c8a3806','canonical':B/'canonical-prepared-v5/fbe6f2cf-78cd-4a55-9608-24a66bb3aa9f','scale':B/'scale-10000-full/7fc2b28f-1ec8-4b31-aded-91b7328d2ee0'}
sha=lambda b:hashlib.sha256(b).hexdigest()
s0=source_identity();v0=verification_identity();assert s0['sha256']==S and v0['sha256']==V and subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==HEAD
assert not D.exists(),'Never overwrite an existing v5 archive';D.mkdir(parents=True)
origins={};derived={}
def copy(source,relative,index=None):
 assert source.is_file() and not source.is_symlink()
 data=source.read_bytes();digest=sha(data)
 if index is not None and source.name in index:
  item=index[source.name];assert item['sha256']==digest and item['bytes']==len(data),(source,'original frozen file index mismatch')
 dest=D/relative;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(data);assert dest.read_bytes()==source.read_bytes()
 origins[relative]={'source_path':str(source),'bytes':len(data),'sha256':digest,'byte_identical_to_original':True,'checked_against_original_run_file_index':bool(index is not None and source.name in index)}
def write(relative,value,from_sources):
 dest=D/relative;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();data=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(value,str) else value.encode();dest.write_bytes(data)
 derived[relative]={'derived_from':[str(x) for x in from_sources],'purpose':'Scope-preserving archive index or explanatory note; original native files remain byte-identical.'}
for group,p in roots.items():
 original_index=json.loads((p/'files.json').read_text())
 for f in sorted(p.iterdir()):
  if not f.is_file():continue
  relative=f'{group}/'+('original-files.json' if f.name=='files.json' else f.name)
  copy(f,relative,original_index)
copy(B/'v5-summary.json','v5-summary.json')
copy(Path(__file__),'archive-driver.py')
release=json.loads((roots['native']/'report.json').read_text());candidate=json.loads((roots['candidate']/'summary.json').read_text());canonical=json.loads((roots['canonical']/'report.json').read_text());scale=json.loads((roots['scale']/'result.json').read_text());scale_wrapper=json.loads((roots['scale']/'report.json').read_text())
assert all(x['passed'] for x in (release,candidate,canonical,scale,scale_wrapper))
assert release['source']==candidate['source']==scale_wrapper['source']==s0 and release['verification']==candidate['verification']==scale_wrapper['verification']==v0
assert canonical['clone_initial']==canonical['clone_final']==canonical['primary_initial']==canonical['primary_final']=={'source':s0,'verification':v0}
inputs=[]
for category,group in (('distribution_source',release['source']),('verification_input',release['verification'])):
 for name,digest in group['files'].items():
  original=roots['native']/'frozen-inputs'/name;data=original.read_bytes();assert sha(data)==digest
  inputs.append({'name':name,'category':category,'sha256':digest,'bytes':len(data),'original_snapshot_path':str(original),'copied_into_this_archive':False,'omission_reason':'Avoid duplicate 107 source files; exact immutable commit, native identity maps and source SHA are retained.'})
assert len(inputs)==107
write('input-index.json',{'app_commit':HEAD,'source_sha256':S,'verification_sha256':V,'count':107,'contents_copied':False,'inputs':inputs},[roots['native']/'frozen-inputs.json'])
for key,archives in (('candidate',[candidate['archive']]),('canonical',canonical['archives'])):
 entries=None
 for meta in archives:
  p=Path(meta['path']);data=p.read_bytes();assert sha(data)==meta['sha256'] and len(data)==meta['bytes']
  with zipfile.ZipFile(p) as z:
   assert len(z.namelist())==24
   listing=[{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'sha256':sha(z.read(i)),'timestamp':list(i.date_time),'permissions':i.external_attr,'compression':i.compress_type} for i in z.infolist()]
  if entries is None:entries=listing
  else:assert entries==listing
 write(f'{key}/archive-file-list.json',{'archives':[{**m,'copied_into_this_archive':False,'omission_reason':'ZIP indexed by verified SHA/size; keep distribution payloads outside this evidence archive.'} for m in archives],'file_count':24,'entries':entries},[roots[key]/('summary.json' if key=='candidate' else 'report.json')])
write('canonical/reverse-proof.json',{'derived_from_report_sha256':sha((roots['canonical']/'report.json').read_bytes()),**canonical['reverse_proof']},[roots['canonical']/'report.json'])
write('scale/unretained-backups.json',{'retained_actual_backup_files':False,'initial_real_json_backup':{'recorded_bytes':scale['export_file_bytes'],'original_temporary_download_path':None,'temporary_path_recorded_by_native_program':False,'raw_file_sha256':None,'raw_file_sha256_recorded':False,'retention_status':'Not retained. The native program reads the browser-managed temporary download; the original path is not recorded and browser/context cleanup removes those downloads.','verified_by_original_assertions':['payload checksum valid','all task fields identical to complete baseline','repeat references valid, including root ID zero']},'final_real_json_backup':{'retained':False,'bytes_recorded':False,'original_temporary_download_path':None,'raw_file_sha256':None,'verified_by_original_assertions':['payload checksum valid','all task fields identical to complete baseline after all operations']},'recorded_task_structure_fingerprint':{'value':scale['baseline_signature'],'kind':'native canonical task-structure fingerprint, not the raw downloaded JSON file SHA'},'retained_native_result':{'path':'result.json','bytes':(roots['scale']/'result.json').stat().st_size,'sha256':sha((roots['scale']/'result.json').read_bytes())}},[roots['scale']/'result.json',R/'tools/workspace_roundtrip_playwright.py',R/'tools/smoke_playwright.py'])
readme='''# v5 发行与规模验收归档

**发行／规模门已过；整体CI与生产验收尚未完成，clean canonical为预制包，未发布，也未宣称最终交付。** 本目录只归档本地已完成的限定范围。主代理负责余下总目标及发布；此处不修改其他阶段或根目录manifest。

绑定应用提交 `6da3c7293f08c5d16ca73c7a63d8ff74e17358db`，应用4.15.1。23项发行源码指纹 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`；84项验证输入指纹 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`。各阶段首尾107输入逐项相同，原始JSON和日志保持原字节。

## 已完成的本地范围

- [原生发行报告](native/report.json)：完整静态7项、原release程序的两次构建一致、解包任务持久及离线，以及实际4.15.0 ZIP到4.15.1、回退、再升级；每段核对页面／worker身份、任务／视图字段、CRUD和离线。
- [候选包记录](candidate/summary.json)：24文件、992,072字节，SHA `8f69cc98414e6401dae091edab474a003b1ed7792d65487b41fe0c5fec9f6a65`；manifest绑定6da且dirty=true，真实反映主仓未跟踪验收材料。
- [clean双构建报告](canonical/report.json)：指定独立临时clone首尾HEAD6da且Git干净；107输入与主仓一致。两包字节相同，均24文件、992,073字节，SHA `4babded212213f3904f5ae5bafb2dcc37983f9ca4782dadb05d9a892b66f0ca8`，manifest dirty=false。[反证](canonical/reverse-proof.json)确认23载荷逐字相同，integrity唯一差异为dirty的true→false，替换后字节亦相同。
- [10k原结果](scale/result.json)：一万任务×六子任务，完整 `--full-views` 原9组检查通过，包括真实导出／替换导入／安全快照、10000项全量选择、1000项范围的批量修改与删除／精确撤销／检查点恢复、列表／时间线／日历分页及末端搜索、只读数据库指纹和最终真实备份。总耗时120.306秒，stderr为空、无页面／完整性错误，原生进程组已关闭。

## 范围与未保留文件

原实际旧包为4.15.0，990,442字节／24文件，SHA `02cc67c9ac2a454b9ca248c3a122f92060c674677914dfab567cd7de5f6fbca3`，manifest提交93c990、dirty=false；[原核验](native/baseline-audit.json)与[实际升级日志](native/actual-4.15.0-upgrade.stdout.log)保留。没有重建、覆盖或复制该旧ZIP。

本目录不含任何ZIP或重复107源码。`candidate/`和`canonical/`的archive-file-list列出真实外部ZIP的路径、字节、SHA及24个文件的完整索引；`input-index.json`记录107输入字节／SHA和原快照路径，源码由不可变提交及原指纹定位。外部路径是捕获当时的位置，不保证在其他环境存在。

10k初次实际下载备份的原记录大小为17,383,726字节；**原大文件未归档，临时下载路径和原文件字节SHA未记录**。浏览器上下文关闭后其下载临时文件不再保留。[未保留说明](scale/unretained-backups.json)区分任务结构指纹、原结果文件SHA与备份文件SHA，不能将baseline_signature冒称原下载文件SHA。最终备份仅保留原程序的checksum／全字段一致断言通过记录，不编造其大小、路径或文件SHA。

实际规模浏览器为system Chromium154.0.8037.57，原程序采用reduced-motion；这是合成数据正确性运行，CPU负载未受控，不能称CI151等价、真实设备、受控性能benchmark或独立事务故障注入通过。故障注入应引用其他专门程序的原报告。原release／upgrade使用普通HTTP handler，无新增HTTP CSP头，未设置bypass_csp；构建校验源CSP哈希，运行时生产CSP属于单独验收范围。原程序、断言、45秒等预算均未放宽。

## 核验与复现

`manifest.json`只索引本目录实际存在的文件（不包含自身）；`source-origins.json`记录逐文件来源字节／SHA及派生说明。各组`original-files.json`是原捕获目录的索引，可能列出本目录明确未复制的ZIP／107快照，不能据此声称那些原大文件已归档。`v5-summary.json`及原JSON中的绝对路径均保持原身份，不重写为本目录。旧阶段失败和中断没有在此转为通过。

复现时使用独立clone的精确提交6da，先核对107输入指纹、Python依赖和实际浏览器版本。以下为原CLI（对应日志保留）：

```sh
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check.py --static-only --keep-going --report /tmp/repro-static.json
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/release_playwright.py
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/upgrade_playwright.py --baseline-archive /path/to/actual/task-tracer-4.15.0.zip
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/workspace_roundtrip_playwright.py --size 10000 --subtasks 6 --full-views --output /tmp/new-unique-result.json
```

实际旧包必须先匹配02cc原SHA，不以重建旧版代替。clean包复现应在精确提交且Git干净的独立clone，使用原 `tools/build_release.py --output-dir` 两个仓库外新目录，避免pycache／输出使工作树变脏，再比对24文件／4bab SHA。原执行driver已随各组保留，仅作为捕获环境中的复现记录，不自动发布。
'''
write('README.md',readme,[B/'v5-summary.json',roots['native']/'report.json',roots['canonical']/'report.json',roots['scale']/'result.json',roots['scale']/'report.json'])
assert source_identity()==s0 and verification_identity()==v0 and subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==HEAD
write('source-origins.json',{'recorded_at':datetime.now(timezone.utc).isoformat(),'copied_files':origins,'derived_files':derived,'scope':'Only files under this v5 archive were written; original evidence, other docs and all107 product/verification inputs remain unchanged.'},[Path(__file__)])
entries={p.relative_to(D).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in D.rglob('*') if p.is_file()}
manifest={'schema_version':1,'recorded_at':datetime.now(timezone.utc).isoformat(),'status':'passed_local_release_and_scale_only_not_final_delivery','app_commit':HEAD,'source_sha256':S,'verification_sha256':V,'all107_inputs_unchanged':True,'manifest_excludes_only_itself':True,'max_total_archive_bytes':3000000,'indexed_file_count':len(entries),'indexed_bytes_excluding_this_manifest':sum(x['bytes'] for x in entries.values()),'files':entries}
(D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
assert {p.relative_to(D).as_posix() for p in D.rglob('*') if p.is_file()}==set(entries)|{'manifest.json'}
for name,meta in entries.items():
 data=(D/name).read_bytes();assert len(data)==meta['bytes'] and sha(data)==meta['sha256']
for name,meta in origins.items():assert (D/name).read_bytes()==Path(meta['source_path']).read_bytes()
total=sum(p.stat().st_size for p in D.rglob('*') if p.is_file());assert total<3000000
assert not any(p.suffix=='.zip' for p in D.rglob('*')) and source_identity()==s0 and verification_identity()==v0
print(json.dumps({'archive':str(D),'files':len(entries)+1,'total_bytes':total,'manifest_sha256':sha((D/'manifest.json').read_bytes()),'source_origins_sha256':sha((D/'source-origins.json').read_bytes()),'all_copied_files_byte_verified':True,'all107_unchanged':True,'zip_files_copied':False,'actual_large_backup_copied':False,'published':False}),flush=True)
