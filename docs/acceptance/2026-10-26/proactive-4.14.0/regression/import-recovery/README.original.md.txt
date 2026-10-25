# 4.14.0 原导入与恢复回归 lane

指定 7 个原程序按顺序执行，全部首次 exit 0；总程序用时 158.395 秒。本 lane 无失败尝试，也没有追加工具适配。原工具副本、实际命令、UTC 起止时间、退出码、原 stdout/stderr 合并日志及输入文件 bytes/SHA 均逐次保留。

[完整运行记录](lane-report.json) · [机器摘要](summary.json) · [文件清单](manifest.json)

| 原程序 | 原 CLI 状态 | 秒 | 原报告 | 原日志 |
|---|---|---:|---|---|
| `recovery_playwright.py` | exit 0 | 22.71 | [report](01-recovery_playwright/attempt-01/report.json) | [console](01-recovery_playwright/attempt-01/console.log) |
| `recovery_management_playwright.py` | exit 0 | 18.36 | [report](02-recovery_management_playwright/attempt-01/report.json) | [console](02-recovery_management_playwright/attempt-01/console.log) |
| `craft_import_summary_playwright.py` | exit 0 | 11.042 | [report](03-craft_import_summary_playwright/attempt-01/report.json) | [console](03-craft_import_summary_playwright/attempt-01/console.log) |
| `import_conflicts_playwright.py` | exit 0 | 5.976 | [report](04-import_conflicts_playwright/attempt-01/report.json) | [console](04-import_conflicts_playwright/attempt-01/console.log) |
| `import_preview_concurrency_playwright.py` | exit 0 | 36.721 | [report](05-import_preview_concurrency_playwright/attempt-01/report.json) | [console](05-import_preview_concurrency_playwright/attempt-01/console.log) |
| `imported_text_edit_playwright.py` | exit 0 | 40.531 | [report](06-imported_text_edit_playwright/attempt-01/report.json) | [console](06-imported_text_edit_playwright/attempt-01/console.log) |
| `imported_reminder_edit_playwright.py` | exit 0 | 23.055 | [report](07-imported_reminder_edit_playwright/attempt-01/report.json) | [console](07-imported_reminder_edit_playwright/attempt-01/console.log) |

每项都使用 `python 原程序路径`，不增加 case/browser 参数；完整实际解释器路径见每个 report。显式选择 `/usr/bin/chromium`、禁止 bytecode 写入，并使用本地服务而非外部 TASK_TRACER_URL。原程序自己的夹具、故障注入、运动设置和数据断言未变。

所有七项的 index、两份语言资源、vercel 配置和 service worker 均为同一组起止字节；不要求正在更新的截图或发行文档保持 payload 文件集合。

| 输入 | 字节 | SHA-256 |
|---|---:|---|
| `index.html` | 969460 | `765c354ba6e0c2eb00c01e7dc0bc9e841af11a1fe7eaa6e66537f9058a38f672` |
| `resources/en.json` | 57088 | `e8bd753937abc0c5cc489c53632554b62bc92ad303fdcf2a6bb442014fac70bd` |
| `resources/zh-CN.json` | 55580 | `3fe25694a9c5b5011d8e2e8c1b00f8ed22baf74939f2259c23b884ee6f1dabc9` |
| `vercel.json` | 1194 | `2c45cfccd1068c8659881f2f3f80d5fcb86d522c4e029817cdb22d00c31fb389` |
| `sw.js` | 8305 | `33faf13b0a83140f11198a77029d94b9071a621de7238fe45c43cd9b721b0dd9` |

本结果遵循原 CLI 默认的本地 Static HTTP，**未附部署 CSP**；除 recovery 程序使用原浏览器默认运动设置外，其余六项保留原 reduced-motion 上下文。正常 CSP/正常动画的人工和定向检查由独立收据负责。这里不扩大为跨引擎、线上、OS 通知、规模性能或完整商业发布证明。

七个 CLI 均正常退出，原程序中的浏览器/上下文和本地服务关闭流程已完成。未检查或关闭其他 agent 的资源。未写仓库 Markdown，未修改应用、资源或检查注册表。
