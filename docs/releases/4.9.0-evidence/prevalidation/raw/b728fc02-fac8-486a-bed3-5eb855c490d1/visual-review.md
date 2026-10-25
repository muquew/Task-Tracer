# c74e68e5 八张真实截图审读

八张均已逐张实际view。本矩阵未观察到P0/P1。原始report.json、PNG、index.input.html、capture.py保持不变；独立审读在本文件和visual-review.json，发行四图由根代理核图后选择，本代理未复制进仓库。

## 重点确认

- 07英文桌面quick-add：plus与tomorrow的t已明显分开；01中文浅色、02暗色的plus与首字同样分开。旧批中的首字符覆盖在这些实际图中不再出现。
- 03/05窄屏搜索有清楚的左侧文字间距，保存视图按钮收在工具条右内边界。主任务没有被新工具行挤走，首标题比旧覆盖批提前6px。
- 06/08中英普通表单：名称输入获得焦点，标签、正文输入、边距和固定取消/添加页脚可读；未见此次装饰输入ID修复误伤普通表单的可见迹象。
- 04日程层在390×844中完整显示月份、日期与关闭按钮，10月1日周四、25日周日正确。关闭后焦点回入口已实际断言，05捕捉焦点记录为workspaceScheduleToggle。

## 八图

| 图 | 逐张记录 |
| --- | --- |
| 01-zh-desktop-light | 四父任务与首任务1/2子任务可读；quick首字分离，短周索引/月历/即将到期清楚。 |
| 02-zh-desktop-dark | 暗色层次、必要勾选边界与白色勾号可辨；quick首字分离。 |
| 03-zh-narrow-dark | 真实今天截止1项与日程入口保留，搜索/保存视图正常内收，任务纵向排布无横溢。 |
| 04-zh-narrow-schedule | 月历层完整，日期与事件点可读，关闭焦点返回入口。 |
| 05-zh-narrow-light | 浅色必要边界和项目/截止元信息可辨，无提示遮挡，搜索与右侧按钮不相压。 |
| 06-zh-new-task | 默认空中文新建、名称焦点与固定页脚可见；下方子任务仍属内部滚动内容。 |
| 07-en-desktop-light | 英文UI、Read for 20 minutes自然空格正确；quick plus与首字明显分开。 |
| 08-en-new-task | 英文字段、说明、边距与固定页脚可读；名称字段获焦，未见普通表单布局变化。 |

## 精确范围

- 1440×1024、DPR1，首任务标题x308/y359.75。
- 390×844、DPR1，首任务标题x69/y333.296875。
- 八张scrollWidth==clientWidth，分别为1440/390；局部安全区的更宽视口、长查询与命令面板检查由根代理单独完成，本八图不代填那些测量。
- 正常生产CSP，无bypass_csp、ignore_https_errors或附加浏览器安全绕过参数。实际CSP响应头保留于原报告。
- 23个发行源文件+70个验证文件=93输入，起末两组完整身份相同。errors/page_errors/console_errors/request_failures/http_errors均0；context/browser/server/thread清理完成。
- 数据为明确合成fixture；每个页面导航前受控浏览器时钟从2026-10-25 07:00UTC（北京15:00）开始并正常前进，不pause/fixedTime/manual advance。Python实际墙钟08:53:19.469–08:53:26.183UTC分别记录，不将浏览器时钟当墙钟。
- PNG尺寸与哈希、原始index输入与外部脚本哈希均已核对。原生日期/时间控件保持当前Chromium环境MM/DD/YYYY与AM/PM显示；下方表单需内部滚动，截图不声称包含全部字段。
- 未修改仓库或复制screenshots；不作性能、真实设备、完整无障碍或生产部署结论。
