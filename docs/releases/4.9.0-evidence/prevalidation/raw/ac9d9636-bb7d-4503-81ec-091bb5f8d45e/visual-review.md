# 50f6fffe 候选八图审读：发现真实输入覆盖问题

本批8张已逐张view，正常生产CSP、实际Chromium，原始报告与PNG均保留不变。它们不是最终发行图：根代理在07英文图指出quick-add首字符疑似被图标覆盖后，已通过同源码、正常CSP的只读计算几何确认真实问题。此前仅凭整图未确认该首字符细节的判断，以本次测量纠正。

## P0 / P1

- P0：本批未发现。
- P1：一个CSS specificity根因影响三个装饰输入。`input:not([type="checkbox"])` 的0,1,1与后置font选择器覆盖类规则，实际padding为9px 12px、font14px、minHeight42px。
- 1440px quick-add：文字起点x273，图标x272–290，侵入17px。命令面板：文字起点x423，图标x422–440，同样侵入17px。390px quick-add同样侵入17px。
- 1440px搜索：padding-right12，文字内容右边界1023；clear位于958–984，shortcut位于997.55–1026；真实输入的长查询文字到967.18，进入clear区约9.18px。390px内容右边界311，clear位于288–314，缺少23px安全空间。
- 完整CSS命中、font/minHeight、输入/图标/clear/shortcut BCR、文字起点与源身份在 `/tmp/task-tracer-input-geometry/7cfc7978-0efe-44e9-bf40-976d55daee1e/report.json`。探针source50f6起末同，错误0，context/browser/server/thread均已关闭。不能忽略已有实际图中的问题，也不能用自动捕捉passed代替视觉通过。

根代理将让应用负责人仅修正这三个输入的base/media选择器，原规则值不变，再以新SHA重捕。本批不得复制为发行源。

## 八图逐张观察

| 图 | 观察 |
| --- | --- |
| 01-zh-desktop-light | 四父任务/首任务1/2子任务/0父任务完成、短周日期索引与月历可读；没有页面横溢。quick-add存在上述P1，中文字符轮廓较不明显，不因此排除覆盖。 |
| 02-zh-desktop-dark | 暗面层次与选中白勾可辨；同一个quick-add几何问题存在。 |
| 03-zh-narrow-dark | 日期摘要与入口保留、主任务纵向排布，保存视图按钮已收进工具条右内边界；输入仍受generic覆盖。 |
| 04-zh-narrow-schedule | 月历层完整落在390视口，10月1日周四、25日周日正确；关闭日程实际断言焦点返回入口。 |
| 05-zh-narrow-light | 必要勾选边界、项目/日期可辨，未见任务/提示相叠；本图焦点为workspaceScheduleToggle。 |
| 06-zh-new-task | 空新建名称字段获焦，取消/添加页脚可见；下方子任务需内部滚动，未声称本图包含全部字段。 |
| 07-en-desktop-light | Read for 20 minutes已修、英文UI可读；quick-add首字符图标重叠在此图最明显，已列P1。 |
| 08-en-new-task | 英文表单名称字段获焦、说明与页脚可读；背景quick-add仍含P1。 |

## 几何、焦点与证据范围

- 1440×1024、DPR1：首任务标题x308/y359.75。
- 390×844、DPR1：首任务标题x69/y339.296875。
- 八图scrollWidth==clientWidth（1440或390）；局部文字/图标覆盖不会使scrollWidth增加，所以无页面横溢不能证明输入没有覆盖。
- 日程关闭后焦点回workspaceScheduleToggle已实际断言；05图记录同入口焦点；06/08图焦点均在taskName。新建取消无脏提示已操作，但该脚本未额外断言取消后的所有焦点路径。
- 合成数据与受控浏览器时间明确声明：每个独立页面从2026-10-25 07:00UTC（北京15:00）开始正常前进，无pause/fixedTime/manual advance。Python实际墙钟08:46:14.906–08:46:24.327UTC分别保留。
- 23发行源文件+70验证文件=93输入，起末两组完整身份相同。自动流程错误0、清理完整；PNG、原index输入与外部脚本哈希均已核对。
- 未改仓库、未复制screenshots、未作性能结论；并行smoke/a11y结论由各自原始报告说明。
