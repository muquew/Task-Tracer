# Task Tracer 内部代码说明

本文档说明 Task Tracer 的内部结构、运行流程、主要函数职责与维护约定。`index.html` 和 `sw.js` 是会被用户加载的发布文件，应保持精简；详细解释统一维护在这里。

## 发布文件边界

- `index.html`: 单文件 PWA 主应用，包含样式、SVG 图标、HTML 模板和全部前端业务逻辑。
- `sw.js`: Service Worker，负责 App Shell 缓存、语言资源更新策略、静态资源缓存和通知点击回到应用。
- `manifest.json`: PWA manifest。
- `resources/zh-CN.json`、`resources/en.json`: 外置语言文件，避免主 HTML 继续膨胀。
- `docs/accessibility-i18n-audit.md`: 无障碍、键盘、读屏器语义和 i18n 审计基线。

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
   - Header 放主题、通知、今日计划、新建和菜单入口。
   - 主菜单放导出/备份、导入、归档已完成、清除已完成和语言切换。
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
- 所有数据库操作通过 `dbActions` 或 `utils.dbOp()` 进入；单请求操作必须等 IndexedDB transaction `complete` 后才视为成功。

- Task 主要字段:
  - `id`: 数字主键。
  - `name`: 任务名。
  - `description`: 描述。
  - `project`: 单个项目名，用作主分组。
  - `tags`: 标签数组，用于跨项目标记和搜索。
  - `dueLocalDate`: 任务时区下的截止日期，格式为 `YYYY-MM-DD`，无截止日期时为 `null`。
  - `dueLocalTime`: 任务时区下的截止时间，格式为 `HH:mm`，无截止日期时为 `null`。
  - `dueAt`: 截止日期对应的真实时间点 ISO 字符串，用于提醒、逾期和剩余时间计算。
  - `dueDate`: 兼容字段，当前与 `dueAt` 保持一致；旧版数据会在加载时迁移。
  - `dueTimeZone`: 该截止时间所属的 IANA 时区名称。
  - `reminderOffset`: 提前提醒分钟数，`-1` 表示不提醒。
  - `reminderRepeat`: 重复提醒间隔分钟数，`-1` 表示不重复。
  - `snoozedUntil`: 稍后提醒时间点，UTC ISO 字符串或 `null`。
  - `lastReminderAt`: 最近一次成功投递提醒的时间。
  - `subtasks`: 子任务数组，每个子任务有唯一 `id`。
  - `completed`: 完成状态。
  - `completedAt`: 完成时间，用于统计今日完成数和连续完成天数。
  - `repeatType`: 重复类型，取值为 `none`、`daily`、`weekly`、`weekly-days`、`monthly`、`monthly-last`、`custom`。
  - `repeatInterval`: 自定义重复天数；非自定义类型统一为 `1`。
  - `repeatWeekdays`: 指定星期重复使用的星期数组，采用浏览器 `Date.getDay()` 数值，`0` 为周日。
  - `repeatPaused`: 是否暂停重复；暂停后完成任务不会生成下一期。
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
  - `commandPaletteItems`、`commandPaletteActiveIndex`、`commandPaletteReturnFocus`: 命令面板候选项、当前选中项和关闭后的焦点恢复目标。
  - `currentLanguage`、`translations`、`dateTimeFormatters`: i18n 与本地化缓存。
  - `storageAvailable`、`storageError`、`storageFallbackTasks`、`storageFailureEventsBound`: 本地存储可用性、失败原因、降级态内存快照和降级态事件绑定状态。

- `config` store 常用键:
  - `language`: 当前语言。
  - `notifications_enabled`: 通知开关。
  - `sampleTasksAdded`: 是否已经写入示例任务。
  - `lastBackupAt`: 最近一次点击“导出/备份”的时间。
  - `__task_tracer_storage_probe__`: 启动探针临时键，写入后立即删除，用于验证 IndexedDB 真的可写。

## 项目、标签与搜索规则

