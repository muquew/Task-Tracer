# Task Tracer 内部代码说明

本文档说明 Task Tracer 的内部结构、运行流程、主要函数职责与维护约定。`index.html` 和 `sw.js` 是会被用户加载的发布文件，应保持精简；详细解释统一维护在这里。

## 发布文件边界

- `index.html`: 单文件 PWA 主应用，包含样式、SVG 图标、HTML 模板和全部前端业务逻辑。
- `sw.js`: Service Worker，负责 App Shell 缓存、语言资源更新策略、静态资源缓存和通知点击回到应用。
- `manifest.json`: PWA manifest。
- `resources/zh-CN.json`、`resources/en.json`: 外置语言文件，避免主 HTML 继续膨胀。

## index.html 结构

1. Head 与主题预加载
   - 设置 PWA 主题色、manifest、favicon。
   - 早期主题脚本在页面渲染前写入 `data-theme`，减少暗色模式刷新闪烁。

2. CSS
   - `:root` 和 `html[data-theme="dark"]` 定义 design tokens。
   - 后续样式按 Header、菜单、控制栏、任务卡片、子任务、弹窗、状态、响应式和动效降级组织。
   - `:focus-visible` 和 `prefers-reduced-motion` 是无障碍基线的一部分。

3. SVG symbols
   - 图标统一以内联 symbol 定义，通过 `<use href="#icon-*">` 复用。
   - 动态创建的 SVG 通过 `createIcon()` 默认标记为装饰性图标。

4. App shell HTML
   - Header 放主题、通知、新建、菜单入口。
   - 主菜单放导出、备份、导入、归档已完成、清除已完成和语言切换。
   - Controls bar 放搜索、项目视图、筛选、排序。
   - View switcher 放列表、日历、时间线和统计视图入口。
   - `#taskList` 是任务列表的唯一渲染容器。
   - `#taskModal` 同时承载任务表单和确认弹窗。
   - `#srStatus` 是给读屏器使用的隐藏 live region。

5. Task template
   - `#task-template` 是任务卡片 DOM 模板。
   - 渲染时由 `createTaskNode()` 克隆，再由 `renderTaskItem()` 填充状态、文本、按钮和子任务。

6. JavaScript runtime
   - `CONFIG` 保存常量。
   - `state` 保存运行时状态。
   - `DOM` 保存缓存后的 DOM 引用。
   - 初始化入口为 `DOMContentLoaded -> initApp()`。

## 数据与状态

- IndexedDB:
  - DB 名称: `TaskTrackerDB`
  - stores: `tasks`、`config`
  - 所有数据库操作通过 `dbActions` 或 `utils.dbOp()` 进入。

- Task 主要字段:
  - `id`: 数字主键。
  - `name`: 任务名。
  - `description`: 描述。
  - `project`: 单个项目名，用作主分组。
  - `tags`: 标签数组，用于跨项目标记和搜索。
  - `dueDate`: UTC ISO 字符串或 `null`。
  - `reminderOffset`: 提前提醒分钟数，`-1` 表示不提醒。
  - `reminderRepeat`: 重复提醒间隔分钟数，`-1` 表示不重复。
  - `snoozedUntil`: 稍后提醒时间点，UTC ISO 字符串或 `null`。
  - `lastReminderAt`: 最近一次成功投递提醒的时间。
  - `subtasks`: 子任务数组，每个子任务有唯一 `id`。
  - `completed`: 完成状态。
  - `completedAt`: 完成时间，用于统计今日完成数和连续完成天数。
  - `repeatType`: 重复类型，取值为 `none`、`daily`、`weekly`、`monthly`、`custom`。
  - `repeatInterval`: 自定义重复天数；非自定义类型统一为 `1`。
  - `repeatSourceId`: 重复链路的源任务 ID。
  - `repeatCreatedFrom`: 当前任务由哪个任务完成后生成。
  - `nextRepeatTaskId`: 当前任务完成后生成的下一期任务 ID。
  - `archived`: 归档状态。
  - `archivedAt`: 归档时间。
  - `createdAt`: 创建时间。
  - `order`: 手动排序权重。

