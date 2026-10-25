# GitHub 推送后生产部署匹配验收

结论：**通过**。

首次未修改原 CLI 完整通过：北京时间 **2026-10-25T13:23:39.640485+08:00**（UTC 2026-10-25T05:23:39.638919+00:00）。第 1 次检查即退出 0，无需重试。

已推送本地 Git 提交：`d9b2a58d8359aa27c087f3da809d7de27ee398f0`。本报告验证生产静态文件与该提交对应的当前候选源码相同；没有读取 Vercel 后台的部署 Git 元数据。

- 线上与候选应用/Service Worker：4.8.5；语言资源：4.36。
- 原 `python tools/verify_deployment.py --url https://todo.muquew.com/` 全部原断言通过，包含 HTML、CSP 和登记安全头、全部静态资源。
- 随后以仅记录响应的包装再调用同一原 verify 函数，14/14 实际 HTTPS GET 均 200，响应 bytes/SHA 与当前候选逐项相同。
- 22 个发行源码输入与 69 个验证输入起末及当前均保持一致。
- 继承默认代理与 TLS 验证；没有额外 cache 参数、请求头覆盖、Vercel 登录或手工部署。
- 之前4.1旧部署的失败/未匹配报告保留在独立目录，没有覆盖。

[原始机器报告](report.json) · [原 CLI stdout](attempt-01.stdout.log) · [原 CLI stderr](attempt-01.stderr.log) · [初始文件 SHA 清单](files.json)

本报告只证明静态文件和安全头匹配；真实域名浏览器流程、离线、真实设备和远程 CI 状态由各自实际结果另记。
