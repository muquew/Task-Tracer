# Help and support / 使用与反馈

Read the [English guide](README.md) or [中文说明](README_zh_cn.md) for capture, planning, recurrence, reminders and backups. Task Tracer keeps tasks in the current browser profile; another browser, device or site address has separate storage. Browser reminders depend on browser and operating-system behavior and are not guaranteed system alarms.

使用方法见上述中英文说明。任务保存在当前浏览器配置中；其他浏览器、设备或域名具有独立存储。提醒受浏览器与系统行为影响，不能当作保证送达的系统闹钟。

## Protect data before troubleshooting / 排查前保护数据

Export a task JSON backup and, if needed, a separate **Transfer saved views** JSON file before changing profiles, clearing site data or reinstalling. Keep both outside the browser; app preferences and recovery checkpoints are not included. Use **Import** for task files and **Transfer saved views** for view files. CSV is a spreadsheet report, not a restorable backup. Recovery history is stored in the same browser and cannot replace a downloaded copy. If the application offers emergency export during a storage error, save that file before trying resets. For a blocked database upgrade, close older Task Tracer windows, including installed-app windows, then retry.

更换浏览器配置、清理网站数据或重新安装前，请先将任务 JSON 备份及需要保留的独立视图 JSON 保存到浏览器之外。应用偏好与恢复历史不包含在这些文件中；任务文件使用“导入”，视图文件使用“迁移保存的视图”。CSV 不能恢复数据；同一浏览器内的恢复历史也不能替代下载的备份。存储故障时若有紧急导出入口，请先保存文件。数据库升级被阻塞时，关闭旧版标签页和独立应用窗口后重试。

If a storage error interrupts Quick add, keep that page open. Nonblank input stays read-only and copyable; copy it before refreshing, closing or losing the page. Retry reconnects storage without a reload while quick-add text or retained forms remain. Failed retries keep the text; after recovery, explicitly submit once. Source details from capture links remain with the retained text. Quick-add text is not included in full-form draft files and is not durably autosaved.

快速添加遇到存储错误时，请保持页面打开。有文字的输入框会保留为只读，可选中复制；刷新、关闭或丢失页面前请先复制。有快速添加文字或待恢复表单时，“重试”在原页重连存储；失败重试保留文字，恢复后请自行提交一次。捕获链接的来源信息会随保留原文延续。快速添加文字不包含在完整表单草稿文件里，也不会自动持久保存。

If a storage error shows **Unsaved task draft retained**, keep that page open and download its drafts before refreshing. This `task-draft` file is a reference copy of unsaved forms, separate from Emergency backup of committed tasks; it cannot be restored using task Import. Verify that the download was saved. With drafts retained, Retry reconnects storage without reloading; Resume editing becomes available after recovery. Drafts left only in memory are lost on refresh, close or crash, and the browser may suppress departure warnings.

存储错误后若提示“未保存的任务草稿已保留”，请保持页面打开，刷新前先下载草稿。该 `task-draft` 文件仅供查阅未保存表单，与已提交任务的紧急备份不同，不能通过任务“导入”恢复；请确认下载文件已保存。有待恢复草稿时，“重试”在原页重连存储，恢复后可继续编辑。只在内存中的草稿会随刷新、关闭或崩溃丢失，浏览器也可能不显示离页提醒。

If a task file is still reading, cancel that dialog before starting another task; a cancelled or superseded read will not replace the newer form or preview. If a task or view import rebuilds its preview because the data changed, review the new preview and confirm again. If a database conflict closes the task preview, select the file again to start a fresh review. For task replacement, download the new safety snapshot as prompted. If a destructive confirmation is rejected, inspect the latest tasks and start that action again; repeated clicks on the old approval are not a recovery method.

任务文件仍在读取时，可先取消读取弹窗再处理其他任务；已取消或被较新文件取代的读取不会覆盖新的表单或预览。任务或视图导入因数据变化而重建预览时，请检查新预览再确认；若数据库冲突关闭了任务预览，请重新选择文件开始检查。替换任务时按提示重新下载安全快照。删除或恢复等确认被拒绝后，请检查最新任务，再重新发起操作，不要反复点击过期确认。