- 运行时状态:
  - `filter`、`sort`、`projectFilter`、`searchQuery`: 当前任务范围条件。
  - `viewMode`: 当前主视图，取值为 `list`、`calendar`、`timeline`、`stats`。
  - `calendarMonthDate`: 日历视图当前月份锚点。
  - `editingTaskId`: 当前编辑任务 ID。
  - `tempSubtasks`、`editingSubtaskIndex`: 弹窗内的临时子任务草稿。
  - `notificationsEnabled`、`notifiedTasks`、`pendingNotificationKeys`: 通知投递状态。
  - `currentLanguage`、`translations`、`dateTimeFormatters`: i18n 与本地化缓存。

- `config` store 常用键:
  - `language`: 当前语言。
  - `notifications_enabled`: 通知开关。
  - `sampleTasksAdded`: 是否已经写入示例任务。
  - `lastBackupAt`: 最近一次点击“立即备份”的时间。

## 项目、标签与搜索规则

- 项目是单值字段，用于主分组和项目视图过滤。全部项目的智能排序视图会调用 `renderGroupedTaskList()` 按项目分组。
- 标签是数组字段，用于给任务增加多个横向标记。
- `matchesTaskSearch(task)` 当前匹配任务名称、描述、项目名和标签。项目和标签都会参与搜索；区别在于项目负责组织层级，标签负责跨项目检索。
- 手动排序只在列表视图、`sort === 'manual'`、`filter === 'all'`、`projectFilter === 'all'` 且无搜索词时启用，避免局部视图排序写回全局顺序造成误解。

## 重复任务、日期视图与统计

- 重复任务由 `repeatType` 和 `repeatInterval` 表示。用户完成一个重复任务时，`toggleTaskComplete()` 会保留当前完成记录，并通过 `createNextRepeatTask()` 生成下一期。
- 每月重复使用 `addMonthsClamped()` 处理月底日期，避免 1 月 31 日这类日期溢出到错误月份。
- 日历视图使用 `calendarMonthDate` 渲染 42 个日期格，任务按钮点击后进入编辑弹窗。
- 时间线视图按本地日期分组，继续复用任务卡片模板，因此任务按钮、子任务和归档逻辑保持一致。
- 统计视图使用 `getStatsScopeTasks()`，只受项目和搜索范围影响，不受状态筛选影响。完成率按非归档任务计算，逾期率按有截止日期任务计算，连续完成天数基于 `completedAt`。

## 导入、导出与备份边界

- 导出由 `exportTasks()` 进入，下载当前任务 JSON，适合迁移、查看或手动保存。
- 导入由 `importTasks(file)` 进入，会先构建预览，展示导入数量、同名重复项和替换影响，确认后通过 `replaceAllTasks()` 全量替换当前任务。
- 备份由 `backupTasks()` 进入，下载带 `schema` 和 `versionNotes` 的版本化快照，并把时间写入 `lastBackupAt`。
- `scheduleBackupReminder()` 根据 `lastBackupAt` 和任务数量决定是否显示最近备份提醒。

## 初始化流程

`initApp()` 的顺序很重要：

1. `cacheDOM()` 缓存节点。
2. `loadTranslations()` 加载语言文件。
3. `createLangButtons()` 创建语言菜单项。
4. `initDB()` 初始化 IndexedDB。
5. `loadSettings()` 恢复语言、通知和已提醒签名。
6. `initLanguage()` 同步 `lang`、`dir` 和页面文案。
7. `loadNormalizedTasks()` 读取任务并修复历史任务字段和子任务重复 ID。
8. 必要时 `addSampleTasks()` 添加示例。
9. `bindEvents()` 绑定事件。
10. `renderTaskList()` 首次渲染。
11. `startProgressTimer()` 启动倒计时刷新。
12. `scheduleBackupReminder()` 根据最近备份时间决定是否提示备份。

## 主要函数清单

### DOM 与初始化

- `cacheDOM()`: 缓存常用 DOM 引用。
- `initApp()`: 应用总入口。
- `loadSettings()`: 恢复配置。
- `restoreLanguageSetting()`: 恢复或解析首选语言。
- `restoreNotificationSetting(savedNotify)`: 恢复通知开关。
- `restoreNotifiedTasks()`: 恢复已提醒任务签名。

### 语言与 i18n

- `loadTranslations()`: 拉取并扁平化语言资源。
- `flattenTranslations(source, prefix, target)`: 将嵌套 JSON 展平为点分 key。
- `validateTranslations()`: 运行时检查语言 key 是否对齐。
- `createLangButtons()`: 创建语言菜单按钮。
- `initLanguage()`: 同步语言按钮、`html.lang`、`html.dir` 和文案。
- `getLanguageDirection(code)`: 返回语言方向。
- `switchLanguage(code)`: 切换语言并持久化。
- `utils.applyTranslations()`: 应用 `data-i18n*` 属性。
- `utils.translate(key)`: 当前语言优先、默认语言兜底的翻译读取。

