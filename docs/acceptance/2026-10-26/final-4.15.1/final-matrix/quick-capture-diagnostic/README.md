# 快速记录启动诊断（外部提案，尚未合入）

本目录归档 source `4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4` 下的只读诊断。**两条启动状态断言仍是 proposed，未合入 primary，也不是已经部署的修复。** 本目录不替代原 matrix 的失败结果。

| 原始执行 | 原样证据 | 结论 |
| --- | --- | --- |
| 裸原 CLI，第1次 | [原报告](bare-original-failure/report.json)、[完整 stderr](bare-original-failure/stderr.log)、[完整 stdout](bare-original-failure/stdout.log) | 在 capture_metadata 的第一次 ensure_capture 中，面板持续 hidden，15秒断言失败。 |
| 原 case，加观测，第2次 | [原报告](observed-with-trace/report.json)、[数据库前](observed-with-trace/database-before.json)、[数据库后](observed-with-trace/database-after.json) | 通过；初次 is_visible 已为 true。没有捕获失败时的 pointer 链，不能把这次通过改写成故障复现。 |
| 原 case，精简观测，第3次 | [原报告](observed-light/report.json) | 通过；初次 is_visible 已为 true。达到三次上限后停止复现，没有继续循环。 |
| 正常 CSP 用户首开与关闭再开 | [原报告与全 DB](normal-csp/report.json)、[原视觉审读](normal-csp/manual-review.json) | 首帧2035ms已有 title、query已清，但面板仍 hidden；2037ms原 RAF 聚焦并打开面板，之前没有 pointer/click。关闭再开文本保留，tasks/config全量相等。 |
| 仅外部副本补两断言 | [capture 原日志](external-proposal-validation/capture/stdout.log)、[all 原日志](external-proposal-validation/all/stdout.log)、[汇总](external-proposal-validation/report.json) | capture 7.959秒和全部6个原 case 43.487秒通过。保留全部原数据、重试、原生 beforeunload 和去重不变量。 |

输入文字和 query 状态先于启动 RAF 完成。切换型 ensure_capture 在面板自动打开前后竞态时，可能把已打开面板再关闭；现有证据支持测试启动同步不充分。正常 CSP 用户入口与保留数据检查通过，没有据此修改产品。裸失败由原 finally 关闭浏览器，因此没有失败瞬间 PNG 或 DB；两次观测也没有捕到这条失败事件链，这一限制保留在[原诊断](diagnosis.json)中。

最小方案只在原 value/query 断言后等待面板可见与输入框已聚焦：[统一补丁](proposal/quick_add_recovery_playwright.patch)、[proposed 原副本](proposal/quick_add_recovery_playwright.proposed.py)、[AST 范围证明](proposal/scope-proof.json)。原 verifier SHA 为 `0ed4fc9e8415a2963acaa7844873a50fc718e49105c6eeb29adc468a8b26e7a7`；外部 proposed SHA 为 `a09c0cd9affc8124132fc1a92e3bbc73513b77fb15df8bbaebe5654c80ed9cf0`。

仅保留两张已实际审读的真实图片：[首开](normal-csp/01-first-capture-open.png)、[关闭再开](normal-csp/02-reopened-capture-retained.png)。没有修图、伪造 DOM、force click 或任意等待；WebKit 使用原已验证 sysroot 与官方 host-validator 环境标志。原 HTTP/reduced-motion case 与正常 CSP/normal-motion 用户检查分别标明，不互借结论。

[原文件来源清单](original-sources.json)列出全部保留及省略文件的原绝对路径、SHA256、字节数和省略原因；大 trace、重复源代码与未审读的冗余观察图只索引，不复制。[本目录 manifest](archive-manifest.json)仅验证这份归档的文件完整性，不表示全站或整套 matrix 通过。所有原 JSON/日志均未截断或改写；本次只复制文档，没有新开浏览器或干扰现有验收进程。