- 项目是单值字段，用于主分组和项目视图过滤。全部项目的智能排序视图会调用 `renderGroupedTaskList()` 按项目分组。
- 标签是数组字段，用于给任务增加多个横向标记。
- `matchesTaskSearch(task)` 当前匹配任务名称、描述、项目名和标签。项目和标签都会参与搜索；区别在于项目负责组织层级，标签负责跨项目检索。
- 手动排序只在列表视图、`sort === 'manual'` 且无搜索词时启用。局部筛选或项目视图下拖拽时，`mergeVisibleManualOrder()` 只调整当前可见任务在全局手动顺序中的相对位置。

## 日期语义、重复任务、日期视图与统计

- 截止日期以 `dueAt` 作为真实时间点来源，并使用 `dueTimeZone` 还原任务时区下的日期和时间。界面展示、日历和时间线使用按任务时区还原后的日期；提醒、逾期和剩余时间使用 `dueAt`。
- 编辑任务时，如果截止日期和时间没有变化，会保留原任务的 `dueTimeZone`；如果用户修改日期或时间，则按当前浏览器时区重新生成 `dueAt`。
- 旧版 `dueDate` 以本地墙上时间编码到 ISO 字符串中，`normalizeTaskDueFields()` 会通过 `legacyStoredDueDateToLocalDate()` 保留原先显示的日期时间，再写入新的 `dueLocalDate`、`dueLocalTime` 和 `dueAt`。
- `completedAt`、`archivedAt`、`createdAt`、`snoozedUntil` 和 `lastReminderAt` 都是真实时间点，不能走旧版截止日期转换逻辑。
- 重复任务由 `repeatType`、`repeatInterval`、`repeatWeekdays` 和 `repeatPaused` 表示。用户完成一个未暂停的重复任务时，`toggleTaskComplete()` 会保留当前完成记录，并通过 `createNextRepeatTask()` 生成下一期。
- 指定星期重复使用 `getNextWeeklyRepeatDate()` 在已选星期中寻找下一个日期；每月最后一天使用 `getLastDayOfNextMonth()`。
- 卡片上的“跳过本次”调用 `skipRepeatOccurrence()`，直接把当前任务推进到下一期，不标记完成，也不创建完成记录。
- 每月重复使用 `addMonthsClamped()` 处理月底日期，避免 1 月 31 日这类日期溢出到错误月份。
- 日历视图使用 `calendarMonthDate` 和浏览器 `Date` 计算月份首日、星期偏移与 42 个日期格，任务按钮点击后进入编辑弹窗。
- 时间线视图按本地日期分组，继续复用任务卡片模板，因此任务按钮、子任务和归档逻辑保持一致。
- 统计视图使用 `getStatsScopeTasks()`，只受项目和搜索范围影响，不受主状态筛选影响；状态搜索会复用列表视图的归档隔离规则，只有显式 `status:archived` 才会纳入归档任务。完成率按当前范围任务计算，逾期率按未归档且有截止日期的任务计算，连续完成天数基于 `completedAt`，并单独展示归档数量。

## 导入与导出/备份边界

- 导入由 `importTasks(file)` 进入，会先经过 `prepareImportPayload()`，再构建预览，展示恢复检查清单、导入差异、导入数量、文件内同名重复、重复任务 ID、与当前任务同名项和替换影响。默认确认后通过 `replaceAllTasks()` 全量替换当前任务；如果替换前已有任务，会先下载 `pre-import-backup` 快照并停留在确认弹窗，等待用户第二次确认。完整性校验失败且用户仍选择替换时，也会先停留并要求显式风险确认。开启合并模式后会读取冲突策略，并通过 `mergeImportedTasks()` 合并、跳过或替换同名本地任务。
- 导出/备份由 `backupTasks()` 进入，下载带 `schema`、`versionNotes`、`exportId` 和 `checksum` 的版本化快照，并把时间写入 `lastBackupAt`。
- 紧急备份由 `downloadEmergencyBackup()` 进入，仅在运行中存储故障且 `storageFallbackTasks` 仍有内存快照时开放；文件会标记 `type: emergency-backup` 和 `schema.storage: memory-fallback`，便于后续恢复时识别来源。
- `scheduleBackupReminder()` 根据 `lastBackupAt` 和任务数量决定是否显示最近备份提醒。
- `ensureStorageAvailable()` 是写入口保护层；当 IndexedDB 不可用时，新建、编辑、删除、完成、拖拽排序、导入、常规导出/备份、归档和通知开关都会被暂停，只有当前页面内存快照的紧急备份不经过 IndexedDB。