### 事件绑定

- `bindEvents()`: 统一绑定入口。
- `bindGlobalEvents()`: 全局键盘、滚动、可见性事件。
- `bindDialogEvents()`: 弹窗打开、关闭、提交事件。
- `bindFormEvents()`: 表单联动。
- `bindSearchEvents()`: 搜索、项目视图和清除完成任务入口。
- `bindViewEvents()`: 主视图切换入口。
- `setViewMode(viewMode)`: 切换列表、日历、时间线或统计视图。
- `syncViewSwitcher()`: 同步视图按钮选中态。
- `bindNotificationEvents()`: 通知按钮。
- `bindMenuEvents()`: 主菜单、语言子菜单、导入、导出、备份和归档入口。
- `bindTaskListEvents()`: 任务列表委托点击。
- `bindSubtaskInputEvents()`: 子任务输入。
- `bindSubtaskPreviewEvents()`: 子任务草稿编辑。

### 键盘与无障碍

- `handleKeyboardShortcuts(e)`: 全局快捷键。
- `isDialogOpen()`: 判断弹窗是否打开。
- `trapDialogFocus(e)`: 弹窗焦点循环。
- `getFocusableDialogElements()`: 获取弹窗可聚焦元素。
- `utils.announce(msg)`: 写入 `#srStatus` 让读屏器播报。
- `handleTaskReorderKeydown(e)`: 手动排序模式下的键盘排序。
- `announceTaskReorderMove(item)`: 播报移动结果。
- `announceTaskReorderBoundary(item, key)`: 播报已经到边界。

### 任务 CRUD

- `handleTaskSave(e)`: 保存新建或编辑任务。
- `buildTaskPayloadFromForm()`: 从表单组装任务 payload。
- `createTaskRecord(taskPayload)`: 创建新任务记录。
- `mergeTaskPayload(original, taskPayload)`: 合并编辑结果。
- `getTaskById(id)`: 从 `state.tasks` 查找任务。
- `getNextTaskOrder()`: 新任务默认排序权重。
- `refreshTasks()`: 重新读取并渲染任务。
- `editTask(id)`: 打开编辑弹窗。
- `deleteTask(id)`: 删除确认。
- `toggleTaskComplete(id)`: 切换任务完成状态。
- `shouldCreateNextRepeatTask(task)`: 判断完成后是否需要创建下一期重复任务。
- `createNextRepeatTask(task)`: 克隆当前任务并推进截止日期，生成下一期。
- `resetRepeatedSubtasks(subtasks)`: 复制子任务并重置完成状态。
- `calculateNextRepeatDueDate(iso, rule)`: 根据重复规则计算下一期截止时间。
- `addMonthsClamped(date, months)`: 月重复时按月份天数夹取日期。
- `handleClearCompleted()`: 批量清除已完成任务。
- `handleArchiveCompleted()`: 批量归档未归档的已完成任务。
- `toggleTaskArchive(id)`: 单任务归档和从归档恢复。
- `normalizeTaskProject(value)`: 规范化项目名。
- `parseTagsInput(value)`: 将逗号分隔的标签输入转换为数组。
- `normalizeTaskTags(tags)`: 去空、去 `#`、去重并规范化标签。
- `normalizeTaskRepeatType(value)`: 规范化重复类型。
- `normalizeTaskRepeatInterval(type, value)`: 规范化自定义重复天数。
- `getTaskRepeatRule(task)`: 读取任务重复规则。
- `hasTaskRepeat(task)`: 判断任务是否启用重复。

### 子任务

- `cloneSubtasks(subtasks)`: 浅克隆子任务。
- `cloneSubtasksWithUniqueIds(subtasks)`: 克隆并保证 ID 唯一。
- `createUniqueNumericId(usedIds)`: 生成唯一数字 ID。
- `normalizeUniqueNumericId(value, usedIds)`: 保留合法唯一 ID，否则生成新 ID。
- `createUniqueSubtaskId(subtasks)`: 新增草稿子任务时生成 ID。
- `normalizeTaskRecords(tasks)`: 读取历史数据时修复任务字段、归档字段、提醒字段和子任务 ID。
- `normalizeSubtasksForTask(subtasks)`: 单任务内子任务 ID 去重。
- `handleAddSubtaskInput()`: 添加草稿子任务。
- `toggleSubtaskComplete(taskId, subtaskId)`: 切换子任务完成状态。
- `removeTempSubtask(index)`: 删除草稿子任务。
- `editTempSubtask(index)`: 进入草稿子任务编辑。
- `saveEditSubtask(inputEl)`: 保存草稿编辑。

