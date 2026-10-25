# 2026-10-25 生产域名只读验收

执行：北京时间 2026-10-25T13:19:24.793227+08:00；UTC 2026-10-25T05:19:24.793106+00:00。

结论：**4.8.5 候选的生产部署匹配验收未通过**。线上实际仍为 app/cache **4.1**、资源 **4.25**；本地候选为 app/cache **4.8.5**、资源 **4.36**。未发布、未推送、未更改线上任务。

原 `tools/verify_deployment.py --url https://todo.muquew.com/` 在保留原断言、代理与默认 TLS 验证下退出 **1**：HTML 字节不匹配，报告线上版本 4.1。原 stdout/stderr、源码与验证输入起末指纹在 [report.json](report.json) 中。首次本地 sandbox socket denied 已[单独保留](../ea21469f-83cb-4edf-808c-974ab09001a7/report.json)，后续 reviewed escalation 的 HTTPS 观察才是线上结果。

## 实际 HTTP 与资源

原验证和完整资源诊断共 15 次 HTTPS GET，加 3 次 no-cache/nonce 补查，**18/18 HTTP 200**。14 条候选静态路径中 7 条相同、7 条不同（含根 HTML 与 index.html、两种语言的带/不带版本参数路径、sw.js）；同一语言的两个路径是两次请求，不是两个不同源文件。

| 请求路径 | 与候选相同 |
| --- | --- |
| `/` | 否 |
| `fav/android-chrome-192x192.png` | 是 |
| `fav/android-chrome-512x512.png` | 是 |
| `fav/apple-touch-icon.png` | 是 |
| `fav/favicon-16x16.png` | 是 |
| `fav/favicon-32x32.png` | 是 |
| `fav/favicon.ico` | 是 |
| `index.html` | 否 |
| `manifest.json` | 是 |
| `resources/en.json?v=4.36` | 否 |
| `resources/zh-CN.json?v=4.36` | 否 |
| `resources/en.json` | 否 |
| `resources/zh-CN.json` | 否 |
| `sw.js` | 否 |

## 安全响应头

CSP 与当前候选不同：线上 `script-src` 仍含 `unsafe-inline`，候选采用四个脚本 SHA-256 hash 且 `script-src-attr none`。其余登记的 Referrer-Policy、X-Content-Type-Options、X-Frame-Options、Permissions-Policy 均与候选相同。此差异属于当前旧部署，未据此修改本地候选。

## 缓存复查与边界

[附加 no-cache/nonce 原始观察](fresh-cache-observation.json) 的 HTML 与 worker 仍返回同一 4.1 字节；本次请求不经过浏览器配置或 Service Worker。不能由这些 GET 直接推断 Vercel 后台发布记录、部署分支或原因。

下一步应在经授权的对应候选部署完成后，重新执行原匹配校验；当前结果不能用作 4.8.5 已上线或生产验收通过的证据。浏览器中的本地候选验收由同轮其它报告单独记录。

[原始报告](report.json) · [摘要 JSON](summary.json) · [原 CLI stderr](original-cli.stderr.log) · [文件 SHA 清单](supplement-files.json)