## 初始化流程

`initApp()` 的顺序很重要：

1. `cacheDOM()` 缓存节点。
2. `loadTranslations()` 加载语言文件。
3. `createLangButtons()` 创建语言菜单项。
4. `initializeStorageOrFallback()` 单独处理存储初始化；内部调用 `initPersistentStorage()` 初始化 IndexedDB，并通过 `verifyPersistentStorage()` 执行写入/删除探针。
5. `loadSettings()` 恢复语言、通知和已提醒签名。
6. `initLanguage()` 同步 `lang`、`dir` 和页面文案。
7. `loadNormalizedTasks()` 读取任务并修复历史任务字段和子任务重复 ID。
8. 必要时 `addSampleTasks()` 添加示例。
9. `bindEvents()` 绑定事件。
10. `renderTaskList()` 首次渲染。
11. `startProgressTimer()` 启动倒计时刷新。
12. `scheduleBackupReminder()` 根据最近备份时间决定是否提示备份。

如果 IndexedDB 被禁用、浏览器隐私模式阻止本地数据库，或写入探针失败，`initializeStorageOrFallback()` 会调用 `handleStorageUnavailable()` 进入保护模式：显示存储不可用横幅和任务区错误态，禁用任务写入口，只保留主题切换、重试检测，以及在内存快照存在时可用的紧急备份。非存储阶段的初始化错误不会被包装成本地存储不可用。

## 主要函数清单

### DOM 与初始化

