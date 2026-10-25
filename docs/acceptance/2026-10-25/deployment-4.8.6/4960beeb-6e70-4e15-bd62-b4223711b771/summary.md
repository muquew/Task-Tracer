# 4.8.6 推送后生产部署验收

结论：**通过**。

首次原始 CLI 完整通过：北京时间 **2026-10-25T14:14:33.272528+08:00**（UTC 2026-10-25T06:14:33.272528+00:00）。第 1 次检查即退出 0。

已推送 Git 提交：`f13d7e11111a1ee321363dec875c8899146dffa6`。已验证生产静态文件与该提交对应的当前候选源码一致；没有读取 Vercel 后台 Git 元数据。

- 实际应用与 Service Worker 缓存版本：**4.8.6**；语言资源版本：**4.36**。
- 原 `python tools/verify_deployment.py --url https://todo.muquew.com/` 完整通过，全部原断言不变，包括 HTML、CSP、安全响应头与全部静态资源。
- 随后记录响应的包装再次执行同一原 verify 函数：**14/14** 实际 HTTPS GET 均 HTTP 200、bytes/SHA 与候选逐项相同，响应体和安全头已归档。
- **22 个发行源码 + 69 个验证输入 = 91 项**，起末及当前与本轮运行前冻结完全相同。
- 默认代理与 TLS 继承不变，没有添加绕缓存查询或请求头，没有登录 Vercel、手工创建部署或修改源码。
- 4.8.5 的成功部署及更早 4.1 的未匹配记录保留在各自目录，未被改写。

| 实际请求路径 | HTTP | 与候选字节相同 |
| --- | --- | --- |
| `/` | 200 | 是 |
| `fav/android-chrome-192x192.png` | 200 | 是 |
| `fav/android-chrome-512x512.png` | 200 | 是 |
| `fav/apple-touch-icon.png` | 200 | 是 |
| `fav/favicon-16x16.png` | 200 | 是 |
| `fav/favicon-32x32.png` | 200 | 是 |
| `fav/favicon.ico` | 200 | 是 |
| `index.html` | 200 | 是 |
| `manifest.json` | 200 | 是 |
| `resources/en.json?v=4.36` | 200 | 是 |
| `resources/zh-CN.json?v=4.36` | 200 | 是 |
| `resources/en.json` | 200 | 是 |
| `resources/zh-CN.json` | 200 | 是 |
| `sw.js` | 200 | 是 |

[原始报告](report.json) · [摘要 JSON](summary.json) · [原 CLI stdout](attempt-01.stdout.log) · [原 CLI stderr](attempt-01.stderr.log) · [原始文件清单](files.json) · [完整保留文件清单](retained-files.json)

本报告证明候选静态部署和安全头一致；真实域名浏览器功能、跨引擎、离线、真实设备及远程 CI 结果另行记录，不能由本报告代填。