Recovery history can retain old copies of deleted tasks. Review checkpoint names/statuses before restoring, or export the selected checkpoint for a separate task JSON copy; that download does not mark current tasks as backed up. Clear recovery history removes local checkpoints after confirmation and does not remove current tasks or downloaded files. If the history changes, review the refreshed list and start the clear confirmation again. Later task writes create new checkpoints.

恢复历史可能保留已删除任务的旧副本。恢复前请检查恢复点中的名称和状态，也可将所选恢复点另存为任务 JSON；该下载不会把当前任务标记为已备份。清空恢复历史会在确认后删除本地恢复点，不删除当前任务或已下载文件。历史变化后请检查刷新列表，重新发起清空确认；后续任务写入会建立新恢复点。

A newer task change from another window can make Undo unavailable or cause it to be refused. Check the latest tasks rather than repeatedly retrying the older action; a fresh task change can establish a new Undo. This protects unrelated newer fields as well as the task you were editing.

另一窗口的较新任务修改可能使撤销不可用或被拒绝。请检查当前任务，不要反复点击旧动作；新的任务操作仍可建立新的撤销记录。这项保护也包括与刚才操作无关的较新任务字段。

Batch mode starts with 100 matching task cards and offers Show more. **Select all matching** selects the entire current search/project/status scope, including tasks not yet displayed. The selection count shows the operation's scope; loading another page retains selections. Changing the search, project or status drops selections outside the new scope. Review that count before completing, archiving or deleting tasks. Manual ordering outside batch mode still renders the complete matched list.

批量模式先显示 100 个匹配任务，可继续“显示更多”。“全选匹配项”会选择当前搜索、项目和状态范围内的全部任务，包括尚未显示的项目；选择数量表示实际操作范围，翻页保留选择。修改搜索、项目或状态后，会移除新范围之外的选择。完成、归档或删除前请核对选择数量。非批量模式的手动排序仍渲染完整匹配列表。

## Dates, live views and saved views / 日期、持续刷新与保存视图

Editing one field keeps accepted imported text, tags and reminder values in the other fields. Tags containing a comma or double quote appear as quoted fields: wrap a comma-containing tag in double quotes and write an internal double quote twice. New or explicitly changed text still follows the form's normal trimming and tag rules. Saved custom reminder durations remain selectable; choosing a preset, turning reminders off or removing the deadline applies that new choice.

修改一个字段时，其他字段会保留已接受的导入文本、标签与提醒值。含逗号或双引号的标签会显示为带引号的字段：含逗号的标签用双引号包裹，标签内的双引号写两次。新建或明确修改的文本仍按表单原有规则清理。已保存的自定义提醒分钟数可继续选择；明确选择预设、不提醒或移除截止日期会应用新选择。

Quick add treats a month/day without a year as the nearest valid occurrence today or later; February 29 advances to a valid leap year. Explicit full dates use the same timezone clock-gap policy as the full form. Relative dates use the device's local date when submitted.

快速添加中，不带年份的月日取今天或之后最近的有效日期；2 月 29 日会推进至有效闰年。完整日期与完整表单使用相同的时区跳时规则；“今天”“明天”等按提交时设备本地日期解释。

When an existing later occurrence can be identified, completing an older occurrence does not create another, and Skip explains that a later task already exists. Deleting an intermediate occurrence reconnects only uniquely proven links in the same transaction. An older file that has already lost its relationships may need manual review; the app does not infer their order from edited deadlines or shared series names.

能识别已有后续时，再次完成旧期不会另外创建下一期，“跳过”会说明已有后续。删除中间期时，仅在同一事务中重接唯一可确认的关系。旧文件若已丢失关系，可能需要人工检查；应用不会按修改后的截止日期或相同系列名称推测先后。

For a newly set or changed deadline, a clock gap moves the entered time forward by the gap and a repeated time uses its first occurrence. Check the actual deadline shown after saving. Editing another field without changing date/time preserves an existing instant, including a later fold occurrence. Recurrence advances in the task's stored timezone, independently of the current device timezone. For a date problem, report the entered and displayed date/time, device timezone, task timezone if known and whether the action was creation, editing, completion or skipping; use synthetic data.

When editing on a device in another timezone, the date/time fields show the task's saved clock values. Keeping both fields unchanged retains that task's timezone and exact instant; explicitly changing either field interprets the new deadline in the current device timezone. Calendar dates and the month being viewed stay stable when the device timezone changes; Today and Today Plan follow the device's current local day.