- `cacheDOM()`: 缓存常用 DOM 引用。
- `initApp()`: 应用总入口。
- `initializeStorageOrFallback()`: 只包住存储初始化阶段，决定进入正常模式还是存储不可用保护模式。
- `initPersistentStorage()`: 初始化 IndexedDB 并执行存储写入探针。
- `verifyPersistentStorage()`: 向 `config` store 写入临时键并删除，确认数据库可写。
- `handleStorageUnavailable(error)`: 切换到存储不可用保护模式。
- `renderStorageUnavailableState()`: 渲染存储不可用的任务区状态。
- `syncStorageAvailabilityUI()`: 同步横幅、按钮禁用态和 `aria-disabled`。
- `ensureStorageAvailable()`: 写操作统一守卫。
- `captureStorageFallbackSnapshot()`: 在进入运行时存储故障保护模式前复制当前任务内存快照。
- `safeGetStorageItem()`、`safeSetStorageItem()`、`safeRemoveStorageItem()`: 包装 `localStorage`/`sessionStorage`，避免隐私模式抛错导致启动中断。
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
- `bindSavedViewEvents()`: 保存智能视图条的保存、打开和删除入口。
- `bindFocusModeEvents()`: 顶部今日计划按钮和专注模式退出入口。
- `bindBatchModeEvents()`: 批量选择和批量任务操作入口。
- `setViewMode(viewMode)`: 切换列表、日历、时间线或统计视图。
- `syncViewSwitcher()`: 同步视图按钮选中态。
- `bindNotificationEvents()`: 通知按钮和通知条撤销按钮。
- `bindMenuEvents()`: 主菜单、语言子菜单、导入、导出/备份和归档入口。
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
- `createNextRepeatTaskWithUsedIds(task, usedIds)`: 批量完成重复任务时复用 ID 集合生成下一期。
- `resetRepeatedSubtasks(subtasks)`: 复制子任务并重置完成状态。
- `calculateNextRepeatDueDate(iso, rule)`: 根据重复规则计算下一期截止时间。
- `addMonthsClamped(date, months)`: 月重复时按月份天数夹取日期。
- `handleClearCompleted()`: 批量清除已完成任务。
- `handleArchiveCompleted()`: 批量归档未归档的已完成任务。
- `toggleTaskArchive(id)`: 单任务归档和从归档恢复。
- `toggleTaskFocus(id)`: 将单任务加入或移出今日计划。
- `enterFocusMode()` / `exitFocusMode()`: 进入或退出今日计划专注模式。
- `setBatchMode(enabled)`: 打开或关闭批量操作模式。
- `runBatchTaskUpdate(action)`: 批量加入今日计划、完成、归档或删除。
- `buildBatchCompleteTasks(tasks, completedAt)`: 批量完成时生成待写入任务，并为重复任务创建下一期。
- `captureUndoSnapshot()` / `registerUndoSnapshot(label, beforeTasks)` / `performUndo()`: 捕获任务快照、登记撤销动作并恢复最近一次任务写入前状态。
- `normalizeTaskProject(value)`: 规范化项目名。
- `parseTagsInput(value)`: 将逗号分隔的标签输入转换为数组。
- `normalizeTaskTags(tags)`: 去空、去 `#`、去重并规范化标签。
- `normalizeTaskRepeatType(value)`: 规范化重复类型。
- `normalizeTaskRepeatInterval(type, value)`: 规范化自定义重复天数。
- `getTaskRepeatRule(task)`: 读取任务重复规则。
- `hasTaskRepeat(task)`: 判断任务是否启用重复。
- `getTaskDueDateKey(task)`: 按任务 `dueTimeZone` 还原用于展示和日期分组的日期键。
- `getTaskDueTimeValue(task)`: 按任务 `dueTimeZone` 还原用于表单和重复任务推进的时间值。
- `getTaskDueInstant(task)`: 读取真实截止时间点。

### 子任务

- `cloneSubtasks(subtasks)`: 浅克隆子任务。
- `cloneSubtasksWithUniqueIds(subtasks)`: 克隆并保证 ID 唯一。
- `createUniqueNumericId(usedIds)`: 生成唯一数字 ID。
- `normalizeUniqueNumericId(value, usedIds)`: 保留合法唯一 ID，否则生成新 ID。
- `createUniqueSubtaskId(subtasks)`: 新增草稿子任务时生成 ID。
- `normalizeTaskRecords(tasks)`: 读取历史数据时修复任务字段、完成/归档布尔值、提醒字段、今日计划日期和子任务 ID。
- `normalizeSubtasksForTask(subtasks)`: 单任务内子任务 ID 去重，并修复子任务完成状态布尔值。
- `normalizeBoolean(value, defaultValue = false)`: 兼容旧数据里的布尔字符串和 0/1 数值。
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
- `normalizeSavedViews(rawViews)`: 读取并限制保存的智能视图配置。
- `saveSmartView(name)`: 将当前搜索、筛选、排序和视图保存为智能视图。
- `renderSavedViews()`: 渲染保存的智能视图条。
- `applySavedView(id)`: 恢复保存的搜索、项目、筛选、排序和视图状态。
- `deleteSavedView(id)`: 删除保存的智能视图并持久化。
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
- `renderTaskFocusButton(button, task, t)`: 今日计划按钮状态。
- `renderTaskToggleButton(button, completed)`: 完成/恢复图标切换。
- `renderTaskSnoozeButton(button, task, t)`: 根据提醒状态显示稍后提醒按钮。
- `renderTaskArchiveButton(button, task, t)`: 根据完成/归档状态显示归档或恢复按钮。
- `renderTaskDragHandle(el)`: 手动排序手柄。
- `renderTaskSelectionControl(el, task)`: 批量模式下的任务选择框。
- `renderSubtaskList(el, task)`: 卡片内子任务列表。
- `renderSubtaskPreview()`: 弹窗内草稿子任务列表。
- `getEmptyStateHTML(t)`: 无任务空状态。
- `getEmptyMatchHTML(t)`: 搜索/筛选无结果空状态。
- `getEmptyFocusHTML(t)`: 今日计划为空时的空状态。

