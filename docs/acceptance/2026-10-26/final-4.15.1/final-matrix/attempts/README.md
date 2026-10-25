# 已撤回的最终矩阵尝试

**这些记录均非通过结果，不能移用至新的最终候选。** 原生矩阵正常接收 SIGTERM，原报告和全部关联日志逐字节保留；中断前后输入相同，进程清理收据均已确认。

|尝试|入口 / verification|Chromium 完成程序|Firefox 完成程序|WebKit 完成程序|结果与原因|
|---|---|---:|---:|---:|---|
|[v1](v1-0847/summary.json)|0847b854… / 6fc0d03b…|1|0|未启动|中断；等待修复日历详情分页按钮真实 ARIA 名称缺陷|
|[v2](v2-4a7-6fc/summary.json)|4a7e54f7… / 6fc0d03b…|4|2|2|中断；等待旧 focus helper 正确检查现有 quick-add 外框，并重新冻结工具|

“完成程序”是原报告已结束的程序数，不表示原计划每引擎 33 个全部执行。v1 两引擎均原退出 143，WebKit 排队但未启动；v2 三引擎均原退出 143。两轮均 `completed: false`、`passed: false`。新最终 v3 需在完整无障碍检查后单独执行，不能补写到这些原始记录。

v1 入口 `0847b854ea99e95d37ada7a77e307c3266b2a3d2b54db51d6f8309875a506fb4`，source23 `18f4b3c2b16fc0b21ec7cf895cf9a42e4fd8002b8c834a1ad90e9ef7183e9cbc`。v2 入口 `4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4`，source23 `61ce62bb18afa3fc612ecb634f20f74ff577162ed458a12d6cf31ef840d46543`。两轮 verification84 均 `6fc0d03b8437601b3f07a7304c6059d0f644b625f8c8a4213110e14a298593f3`。

原命令、实际环境、输入逐项 SHA、stdout/stderr、原生 JSON、每程序完整日志，以及中断请求和关闭确认都在各轮 `raw/`：[v1 输入](v1-0847/raw/frozen-inputs.json)、[v1 关闭](v1-0847/raw/interruption-confirmed.json)、[v2 输入](v2-4a7-6fc/raw/frozen-inputs.json)、[v2 关闭](v2-4a7-6fc/raw/interruption-confirmed.json)。

每轮重复的 107 文件源码快照没有复制；[原文件清单](original-files.json)逐项列出外部原路径、真实字节数、SHA 与 `archived: false`。冻结输入清单和开始/结束映射已完整复制，可核对各自身份。原记录中的绝对外部路径仍保留其原值。未截断任何复制日志，未追加人工“通过”字段。

[本范围清单](manifest.json)只覆盖 `final-matrix/attempts/` 并排除自身，不改动历史阶段清单。
