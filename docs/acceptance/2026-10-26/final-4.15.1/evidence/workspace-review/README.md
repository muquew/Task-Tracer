# 最终交付：工作区实际使用审查

本轮新访问隔离的4.15.0快照，index SHA-256 `bfb0a142fb4c813e17af52267062c6faa63a7a56bd5e41feb335728c1999e9c5`。使用真实UI、合成任务、Chromium154、1440×900／390×844／320×700、中英与雾紫亮暗、正常部署CSP及正常动画。初始HTTP响应、实际安全头、浏览器身份见[source.json](source.json)，23项快照来源见[source-files.json](source-files.json)。没有修改仓库应用或工具。后续主分支修复不会回写这份快照或结论。

本会话83份观察，实际打开审读26张代表PNG，名单见[审读及数据核对](review-verification.json)。全部观察的page error为空、整页无横向溢出。存在1次执行者使用不存在的 `#emptyStateClearBtn` 定位超时，原[会话](session.json)保留；随后按真正可见按钮“清除搜索与筛选”成功完成同一流程，不将此超时算作产品缺陷。浏览器与服务器已关闭。

## 分步健康结论

|步骤|实际流程与结论|健康／证据|
|---|---|---|
|1|从空白工作区用真实快速记录创建8任务，跨产品／个人／Inbox、有日期／无日期、标签|健康；[桌面列表](04-list-desktop.png)，日期词“昨天”的例外单列第14步|
|2|完成“复盘本周工作”，统计显示最近7天完成1、今日1，项目待办准确|健康；[统计](06-statistics-with-record.png)，不以测试通过数替代口径核对|
|3|统计今天截止进入2项待办，查询变为status:active due:today，独立返回统计|健康；[下钻](07-statistics-today-drilldown.png)，原搜索及记录完整|
|4|桌面月历、日期按钮、时间线分组，手机紧凑月历与所选日程|健康；[月历](09-calendar-populated.png)、[桌面日期添加](10-calendar-selected-today.png)、[时间线](11-timeline-populated.png)、[手机日程](66-small-mobile-day-agenda.png)。桌面日期按钮语义是按该日添加，手机同位置为打开日程，均有明确aria/title|
|5|标签搜索、无结果、清空搜索，当前范围与恢复入口明确|健康；[空搜索](14-search-empty.png)，无任务假空白或横向滚动|
|6|选择产品范围与手动排序，键盘ArrowUp将发布清单移到验收项之前|健康；[顺序与焦点](19-keyboard-manual-reorder.png)，读库实际order改变，未声称测试了真实触摸拖拽|
|7|把产品范围＋#重点保存为“产品重点”，清条件后点击恢复|健康；[保存](23-saved-view-created.png)、[应用](25-saved-view-applied.png)，准确回到唯一产品方案任务；手机抽屉也能应用|
|8|直接开启选择、选2任务、更多动作、移动到交付项目，再Undo|健康；[更多](31-batch-more.png)、[移动](34-two-tasks-moved.png)、[撤销](35-batch-move-undone.png)；31与35所有8任务逐字段完全相同|
|9|单条任务加入今日计划，计划内无搜索结果后用实际清除按钮恢复，仍留在计划|健康；[计划空搜索](39-plan-empty-search.png)，38/39/41分别1/0/1项，焦点与范围能恢复|
|10|归档并Undo；删除确认具名，取消不写任务，再确认删除和Undo|健康；[删除确认](45-delete-confirmation.png)、[撤销](49-delete-undone.png)；42/44归档往返、44/46/49删除取消／撤销任务全部逐字段相同|
|11|390深色英文列表、收起筛选、320选择及更多浮层|健康；[列表](54-mobile-dark-list.png)、[320批量](59-small-mobile-batch.png)，菜单向上避开底栏，动作可见、退出可达|
|12|320统计、下钻返回、月份格与三任务日程、时间线、导航抽屉及保存视图|健康；[统计行](62-small-mobile-statistics.png)、[月历](65-small-mobile-calendar.png)、[日程](66-small-mobile-day-agenda.png)、[抽屉](68-mobile-navigation.png)，常驻四视图入口始终可达|
|13|真实下载最终JSON备份并调用原完整性helper，核对11个任务|健康；[下载反馈](83-actual-data-backup.png)、[真实备份](task-tracer_backup_2026-10-25_18-50-36-694.json)，原8任务及3个日期复现案例均保留|
|14|中文昨天／前天、英文yesterday与时间组合，预览与入库|P2需修；如下所述，常用过去日期词未被识别，独立时间却默认今天|

## 唯一确认的工作区缺陷：P2常用过去日期词漏识别

当前浏览器为Asia/Shanghai的2026-10-26。输入 `昨天 15:00 历史复盘` 时，预览明确显示 `Mon, Oct 26, 2026, 03:00 PM`；保存后名称仍为“昨天 历史复盘”，`dueLocalDate=2026-10-26`。`yesterday 15:00 Historical review` 和 `前天 15:00 历史事项` 同样被安排为今天。原[预览](71-yesterday-preview.png)、[英文预览](73-english-yesterday-preview.png)、[前天预览](75-day-before-preview.png)均实际打开，保存字段在72/74/76 JSON及真实备份中。

这不是时区误差或截屏猜测。原 `parseQuickAddDateToken` 的相对词Map仅列今天／今日／today／明天／tomorrow／后天；之后已支持上周等过去星期与显式年月日。未知词保留标题，而独立识别的15:00按已有规则设为今天，因此常用过去日期语句容易得到意料外安排。预览确实可供核对，故列P2而非无提示的数据损坏。

建议只增加精确token：昨天／昨日／yesterday→-1、前天→-2。保留纯时间默认今天、普通未知单词保留标题、原星期和显式日期规则；不扩展成泛化NLP，也不拒绝所有未知任务词。根代理已接受这项小修；本报告仍只证明修复前bfb，不能写成新版已通过。

## 限制与交付判断

本组没有其他确认的P0/P1，已有工作区结构与日常流程可以保留。是否达到全项目最终交付仍需根代理汇总编辑器、数据、离线／升级、全量原检查和多引擎结果，本文件不越权宣称整个项目已完成。截图不能证明完整WCAG、真实手机输入法、原生通知或安装；只有列明的26PNG实际审读，其余JSON是动作／数据观察而非全图人工审读。相对过去日期修复需要独立新源码复验。