### 通知

- `toggleNotifications()`: 切换通知总开关。
- `requestNotificationPermission()`: 请求浏览器通知权限。
- `setNotificationsEnabled(enabled)`: 持久化通知开关。
- `supportsNotifications()`: 判断通知能力。
- `hasNotificationPermission()`: 判断权限状态。
- `updateNotificationBtnUI()`: 更新通知按钮状态。
- `checkNotifications()`: 定时扫描待提醒任务。
- `getTaskReminderDueState(task, timeLeft, offset)`: 判断普通提醒、稍后提醒或错过提醒是否到期。
- `shouldDeliverTaskReminder(task, notificationKey, dueState)`: 根据重复提醒与已投递状态判断是否应投递。
- `deliverTaskReminder(task, notificationKey, dueState)`: 发送提醒并写回投递时间。
- `snoozeTaskReminder(id)`: 将任务提醒延后到默认稍后提醒时间。
- `getTaskReminderOffset(task)`: 读取任务提醒偏移。
- `getTaskReminderRepeat(task)`: 读取重复提醒间隔。
- `getTaskNotificationKey(task, offset)`: 生成提醒签名。
- `markReminderIconNotified(taskId)`: 本地更新提醒图标状态。
- `sendNotification(body)`: 发送提醒并返回是否成功。
- `showServiceWorkerNotification(title, options)`: 通过 SW 通知。
- `showWindowNotification(title, options)`: 普通 Notification 兜底。
- `playNotificationFeedback()`: 播放提示音。
- `vibrateNotification()`: 移动端震动反馈。

### 渲染

- `renderTaskList()`: 根据状态渲染列表。
- `getVisibleTasks()`: 过滤并排序任务。
- `isTaskVisible(task)`: 判断任务是否匹配当前筛选。
- `matchesTaskSearch(task)`: 搜索匹配。
- `matchesTaskProject(task)`: 项目视图匹配。
- `renderProjectFilterOptions()`: 根据任务项目生成项目下拉选项。
- `renderGroupedTaskList(tasks)`: 全部项目智能视图下按项目分组渲染。
- `renderCalendarView(tasks)`: 渲染月份日历视图。
- `createCalendarShell(tasks)`: 生成日历容器。
- `createCalendarGrid(tasks)`: 生成星期标题和日期格。
- `createCalendarTaskButton(task)`: 生成日历中的任务按钮。
- `shiftCalendarMonth(delta)`: 切换日历月份。
- `renderTimelineView(tasks)`: 渲染按日期分组的时间线视图。
- `createTimelineGroup(key, tasks)`: 生成单个日期分组。
- `renderStatsView(tasks)`: 渲染统计视图。
- `calculateTaskStats(tasks)`: 计算完成率、逾期率、今日完成和连续完成天数。
- `calculateCompletionStreak(tasks)`: 基于 `completedAt` 计算连续完成天数。
- `getStatsScopeTasks()`: 统计视图使用的任务范围。
- `patchTaskList(tasks)`: 增量更新列表。
- `createTaskNode(task)`: 克隆任务模板。
- `renderTaskItem(el, task)`: 单任务渲染总入口。
- `getTaskRenderStatus(task, t)`: 获取任务状态对象。
- `renderTaskHeader(el, task, statusObj, t)`: 标题、提醒、截止日期。
- `renderTaskDescription(el, task)`: 描述区域。
- `renderTaskMeta(el, task)`: 渲染项目、标签和重复规则 chip。
- `renderTaskProgress(el, task, statusObj)`: 进度条。
- `renderTaskStatus(el, task, statusObj, timeLeft)`: 状态文字。
- `renderReminderIcon(el, task)`: 提醒图标。
- `renderTaskActionTitles(el, task, t)`: 操作按钮标签。
- `renderTaskToggleButton(button, completed)`: 完成/恢复图标切换。
- `renderTaskSnoozeButton(button, task, t)`: 根据提醒状态显示稍后提醒按钮。
- `renderTaskArchiveButton(button, task, t)`: 根据完成/归档状态显示归档或恢复按钮。
- `renderTaskDragHandle(el)`: 手动排序手柄。
- `renderSubtaskList(el, task)`: 卡片内子任务列表。
- `renderSubtaskPreview()`: 弹窗内草稿子任务列表。
- `getEmptyStateHTML(t)`: 无任务空状态。
- `getEmptyMatchHTML(t)`: 搜索/筛选无结果空状态。