### 弹窗

- `openModal(editingTask)`: 打开新建/编辑弹窗。
- `prepareEditTaskForm(editingTask)`: 填充编辑表单。
- `prepareNewTaskForm()`: 填充新建表单。
- `setDialogFormLabels(titleKey, submitKey)`: 设置标题和提交按钮。
- `setDeadlineControls({ enabled, date, time, reminderOffset, reminderRepeat, repeatType, repeatInterval, repeatWeekdays, repeatPaused })`: 截止日期、提醒、重复提醒和重复任务控件联动。
- `syncReminderRepeatControl()`: 根据截止日期和提醒设置启用或禁用重复提醒。
- `syncRepeatControls()`: 根据截止日期和重复类型启用或禁用重复任务控件。
- `openCommandPalette()` / `closeCommandPalette()`: 打开或关闭命令面板，并处理焦点恢复。
- `renderCommandPalette()` / `getCommandPaletteItems()`: 根据当前任务、视图、项目、智能视图、今日计划、批量模式和撤销状态生成命令候选项。
- `executeCommandPaletteItem(index)`: 执行当前命令，覆盖新建任务、快速添加、搜索、视图切换、智能视图、今日计划、批量操作、撤销、导出/备份和项目切换。
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
- `utils.notify(msg, type, options)`: 页面 toast，可显示撤销动作按钮。
- `utils.applyTheme(theme)`: 应用主题并同步 manifest/theme-color。
- `utils.toggleTheme()`: 主题切换动画。
- `utils.formatDateInputValue(date)`: `YYYY-MM-DD`。
- `utils.formatTimeInputValue(date)`: `HH:mm`。
- `utils.localDateTimeToInstantISO(dateValue, timeValue, timeZoneName)`: 指定时区下的日期时间转真实时间点 ISO。
- `utils.formatDateObject(date, timeZone)`: 本地化格式化 `Date` 对象，可指定展示时区。
- `utils.formatDate(iso, timeZone)`: 本地化格式化真实时间点 ISO，可指定展示时区。
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
- `runTaskAction(action, taskId)`: 执行加入今日计划、完成、稍后提醒、归档/恢复归档、编辑、删除。
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
- `mergeVisibleManualOrder(visibleOrderIds)`: 将局部可见任务顺序合并回全局手动排序。
- `sortTasksByManualOrder(tasks)`: 按 `order` 和 `id` 得到稳定手动顺序。

### 导入、导出/备份、示例与定时器

