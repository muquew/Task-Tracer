from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import hashlib,json,re,sys
R=Path('/workspace/Task-Tracer');sys.path.insert(0,str(R/'tools'))
from validate_static import app_version
from check import source_identity,verification_identity
P=R/'docs/acceptance/2026-10-25/deployment/a8155697-f6ef-4eb5-908f-9cc6d23e6a57';d=json.loads((P/'report.json').read_text());fresh=json.loads((P/'fresh-cache-observation.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
for name,meta in json.loads((P/'files.json').read_text()).items():
 b=(P/name).read_bytes();assert len(b)==meta['bytes'] and sha(b)==meta['sha256'],name
html=(P/d['requests'][0]['body_file']).read_text();sw=(P/d['requests'][-1]['body_file']).read_text();localhtml=(R/'index.html').read_text()
normalize=lambda value:{part.split()[0]:set(part.split()[1:]) for part in value.split(';') if part.strip()}
header_results=[]
for group in json.loads((R/'vercel.json').read_text())['headers']:
 if group['source']!='/(.*)':continue
 for h in group['headers']:
  actual=d['requests'][0]['headers'].get(h['key'].lower());wanted=h['value'];same=actual is not None and (normalize(actual)==normalize(wanted) if h['key'].lower()=='content-security-policy' else actual.strip()==wanted.strip())
  header_results.append({'header':h['key'],'matches_candidate':same,'actual':actual,'candidate':wanted})
summary={'captured_at':datetime.now(timezone.utc).isoformat(),'captured_at_beijing':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'acceptance_status':'failed_candidate_not_deployed','online_app_version':app_version(html),'online_resource_version':re.findall(r"RESOURCE_VERSION:\s*['\"]([^'\"]+)",html),'online_cache_name':re.findall(r"CACHE_NAME\s*=\s*['\"]([^'\"]+)",sw),'candidate_app_version':app_version(localhtml),'candidate_resource_version':re.findall(r"RESOURCE_VERSION:\s*['\"]([^'\"]+)",localhtml),'original_cli_exit':d['original_cli']['exit_code'],'successful_http_requests':sum(r.get('status')==200 for r in d['requests'])+sum(r.get('status')==200 for r in fresh['requests']),'candidate_asset_paths':len(d['assets']),'matching_asset_paths':sum(a.get('bytes_equal') is True for a in d['assets']),'different_asset_paths':sum(a.get('bytes_equal') is False for a in d['assets']),'security_headers':header_results,'source_unchanged':source_identity()==d['source']==d['source_final'],'verification_unchanged':verification_identity()==d['verification']==d['verification_final'],'original_evidence_unchanged':True,'cache_observation':'No-cache request header plus distinct nonce query returned the same online 4.1 HTML and worker; no browser profile or Service Worker participated in these HTTPS GETs. Backend deployment history and root cause were not queried.','prior_sandbox_run':'../ea21469f-83cb-4edf-808c-974ab09001a7/report.json','limitations':['No deployment or push performed','No production task database or browser profile modified','Online 4.1 is not candidate 4.8.5 acceptance','First default sandbox denied socket access locally; recorded separately and not treated as an HTTP failure']}
assert summary['source_unchanged'] and summary['verification_unchanged'];assert summary['online_app_version']=='4.1' and summary['candidate_app_version']=='4.8.5';assert summary['original_cli_exit']==1
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
lines=['# 2026-10-25 生产域名只读验收','','执行：北京时间 '+summary['captured_at_beijing']+'；UTC '+summary['captured_at']+'。','','结论：**4.8.5 候选的生产部署匹配验收未通过**。线上实际仍为 app/cache **4.1**、资源 **4.25**；本地候选为 app/cache **4.8.5**、资源 **4.36**。未发布、未推送、未更改线上任务。','','原 `tools/verify_deployment.py --url https://todo.muquew.com/` 在保留原断言、代理与默认 TLS 验证下退出 **1**：HTML 字节不匹配，报告线上版本 4.1。原 stdout/stderr、源码与验证输入起末指纹在 [report.json](report.json) 中。首次本地 sandbox socket denied 已[单独保留](../ea21469f-83cb-4edf-808c-974ab09001a7/report.json)，后续 reviewed escalation 的 HTTPS 观察才是线上结果。','','## 实际 HTTP 与资源','','原验证和完整资源诊断共 15 次 HTTPS GET，加 3 次 no-cache/nonce 补查，**18/18 HTTP 200**。14 条候选静态路径中 7 条相同、7 条不同（含根 HTML 与 index.html、两种语言的带/不带版本参数路径、sw.js）；同一语言的两个路径是两次请求，不是两个不同源文件。','','| 请求路径 | 与候选相同 |','| --- | --- |']
for a in d['assets']:lines.append('| `'+a['request_path']+'` | '+('是' if a['bytes_equal'] else '否')+' |')
lines+=['','## 安全响应头','','CSP 与当前候选不同：线上 `script-src` 仍含 `unsafe-inline`，候选采用四个脚本 SHA-256 hash 且 `script-src-attr none`。其余登记的 Referrer-Policy、X-Content-Type-Options、X-Frame-Options、Permissions-Policy 均与候选相同。此差异属于当前旧部署，未据此修改本地候选。','','## 缓存复查与边界','','[附加 no-cache/nonce 原始观察](fresh-cache-observation.json) 的 HTML 与 worker 仍返回同一 4.1 字节；本次请求不经过浏览器配置或 Service Worker。不能由这些 GET 直接推断 Vercel 后台发布记录、部署分支或原因。','','下一步应在经授权的对应候选部署完成后，重新执行原匹配校验；当前结果不能用作 4.8.5 已上线或生产验收通过的证据。浏览器中的本地候选验收由同轮其它报告单独记录。','','[原始报告](report.json) · [摘要 JSON](summary.json) · [原 CLI stderr](original-cli.stderr.log) · [文件 SHA 清单](supplement-files.json)']
(P/'summary.md').write_text('\n'.join(lines)+'\n');(P/'summary-runner.py').write_bytes(Path(__file__).read_bytes())
manifest={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file() and p.name!='supplement-files.json'}
(P/'supplement-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='security_headers'},ensure_ascii=False));print('summary_path',P/'summary.md');print('files',len(manifest))