### 弹窗

- `openModal(editingTask)`: 打开新建/编辑弹窗。
- `prepareEditTaskForm(editingTask)`: 填充编辑表单。
- `prepareNewTaskForm()`: 填充新建表单。
- `setDialogFormLabels(titleKey, submitKey)`: 设置标题和提交按钮。
- `setDeadlineControls({ enabled, date, time, reminderOffset, reminderRepeat, repeatType, repeatInterval })`: 截止日期、提醒、重复提醒和重复任务控件联动。
- `syncReminderRepeatControl()`: 根据截止日期和提醒设置启用或禁用重复提醒。
- `syncRepeatControls()`: 根据截止日期和重复类型启用或禁用重复任务控件。
- `closeDialog()`: 关闭并清理弹窗。
- `resetDialogToFormMode()`: 从确认模式恢复表单模式。
- `utils.confirm(title, msg, onConfirm)`: 复用任务弹窗显示确认流程。
- `setConfirmMessageContent(el, msg)`: 让确认弹窗同时支持文本和 DOM 内容。
- `clearConfirmHandler()`: 移除确认按钮的一次性 handler。

### 数据库与工具

- `dbActions.init()`: 打开 IndexedDB 并创建 object stores。
- `dbActions.getAllTasks()`: 读取全部任务。
- `dbActions.addTask(task)`: 新增任务。
- `dbActions.updateTask(task)`: 更新单任务。
- `dbActions.deleteTask(id)`: 删除任务。
- `dbActions.updateTasks(tasks)`: 批量写任务。
- `dbActions.deleteTasks(ids)`: 批量删任务。
- `dbActions.replaceAllTasks(tasks)`: 导入时替换全量任务。
- `dbActions.writeTaskTransaction(write, abortMessage)`: 统一写事务。
- `utils.dbOp(storeName, mode, callback)`: IndexedDB 单操作封装。
- `utils.debounce(func, delay)`: 防抖。
- `utils.notify(msg, type)`: 页面 toast。
- `utils.applyTheme(theme)`: 应用主题并同步 manifest/theme-color。
- `utils.toggleTheme()`: 主题切换动画。
- `utils.localToUTC(d, t)`: 本地日期时间转 UTC ISO。
- `utils.utcToLocal(iso)`: UTC ISO 转本地 Date。
- `utils.formatDateInputValue(date)`: `YYYY-MM-DD`。
- `utils.formatTimeInputValue(date)`: `HH:mm`。
- `utils.dateToStoredISO(date)`: Date 转存储 ISO。
- `utils.calculateTimeLeft(iso)`: 剩余分钟。
- `utils.formatDate(iso)`: 本地化日期时间。
- `utils.formatTime(min)`: 本地化剩余/逾期时间。
- `utils.getStatus(min)`: 根据剩余时间计算状态。
- `utils.sortTasks(list)`: 当前排序策略。

### 菜单、下拉与任务动作

- `setupDropdowns()`: 初始化筛选/排序下拉。
- `bindDropdownToggle(dropdown)`: 下拉按钮事件。
- `toggleDropdown(dropdown)`: 打开或关闭下拉。
- `handleFilterDropdownClick(e)`: 筛选选项。
- `handleSortDropdownClick(e)`: 排序选项。
- `closeDropdownsOnOutsideClick(e)`: 外部点击关闭。
- `syncDropdowns()`: 同步下拉选中态和按钮文字。
- `updateDropdownUI(container, selected, btn)`: 更新选项 `selected` 与 `aria-selected`。
- `toggleMenu(menu, btn)`: 主菜单开关。
- `closeMenu()`: 关闭主菜单和语言子菜单。
- `openPopover(container, btn)`、`closePopover(container, btn)`: 通用浮层状态。
- `handleTaskListClick(e)`: 任务列表点击委托入口。
- `handleCalendarActionClick(e)`: 日历月份导航入口。
- `handleCalendarTaskClick(e)`: 日历任务点击后打开编辑。
- `runTaskAction(action, taskId)`: 执行完成、稍后提醒、归档/恢复归档、编辑、删除。
- `getTaskIdFromElement(el)`: 从 DOM 追溯任务 ID。