This policy does not bulk-correct old deadlines. If an older version saved an early instant for a skipped clock time, review and change that deadline manually; its original intent cannot be inferred reliably from the stored fields. The next repeat uses the previous occurrence's actual saved wall time, with no separate original-time anchor.

新设置或更改的截止时间遇到时钟跳变时，不存在的时间按跳变量向后顺延，重复时间使用第一次，请检查保存后的实际显示。未更改日期和时间的其他字段编辑保留原时间点，包括第二次重复时间。重复任务按任务保存的时区推进，不受当前设备时区影响。日期问题请用示例数据记录输入与显示的日期/时间、设备时区、已知的任务时区，以及新增、编辑、完成还是跳过操作。

在其他时区的设备上编辑时，日期和时间字段显示任务保存的钟面值。两个字段都不变时保留任务时区和准确时间点；明确修改其中一个字段后，新截止时间按设备当前时区解释。设备切换时区时，日历日期和正在查看的月份保持稳定；“今天”和“今日计划”跟随设备当前本地日期。

此政策不会批量修正旧截止时间。旧版若曾将不存在的钟面时间保存为错误的较早时间点，请核对后手动修改；现有字段无法可靠推断原意。下一期重复沿用上一期实际保存的钟面时间，没有另外保留原始时间锚点。

Relative-date search, Today Plan, overdue membership and statistics are reconsidered on minute checks and visibility changes. An open dialog, inline edit, task-text selection, drag or selected batch work can defer that refresh; finish the interaction and return to the page before troubleshooting a stale view. Browsers can suspend background timers, so this does not guarantee exact-time updates or notifications. The overdue rate uses ongoing, unarchived tasks with deadlines as its denominator, excluding completed and undated tasks.

相对日期搜索、今日计划、逾期范围和统计会在每分钟检查或页面重新可见时重新计算。弹窗、行内编辑、任务文本选择、拖动或已有批量选择期间可能暂缓刷新；排查旧结果前请先完成交互并回到页面。浏览器可能暂停后台计时器，不能据此保证精确时刻更新或提醒。逾期率分母是有截止日期、未归档的进行中任务，不包含已完成或无截止日期任务。

The saved-view × opens a named confirmation with Cancel focused. Cancel, Escape or closing the dialog keeps the view; explicitly deleting it removes only that view, not tasks, and cannot be undone. Export a views JSON first if you need a copy.

保存视图的 × 会显示准确名称并默认聚焦“取消”；取消、Escape 或关闭弹窗会保留视图。明确删除只移除此视图，不删除任务，且无法撤销；需要副本时先导出视图 JSON。

## Report a problem / 问题反馈

Use [GitHub Issues](https://github.com/muquew/Task-Tracer/issues/new/choose) for ordinary bugs and feature requests. Include the app version or source commit if known, browser/OS versions, reproducible steps with synthetic tasks, and expected versus actual behavior. Mention multiple windows, offline use or a recent upgrade when relevant. For text-entry problems, include the operating-system keyboard/input-method name and whether Enter, Escape or arrow keys were choosing a candidate; synthetic DOM event tests do not establish real keyboard behavior. Review screenshots, diagnostic files and error messages before posting; remove personal information and do not upload real task backups, unsaved-draft files or personal view files. Saved searches can reveal private terms even without task contents. There is no published response-time guarantee or paid-support offer.

普通问题和功能建议请使用上述 GitHub Issues 入口。反馈时附上已知的应用版本、浏览器与系统版本、示例数据复现步骤及预期/实际表现；涉及多窗口、离线或升级时请注明。输入问题请补充系统键盘或输入法名称，以及 Enter、Escape、方向键是否正在选择候选文字；DOM 事件测试不代表真实输入法已验证。发布前检查截图、诊断文件和错误信息，删除个人信息，勿上传真实任务备份、未保存草稿文件或个人视图文件；保存的搜索词也可能泄露私密信息。目前没有公布固定响应时限或付费支持承诺。

For suspected security vulnerabilities, follow [SECURITY.md](SECURITY.md). If private reporting is unavailable, request a private channel without publishing exploit details.

疑似安全漏洞请遵循上述安全报告说明；若无法私密报告，只公开请求建立私密渠道，不要发布漏洞细节。
