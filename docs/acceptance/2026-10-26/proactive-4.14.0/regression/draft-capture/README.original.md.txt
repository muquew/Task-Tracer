# 4.14.0 草稿、输入法与捕获保护 lane

六个原生程序的最终结果均通过，源为 index `765c354ba6e0c2eb00c01e7dc0bc9e841af11a1fe7eaa6e66537f9058a38f672`。两轮原报告各自保留源码、资源、vercel/sw 和工具/helper 起末哈希；没有借旧版本结果。

第一轮依次运行全部六程序：IME、pending subtask、context creation、direct capture、quick-add recovery 五项原样通过；完整 task_draft 在旧空星期默认策略断言失败，原报告/日志保留。新界面先拦截空星期，不会进入配额写入，故该失败属于旧测试契约。

仅 task_draft 的 `check_weekday_recovery` 加现代分支：先证明全空星期提交不改字段或数据库，再由真实控件明确选择周四后触发原配额失败；下载草稿、同文档重试、恢复保留周四；恢复后再次清空仍不写入，重新明确周四后仅保存一次 `[4]`。旧归档分支保留原默认策略。模块 AST 证明其它节点未改变。

适配后完整 task_draft 单独重跑通过（58.771秒），包括原关闭/脏草稿/失败/迟发提交/完整配额恢复，以及捕获交接与真实 beforeunload 取消。其它五个已通过程序未重复执行。详见 [lane-summary.json](lane-summary.json)、[首轮原报告](20261025T174530Z-32d5fe02/report.json)、[完整重跑原报告](20261025T174949Z-5ae87a60/report.json)、[适配范围](weekday-adapter-scope.json)。

只有 pending 程序使用正常部署 CSP；其它原程序保留其原 HTTP handler，不能据此声称 CSP 运行强制执行。输入法程序为 DOM composition，不等于原生 OS 输入法。未跑跨引擎或规模矩阵；所有本 lane 浏览器、HTTP server 已关闭，未发布 Git。
