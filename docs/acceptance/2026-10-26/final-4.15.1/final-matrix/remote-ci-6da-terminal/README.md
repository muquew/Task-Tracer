# 原6da标准运行终态

[标准run40233014544](https://github.com/muquew/Task-Tracer/actions/runs/40233014544)，提交`6da3c7293f08c5d16ca73c7a63d8ff74e17358db`，分支`codex/final-stable-delivery-20261026`，于21:25:37Z公开轮询确认结束：**整体Failure，30m11s；唯一失败job为WebKit compatibility**。

|Job|真实终态|时长|
|---|---|---|
|[checks](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575952)|succeeded|30m9s|
|[compatibility (chromium)](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575939)|succeeded|13m24s|
|[compatibility (firefox)](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575968)|succeeded|14m52s|
|[compatibility (webkit)](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575649)|failed|22m30s|
|[deployed_site](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288576846)|skipped，push条件下预期|0s|

checks公开页只有warning/notice，无error。WebKit仍为验证步骤exit1，不是90分钟总超时；具体失败程序未通过此公开页暴露。未取得原生逐程序报告、正文日志或artifact，不能补造其内容。

[terminal.json](terminal.json)与`evidence/`保存该终态原公开状态及五job页面文本；[receipt.json](receipt.json)绑定原路径和哈希。[首次失败](../remote-ci-6da-first/README.md)仍保留当时In progress，不被本终态覆盖。相同提交的独立repeat40235376686及临时WK诊断各有独立来源，本记录不移用它们的结果。

[manifest.json](manifest.json)仅覆盖本子目录，排除自身和其他scope。main/生产未由本记录发布或验收，也未宣布正式下载包已提供。HEAD与107运行输入未改。
