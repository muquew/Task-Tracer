# 补充视觉审读与编辑器原生验收

本目录保存三个各自绑定来源的证据集。**已审读**只表示对应真实截图经过人工查看，不表示所有流程或实体设备通过；不同阶段的身份和通过结果不互相移用。

| 证据集 | 保留范围与原身份 |
| --- | --- |
| [主题十图原记录](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/README.md) | 20261025T192938Z 的10张真实图片、逐图 JSON、原审读、真实备份、完整任务/写入状态前后及5 runtime/5 helpers映射。实际拍摄 index为4a7e；其边界是本次自己的运行时/工具指纹，公开PNG不在该次锁内。 |
| [编辑器 final-v4 汇总](editor-v4/final-v4-summary.json) | 原 Firefox10/10 与 WebKit10/10 CLI，1280/390两宽度、原5个case；完整原stdout/stderr、native results/DB/events JSON和107项前后身份。source23=`574778e1e805a7a70fcc808d158461140cb1bf7c9264ac08f163e3df63c18e92`；verification84=`dfbbc08ec28deb0e028f8318b592f6cc1b9cb5c3270f99ba1cbc19866d013df7`。 |
| [公开四图实际来源](public-final-4a7e/capture.json) | 独立中英文真实创建任务、完成及今日计划操作；1440×1000、正常CSP/normal motion，index4a7e。保存原capture.py、来源元数据、四PNG、人工审读和107项首尾；仅称该源已审读。 |

[主题原人工审读](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/manual-review.json)、[真实备份](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/task-tracer_backup_2026-10-25_19-29-59-296.json)、[运行时/工具前](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/before-identity.json)与[后](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/after-identity.json)按原阶段保留。源码审读原身份是0847，[原审读边界](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/source-review/review.json)及[原0847到4a7差异](theme/20261025T192938Z-6f46f346-b8b5-4b2f-a20e-d4090ccd619a/source-review/0847-to-4a7-index.diff)只证明一行日历冗余aria-label删除，不将0847阶段浏览器结果移用到final107。

编辑器只取 final-v4：

- [Firefox 原说明](editor-v4/firefox-e9b0e865-5eb7-47e3-8080-785c4c545d8b/summary.json)、[stdout](editor-v4/firefox-e9b0e865-5eb7-47e3-8080-785c4c545d8b/stdout.log)、[stderr](editor-v4/firefox-e9b0e865-5eb7-47e3-8080-785c4c545d8b/stderr.log)、[native results](editor-v4/firefox-e9b0e865-5eb7-47e3-8080-785c4c545d8b/native/20261025T195349Z-firefox-04327e97/results.json)。
- [WebKit 原说明](editor-v4/webkit-94dcf394-be7a-45f1-bc34-3d8b7923ba59/summary.json)、[stdout](editor-v4/webkit-94dcf394-be7a-45f1-bc34-3d8b7923ba59/stdout.log)、[stderr](editor-v4/webkit-94dcf394-be7a-45f1-bc34-3d8b7923ba59/stderr.log)、[native results](editor-v4/webkit-94dcf394-be7a-45f1-bc34-3d8b7923ba59/native/20261025T195831Z-webkit-ab4d7679/results.json)。
- [v4冻结回执](editor-v4/v4-freeze-inputs.json)与两个目录里的 before-identities.json / after-identities.json 保留原23+84身份。原记录声明并观察到HEAD2771。较早中断的Firefox不计入任何通过结果，也未复制其case来补数。

公开图：[中文列表](public-final-4a7e/task-list.png)、[英文列表](public-final-4a7e/task-list-en.png)、[中文表单](public-final-4a7e/add-task.png)、[英文表单](public-final-4a7e/add-task-en.png)。[原人工审读及复制记录](public-final-4a7e/manual-review-and-publication.json)和[root六图审读](public-final-4a7e/root-final-review.json)保持原文与原SHA。此处没有复制或冒用final-0847公开图的来源元数据。

[原文件来源清单](original-sources.json)逐项列出原路径、SHA256、字节数及未复制原因。重复80tools/源树、大trace，以及未额外人工审读的native case PNG仅索引；原logs和JSON均完整复制，不截断、不修改passed。原记录中的绝对路径及对省略附件的引用仍保留，可用来源清单追溯。[本目录manifest](archive-manifest.json)只校验限定归档内容，不替代全量CI、发布或matrix结论。