### 拖拽与排序

- `setupDragAndDrop()`: 注册鼠标、触摸、键盘排序事件。
- `moveTaskElementByKeyboard(item, key)`: 键盘移动 DOM 节点。
- `handleTaskDragStart(e, dragState)`: 鼠标拖拽开始。
- `handleTaskDragOver(e, dragState)`: 鼠标拖拽移动。
- `handleTaskTouchStart(e, dragState)`: 触摸拖拽开始。
- `handleTaskTouchMove(e, dragState)`: 触摸拖拽移动。
- `finishTaskDrag(dragState, activeClass)`: 拖拽结束并保存。
- `updateDragPosition(dragState, y)`: 更新拖拽位置。
- `moveDraggedTask(dragState, y)`: 移动 DOM 节点。
- `handleEdgeScroll(dragState, y)`: 贴边自动滚动。
- `setAutoScrollSpeed(dragState, speed)`: 设置滚动速度。
- `performAutoScroll(dragState)`: 执行滚动循环。
- `stopAutoScroll(dragState)`: 停止滚动。
- `canReorderTasks()`: 是否处于手动排序。
- `getDragAfterElement(container, y)`: 计算拖拽插入点。
- `saveNewOrder()`: 将 DOM 顺序写回任务 `order`。

### 导入、导出、备份、示例与定时器

- `startProgressTimer()`: 启动定时刷新。
- `refreshTaskTimers()`: 局部刷新倒计时和状态样式。
- `handleVisibilityChange()`: 页面恢复时刷新。
- `exportTasks()`: 导出任务 JSON。
- `backupTasks()`: 下载版本化本地备份。
- `downloadTaskData(mode)`: 导出和备份的统一下载入口。
- `createTaskDataPayload(mode, date, tasks)`: 构建带版本说明的数据文件。
- `createTaskDataFilename(mode, date)`: 生成导出或备份文件名。
- `scheduleBackupReminder()`: 根据最近备份时间提示备份。
- `importTasks(file)`: 读取 JSON、展示导入预览并确认替换。
- `buildImportPreview(importedTasks)`: 统计导入数量、当前替换影响和重复项。
- `getImportDuplicateNames(importedTasks)`: 统计导入文件内或与当前任务重名的任务。
- `createImportPreviewContent(preview)`: 生成确认弹窗中的导入预览 DOM。
- `normalizeImportedTasks(rawTasks)`: 导入任务规范化。
- `normalizeImportedTask(rawTask, index, normalizeId)`: 单任务规范化。
- `normalizeImportedSubtasks(rawSubtasks)`: 导入子任务规范化。
- `normalizeStoredDate(value)`: 日期字段校验。
- `addSampleTasks()`: 首次启动示例数据。

## Service Worker 结构

- `CACHE_NAME`: 缓存版本。修改运行时代码或缓存资源时应递增。
- `ASSETS_TO_CACHE`: 预缓存 App Shell、manifest、语言资源和核心图标。
- `install`: 打开缓存并预缓存资源，完成后 `skipWaiting()`。
- `fetch`: 同源 GET 请求分三类处理：
  - 导航和 App Shell: `networkFirst(request, './index.html')`
  - 语言资源: `networkFirst(request)`
  - 其他静态资源: `cacheFirst(request)`
- `notificationclick`: 点击通知时聚焦已有窗口或打开首页。
- `activate`: 删除旧缓存并 `clients.claim()`。
- `isAppShellRequest(url)`: 判断首页请求。
- `networkFirst(request, fallbackUrl)`: 网络优先，失败时回退缓存。
- `cacheFirst(request)`: 缓存优先，未命中时请求网络。
- `cacheResponse(request, response)`: 写入有效响应副本。

## 维护约定

- 用户加载的运行时代码保持无注释；说明写在本文档。
- 修改语言文件内容时，同步更新 `CONFIG.I18N.RESOURCE_VERSION` 和 `sw.js` 中语言资源 query。
- 修改缓存资源或运行时代码时，同步递增 `CACHE_NAME`。
- 新增文案必须同时更新 `zh-CN.json` 和 `en.json`，并通过 `tools/validate_static.py`。
- 新增交互控件必须有可访问名称，键盘路径要纳入 `tools/smoke_playwright.py`。
- 新增任务字段要同步导入规范化、导出格式和内部文档。