- `startProgressTimer()`: 启动定时刷新。
- `refreshTaskTimers()`: 局部刷新倒计时和状态样式。
- `handleVisibilityChange()`: 页面恢复时刷新。
- `backupTasks()`: 下载版本化本地备份，并更新最近备份时间。
- `downloadTaskData(mode)`: 常规导出/备份下载入口。
- `downloadEmergencyBackup()`: 在运行时存储故障后下载当前内存快照。
- `downloadPreImportSnapshot(tasks)`: 替换导入写入前下载当前任务快照；下载触发后不会立刻写入，必须再次确认。
- `downloadJsonPayload(payload, filename)`: 执行 JSON 文件下载。
- `createTaskDataPayload(mode, date, tasks, storage = 'indexeddb')`: 构建带版本说明、导出 ID 和完整性校验的数据文件。
- `createTaskDataChecksum(payload)`: 基于稳定序列化结果生成备份校验值；导入预览会用它判断文件是否被修改。
- `createTaskDataFilename(mode, date)`: 生成导出/备份文件名。
- `scheduleBackupReminder()`: 根据最近备份时间提示备份。
- `importTasks(file)`: 读取 JSON、展示导入预览，并按替换模式或合并模式写入任务。
- `prepareImportPayload(data)`: 统一传统数组、旧版备份和当前备份入口，记录兼容读取信息。
- `buildImportPreview(importedTasks, rawTasks, sourceData, compatibilitySteps)`: 统计导入数量、当前数据影响、文件内同名重复、重复任务 ID、与当前任务同名项、冲突列表、差异摘要和备份来源信息。
- `getImportSourceInfo(sourceData, compatibilitySteps)`: 从导入 JSON 中提取 Task Tracer 备份模板、文件类型、版本、存储来源、包含项、兼容读取信息和完整性状态。
- `createImportRestoreChecklist(preview, t)`: 生成恢复前检查清单，提示模板版本、任务内容、重复 ID、本地同名项和替换影响。
- `createImportDiffPreview(preview, t)`: 生成新增任务、同名冲突和默认替换范围的导入差异摘要。
- `getImportFileDuplicateNames(names)`: 统计导入文件内同名任务。
- `getImportExistingDuplicateNames(names, existingByName)`: 统计导入文件中与当前任务同名的任务。
- `createImportConflictControls(preview, t)`: 生成合并模式下的同名冲突策略控件。
- `prepareImportedTasksForMerge(importedTasks, conflictActions)`: 根据 keep、skip、replace 策略准备合并任务和需要删除的本地任务 ID。
- `createImportPreviewContent(preview)`: 生成确认弹窗中的导入预览 DOM。
- `normalizeImportedTasks(rawTasks)`: 导入任务规范化；重复任务 ID 会生成新 ID，指向重复 ID 的重复链路引用会被清空，避免误连。
- `normalizeImportedTask(rawTask, index, normalizeId)`: 单任务规范化，并修复完成、归档、暂停重复等布尔值。
- `normalizeImportedSubtasks(rawSubtasks)`: 导入子任务规范化，并修复子任务完成状态布尔值。
- `normalizeStoredDate(value)`: 日期字段校验。
- `addSampleTasks()`: 首次启动示例数据。

## Service Worker 结构

- `CACHE_NAME`: Service Worker 缓存版本。修改运行时代码或缓存资源时应递增，并与 `CONFIG.APP.VERSION` 的版本号保持一致。
- `ASSETS_TO_CACHE`: 预缓存 App Shell、manifest、语言资源和核心图标。
- `install`: 打开缓存并预缓存资源，完成后 `skipWaiting()`。
- `fetch`: 同源 GET 请求分三类处理：
  - 导航和 App Shell: `networkFirst(request, './index.html')`
  - 语言资源: `networkFirst(request)`
  - 其他静态资源: `cacheFirst(request)`
- `notificationclick`: 点击通知时聚焦已有窗口或打开首页。
- `activate`: 删除旧缓存并 `clients.claim()`。
- `isAppShellRequest(url)`: 判断首页请求。
- `networkFirst(request, fallbackUrl)`: 网络优先，网络异常或非 OK 响应时回退缓存。
- `cacheFirst(request)`: 缓存优先，未命中时请求网络。
- `cacheResponse(request, response)`: 写入有效响应副本。

## 维护约定

- 用户加载的运行时代码保持无注释；说明写在本文档。
- 修改语言文件内容时，同步更新 `CONFIG.I18N.RESOURCE_VERSION` 和 `sw.js` 中语言资源 query。
- 修改缓存资源或运行时代码时，同步递增 `CONFIG.APP.VERSION` 和 `CACHE_NAME`，两者版本号必须一致。
- 新增文案必须同时更新 `zh-CN.json` 和 `en.json`，并通过 `tools/validate_static.py`。
- 新增交互控件必须有可访问名称，键盘路径要纳入 `tools/smoke_playwright.py`。
- 修改交互结构、焦点流、颜色对比或翻译渲染时，运行 `tools/accessibility_i18n_audit.py`。
- 新增任务字段要同步导入规范化、导出格式和内部文档。
