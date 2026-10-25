# 公开源码位置诊断：33d2d9b

[运行40230821013](https://github.com/muquew/Task-Tracer/actions/runs/40230821013)，提交`33d2d9bf6e15b3234383ef1b02a50f56a6ff285d`，临时分支`codex/ci-outcome-summary-20261026`：Failure，1m30s。[checks](https://github.com/muquew/Task-Tracer/actions/runs/40230821013/job/121281960309) failed，1m28s。

公开安全注释为：

- `pwa_default pass`
- `pwa_full pass`
- `smoke_default fail AssertionError smoke_playwright.py:2596:exercise_notifications`
- 原程序汇总仍为`smoke_playwright.py exit=1`，原验证步骤仍保留exit1。

原默认smoke恢复后确实失败在通知练习函数，两个PWA regular-profile对照均报告通过。primary同文件第2596行只读核对为点击通知开关后要求其`aria-label`为“关闭通知”；具体运行时实际值及权限状态没有公开，不能提前判定是标签契约、权限还是其他通知路径问题，也不把两次PWA通过扩展成排除所有launcher差异。

[summary.json](summary.json)保留精确类型/源码位置、两个variant、任务URL、提交及原文件指纹。原公开页面文字和提取JSON均独立保存。本次仅GET这个新run与两job；未读取受限API、原日志/artifact、原异常正文、环境或凭据。deployed_site预期skipped，compatibility按诊断条件排除，不产生最终验收结果。

本目录与f8程序名诊断分开，`manifest.json`只覆盖列出的本目录文件并排除自身。未修改primary或任何运行输入，也未运行生产验收；生产driver仍等main/Vercel匹配信号。
