# Task Tracer 内部代码说明

本文档说明 Task Tracer 的内部结构、运行流程、主要函数职责与维护约定。`index.html` 和 `sw.js` 是会被用户加载的发布文件，应保持精简；详细解释统一维护在这里。

## 发布文件边界

- `index.html`: 单文件 PWA 主应用，包含样式、SVG 图标、HTML 模板和全部前端业务逻辑。
- `sw.js`: Service Worker，负责 App Shell 缓存、语言资源更新策略、静态资源缓存和通知点击回到应用。
- `manifest.json`: PWA manifest。
- `robots.txt`、`sitemap.xml`: 站点索引入口，指向正式域名 `https://todo.muquew.com/`。
- `resources/zh-CN.json`、`resources/en.json`: 外置语言文件，避免主 HTML 继续膨胀。
- `docs/accessibility-i18n-audit.md`: 无障碍、键盘、读屏器语义和 i18n 审计基线。

## index.html 结构

1. Head 与主题预加载
   - 设置 SEO description、canonical、Open Graph、Twitter Card、SoftwareApplication JSON-LD、PWA 主题色、manifest、favicon。
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
  - `sampleTasksAdded`: 旧版自动示例遗留键；当前启动流程不读取它，不再自动插入任务。
  - `lastBackupAt`: 最近一次点击“导出/备份”的时间。
  - `__task_tracer_storage_probe__`: 启动探针临时键，写入后立即删除，用于验证 IndexedDB 真的可写。

## 项目、标签与搜索规则

- 项目是单值字段，用于主分组和项目视图过滤。全部项目的智能排序视图会调用 `renderGroupedTaskList()` 按项目分组。
- 标签是数组字段，用于给任务增加多个横向标记。
- `matchesTaskSearch(task)` 当前匹配任务名称、描述、项目名和标签。项目和标签都会参与搜索；区别在于项目负责组织层级，标签负责跨项目检索。
- 手动排序只在列表视图、`sort === 'manual'` 且无搜索词时启用。局部筛选或项目视图下拖拽时，`mergeVisibleManualOrder()` 只调整当前可见任务在全局手动顺序中的相对位置。

## 日期语义、重复任务、日期视图与统计

- `timeZoneValidity` 缓存显式时区名的验证结果，最多 128 项；`timeZonePartFormatters` 缓存显式时区的格式器，最多 64 项。超过上限按插入顺序淘汰最早项，避免导入不同名称时无限增长。`getCurrentTimeZone()` 仍实时解析浏览器当前时区；不能把缺省/无效时区回退到固定的启动时区。无日期任务先返回清空字段，跳过不必要的时区工作。
- 截止日期以 `dueAt` 作为真实时间点来源，并使用 `dueTimeZone` 还原任务时区下的日期和时间。界面展示、日历和时间线使用按任务时区还原后的日期；提醒、逾期和剩余时间使用 `dueAt`。
- `getFormDueFieldsForSave()` 在编辑时核对输入日期和时间；未改变时使用原始 `dueAt` 和 `dueTimeZone` 重建显示字段，避免夏令时结束时相同钟面时间的两次发生被合并到第一次。用户改变日期或时间时，仍按当前浏览器时区生成新的时间点。有效的过去日期可用于补记和编辑逾期任务，不再受启动时设置的今天最小值限制。
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

- 任务导入由 `importTasks(file)` 进入，会先经过 `prepareImportPayload()`，再由 `openTaskImportPreview()` 构建预览，展示恢复检查清单、导入差异、导入数量、文件内同名重复、重复任务 ID、与当前任务同名项和替换影响。默认确认后通过 `replaceAllTasks()` 全量替换当前任务；如果替换前已有任务，会先下载 `pre-import-backup` 快照并停留在确认弹窗，等待用户第二次确认。完整性校验失败且用户仍选择替换时，也会先停留并要求显式风险确认。开启合并模式后会读取冲突策略，并通过 `mergeImportedTasks()` 合并、跳过或替换同名本地任务。
- 导出/备份由 `backupTasks()` 进入，通过 `readTaskSnapshot()` 的只读事务同时读取任务和版本，再下载带 `schema`、`versionNotes`、`exportId` 和 `checksum` 的版本化快照。发起下载后，`recordTaskBackup()` 将 `lastBackupAt` 与对应的 `{ date, taskRevision }` 覆盖记录一起写入配置；这些本地记录不属于任务 JSON 新字段，也不能证明浏览器实际保留了文件。导出不能调用会推进 `state.taskRevision` 的任务刷新路径或重绘当前列表。
- 紧急备份由 `downloadEmergencyBackup()` 进入，仅在运行中存储故障且 `storageFallbackTasks` 仍有内存快照时开放；文件会标记 `type: emergency-backup` 和 `schema.storage: memory-fallback`，便于后续恢复时识别来源。
- `scheduleBackupReminder()` 根据 `lastBackupAt` 和任务数量决定是否显示最近备份提醒。
- `runAppAction()` 是交互入口调度层；按钮、快捷键、菜单、命令面板、任务卡片和主下拉的动作统一进入这里。
- `canRunAppAction()` 根据 `STORAGE_GATED_ACTIONS` 判断动作是否依赖持久化存储。IndexedDB 不可用时，任务写入、视图操作、搜索/筛选、导入、常规导出/备份、归档、通知开关、批量操作和命令面板会被拦截，并关闭已经打开的任务弹窗、菜单、下拉和命令面板。
- `ensureStorageAvailable()` 是低层存储保护；核心写函数仍会调用它，作为绕过入口调度时的第二道防线。当前页面内存快照的紧急备份不经过 IndexedDB。

## 初始化流程

`initApp()` 的顺序很重要：

1. `cacheDOM()` 缓存节点。
2. `loadTranslations()` 加载语言文件。
3. `createLangButtons()` 创建语言菜单项。
4. `initializeStorageOrFallback()` 单独处理存储初始化；内部调用 `initPersistentStorage()` 初始化 IndexedDB，并通过 `verifyPersistentStorage()` 执行写入/删除探针。
5. `loadSettings()` 恢复语言、智能视图、通知和已提醒签名。
6. `initLanguage()` 同步 `lang`、`dir` 和页面文案。
7. `loadNormalizedTasks()` 读取任务并修复历史任务字段和子任务重复 ID。
8. `bindEvents()` 绑定事件。
9. `renderTaskList()` 首次渲染；空工作区显示可选示例入口，不写入任务。
10. `handleLaunchCapture()` 处理 `capture`、`add`、`save`、`title`、`text` 和 `url` 启动参数，必要时聚焦快速添加或自动保存；分享目标会把标题作为快速添加文本，把正文和 URL 暂存为确认后写入的描述。
11. `startProgressTimer()` 启动倒计时刷新。
12. `scheduleBackupReminder()` 根据最近备份时间决定是否提示备份。

如果 IndexedDB 被禁用、浏览器隐私模式阻止本地数据库，或写入探针失败，`initializeStorageOrFallback()` 会调用 `handleStorageUnavailable()` 进入保护模式：显示存储不可用横幅和任务区错误态，同步禁用任务相关控件，并由 `runAppAction()` 拦截后续入口；保留主题切换、重试检测、帮助与本地诊断，以及在内存快照存在时可用的紧急备份。非存储阶段的初始化错误不会被包装成本地存储不可用。

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
- `STORAGE_GATED_ACTIONS`: 需要持久化存储可用的交互动作集合。
- `canRunAppAction(action, options)`: 交互入口守卫，必要时关闭已打开的浮层并提示存储不可用。
- `runAppAction(action, payload, options)`: 统一调度按钮、菜单、快捷键、命令面板和任务列表触发的应用动作。
- `closeStorageBlockedSurfaces()`: 存储不可用时关闭任务弹窗、菜单、下拉和命令面板。
- `ensureStorageAvailable(options)`: 核心写函数的低层存储守卫。
- `captureStorageFallbackSnapshot()`: 在进入运行时存储故障保护模式前复制当前任务内存快照。
- `safeGetStorageItem()`、`safeSetStorageItem()`、`safeRemoveStorageItem()`: 包装 `localStorage`/`sessionStorage`，避免隐私模式抛错导致启动中断。
- `handleLaunchCapture()`: 处理 PWA 快捷入口、URL 预填、自动保存和分享目标传入内容。
- `getLaunchCaptureRequest()`: 从 URL 参数读取捕获请求；`add` 优先于分享参数，文本长度由 `CONFIG.CAPTURE.MAX_TEXT_LENGTH` 限制。
- `getSharedCapturePayload(params)`: 将分享目标参数拆成快速添加标题和可写入描述的正文/URL。
- `setQuickAddCaptureDraft(request)` / `getQuickAddCaptureOptions(options)`: 暂存分享描述，并在用户确认同一条分享标题时传给快速添加保存入口。
- `clearLaunchCaptureParams()`: 捕获参数处理后从地址栏移除，避免刷新重复添加。
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
- `bindSavedViewEvents()`: 保存智能视图条的保存、打开、删除与独立视图文件迁移入口。
- `bindFocusModeEvents()`: 顶部今日计划按钮和专注模式退出入口。
- `bindBatchModeEvents()`: 批量选择和批量任务操作入口。
- `setViewMode(viewMode)`: 切换列表、日历、时间线或统计视图。
- `syncViewSwitcher()`: 同步视图按钮选中态。
- `bindNotificationEvents()`: 通知按钮和通知条撤销按钮。
- `bindMenuEvents()`: 主菜单、语言子菜单、导入、导出/备份和归档入口。
- `bindTaskListEvents()`: 任务列表委托点击。
- `bindSubtaskInputEvents()`: 子任务输入。
- `bindSubtaskPreviewEvents()`: 子任务草稿编辑。
- 可能触发任务、配置、视图或筛选状态变化的事件应进入 `runAppAction()`；纯表单联动、弹窗关闭、提示条关闭和本地控件同步可以保持直接事件处理。

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
- `getFormDueFieldsForSave()` / `getFormDueTimeZoneForSave()`: 未更改日期/时间时保留原始时间点与时区，更改时按当前设备时区生成。
- `isValidTimeZoneName(value)` / `getInstantWallPartsInTimeZone(iso, timeZoneName)`: 使用有上限的显式时区缓存，避免对每个日期反复构造验证器和格式器。

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
- `openSavedViewsTransfer()` / `exportSavedViews()` / `importSavedViewsFile(file)`: 打开迁移入口，导出最新配置或读取独立视图文件。
- `validateSavedViewsTransferPayload(payload)`: 验证视图文件的类型、版本、字段、数量、枚举值与完整性校验。
- `planSavedViewsMerge(existing, incoming)` / `showSavedViewsImportPreview(incoming, existing, returnTarget)`: 计算去重、容量与新增数量，展示预览并在事务中确认当前视图未变化。
- `renderProjectFilterOptions()`: 根据任务项目生成项目下拉选项。
- `renderGroupedTaskList(tasks)`: 全部项目智能视图下按项目分组渲染。
- `renderCalendarView(tasks)`: 渲染月份日历视图。
- `createCalendarShell(tasks)`: 生成日历容器。
- `createCalendarGrid(tasks)`: 生成星期标题和日期格。
- `createCalendarTaskButton(task)`: 生成日历中的任务按钮。
- `shiftCalendarMonth(delta)`: 切换日历月份。
- `renderTimelineView(tasks)`: 按时间顺序渲染日期组，无截止日期组置后；普通模式限制任务卡片数量，日期组计数仍来自完整匹配组。
- `createTimelineGroup(key, tasks, totalCount)`: 生成单个日期分组，区分已显示卡片与该日期的完整任务数量。
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
- `saveQuickAddText(rawInput, options)`: 快速添加和 URL 自动保存共用的写入入口；未指定 `/项目` 时任务进入 `Inbox`，分享目标确认保存时会把暂存的正文和 URL 写入描述。
- `buildTaskPayloadFromQuickAdd(rawInput, options)`: 将快速添加文本解析为任务 payload，复用日期、时间、标签、项目解析和可选捕获描述。
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
- `runAppAction(action, payload, options)`: 菜单、快捷键、命令面板、下拉和任务卡片共用的动作调度入口。
- `canRunAppAction(action, options)`: 动作执行前的存储可用性检查。
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
- `importTasks(file)`: 显示可取消的文件读取状态，再把规范化后的任务文件交给导入预览。使用 `pendingTaskImportReader` 和来源 DOM 身份拒绝已取消或被新读取取代的回调；`closeDialog()` 中止仍待处理的读取。
- `openTaskImportPreview(importPayload, importedTasks)`: 将预览绑定到创建时的任务版本；后台刷新后重建预览、重置合并与安全确认，保留已选择的文件，要求再次检查。
- `prepareImportPayload(data)`: 统一传统数组、旧版备份和当前备份入口，记录兼容读取信息。
- `buildImportPreview(importedTasks, rawTasks, sourceData, compatibilitySteps)`: 统计导入数量、当前数据影响、文件内同名重复、重复任务 ID、与当前任务同名项、冲突列表、差异摘要和备份来源信息。
- `getImportSourceInfo(sourceData, compatibilitySteps)`: 从导入 JSON 中提取 Task Tracer 备份模板、文件类型、版本、存储来源、包含项、兼容读取信息和完整性状态。
- `createImportRestoreChecklist(preview, t)`: 生成恢复前检查清单，提示模板版本、任务内容、重复 ID、本地同名项和替换影响。
- `createImportDiffPreview(preview, t)`: 生成新增任务、同名冲突和默认替换范围的导入差异摘要。
- `getImportFileDuplicateNames(names)`: 统计导入文件内同名任务。
- `getImportExistingDuplicateNames(names, existingByName)`: 统计导入文件中与当前任务同名的任务。
- `createImportConflictControls(preview, t)`: 延迟创建合并模式下的同名冲突策略控件，每次加载 100 项；批量策略作用于未显示项。
- `syncImportConflictControls(root)`: 首次开启合并才初始化策略控件，切换合并状态不重建已选行。
- `getImportConflictActions()` / `getImportOptions()`: 收集已渲染行的单独策略及批量默认值，准备合并时为未显示冲突应用该默认值。
- `prepareImportedTasksForMerge(importedTasks, conflictActions, conflictDefault)`: 优先应用已显示行的单独策略，其余同名冲突应用批量默认值，准备合并任务和需要删除的本地任务 ID。
- `createImportPreviewContent(preview)`: 生成确认弹窗中的导入预览 DOM。
- `normalizeImportedTasks(rawTasks)`: 导入任务规范化；重复任务 ID 会生成新 ID，指向重复 ID 的重复链路引用会被清空，避免误连。
- `normalizeImportedTask(rawTask, index, normalizeId)`: 单任务规范化，并修复完成、归档、暂停重复等布尔值。
- `normalizeImportedSubtasks(rawSubtasks)`: 导入子任务规范化，并修复子任务完成状态布尔值。
- `normalizeStoredDate(value)`: 日期字段校验。
- `addSampleTasks()`: 仅响应空工作区中用户主动选择的示例任务操作；不会在启动或刷新时自动填充任务。

## Service Worker 结构

- `CACHE_NAME`: Service Worker 缓存版本。修改运行时代码或缓存资源时应递增，并与 `CONFIG.APP.VERSION` 的版本号保持一致。
- `ASSETS_TO_CACHE`: 预缓存 App Shell、manifest、语言资源和核心图标。
- `manifest.json.shortcuts`: 暴露 `Quick Capture` 安装快捷入口，URL 为 `./?capture=1`。
- `manifest.json.share_target`: 使用 GET 分享目标，把系统分享的 `title`、`text`、`url` 作为 URL 参数传回 `handleLaunchCapture()`；标题用于快速确认，正文和 URL 在确认后进入任务描述。
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

- 复杂逻辑、数据字段和维护规则需要同步记录在本文档。
- 修改语言文件内容时，同步更新 `CONFIG.I18N.RESOURCE_VERSION` 和 `sw.js` 中语言资源 query。
- 修改缓存资源或运行时代码时，同步递增 `CONFIG.APP.VERSION` 和 `CACHE_NAME`，两者版本号必须一致。
- 新增文案必须同时更新 `zh-CN.json` 和 `en.json`，并通过 `tools/validate_static.py`。
- 新增交互控件必须有可访问名称，键盘路径要纳入 `tools/smoke_playwright.py`。
- 修改交互结构、焦点流、颜色对比或翻译渲染时，运行 `tools/accessibility_i18n_audit.py`。
- 新增任务字段要同步导入规范化、导出格式和内部文档。


## 4.3 可靠性与发布约定

- `config.taskRevision` 与任务写操作在同一读写事务中检查并递增；`writeTaskTransaction()` 在调用时同步捕获预期版本，异步数据库回调不再读取可变的当前版本来替代它。旧视图写入会抛出 `TaskConflictError`，刷新任务但保留编辑草稿。编辑表单还保存打开时的任务快照，避免刷新后再次提交覆盖远端修改。
- 撤销记录包含数据库中操作前后的任务快照，只回滚发生变化的 ID，并在写入前检查受影响记录；不会清空整个任务库。
- `config.recoveryHistory` 保存最近 10 个恢复点。普通修改每五分钟最多追加一次，删除、导入、撤销和恢复前强制追加。恢复点与任务写入共同提交或回滚。同步与异步配额失败均必须保留任务和紧急导出。
- 启动写探针失败时，如果数据库仍可读，先保留只读任务快照，再进入保护模式。配额故障的“清空恢复历史”需要二次确认，只删除该配置键，然后重新初始化；不清除任务或其他设置。重连前关闭旧连接。
- 数据库连接处理 `versionchange`，立即释放连接并转入可导出的保护模式；`blocked` 显示关闭旧窗口后重试的提示，放弃的升级请求不会在用户不知情时继续迁移。
- 普通列表每批渲染 100 个匹配任务。搜索与过滤先处理完整任务集，再截取渲染批次；查询解析缓存按查询键复用，搜索文本缓存按渲染周期重建。手动排序和批量模式暂不分页。
- 修改脚本后运行 `python3 tools/security_policy.py --write` 更新部署 CSP。只读检查和真实带响应头的浏览器检查都必须通过。不要恢复 `script-src` 的 `unsafe-inline`。
- `package.json`/锁文件只管理 axe-core 开发依赖；运行应用仍不需要 Node 或构建。全部检查由 `tools/check.py` 调度。`tools/build_release.py` 生成确定性静态包、文件清单与校验和；打包不代表发布。

## 4.4 数据导出与异步提醒

- `exportTasksCsv()` 从数据库读取全部任务，输出 UTF-8 BOM、CRLF 与 17 个稳定英文列名；标签、重复星期、子任务使用 JSON 单元格。`quoteCsvCell()` 统一转义引号并对公式前缀加单引号。CSV 不参与导入恢复，也不改变 `lastBackupAt`。
- `deliverTaskReminder()` 在发送前捕获不可变的提醒键与时间戳；发送后 `recordReminderDelivery()` 在事务中重新读取任务，核对提醒键、稍后提醒及上次发送时间，只在最新记录上更新提醒元数据。删除、完成、归档或提醒条件已变更时跳过，避免异步发送覆盖编辑或复活删除记录。
- CSV 回归在三个浏览器引擎运行；延迟通知回归覆盖另一窗口编辑、删除和稍后提醒，并在提交后检查数据库。

## 4.5 初次使用、任务引用与本地支持

- 初次启动保持空工作区。只有整个任务库为空时，空状态才显示“添加 3 个示例任务”；筛选或搜索得到的空结果不会显示该入口。旧版 `sampleTasksAdded` 标记不再触发自动插入。
- `addSampleTasks()` 对重复点击设置进行中保护，先规范化示例记录，再在一个任务事务中检查数据库仍为空并使用 `add()` 插入全部记录。事务失败不会留下部分示例，也不会覆盖其他窗口新建的任务。示例名称带本地化前缀，提醒关闭，可编辑、删除或撤销；撤销后刷新仍保持空工作区。
- `normalizeTaskReferenceId()` 只接受有限数值或非空的数字字符串。`null`、空白、布尔值及其他无效输入均规范化为 `null`，数值 `0` 保持有效。重复任务生成、任务规范化、导入与引用清理共用该规则，避免把缺失引用当作 ID 0 的关联。
- `normalizeImportedTasks()` 在分配无效或重复 ID 的替代值前预留全部有效原始 ID，避免生成值抢占尚未处理的任务 ID。指向重复原始 ID 的歧义引用被清空；最终引用还必须指向最终导入任务集中的真实记录。
- 智能视图的保存和删除经 `dbActions.updateSavedViews(change)` 在单个 `config` 读写事务中读取最新列表、应用本次操作并写回；不再把旧窗口中的整份列表直接覆盖数据库。`saveSmartView()` 与 `deleteSavedView()` 只在事务完成后更新内存和页面；异步失败保持原有视图，保存失败的对话框保留草稿。跨窗口保存与删除的正确性由专门回归验证，不能依赖单窗口成功路径。
- `openHelp()` 通过菜单和页脚提供快速添加、限定搜索、备份范围、离线与提醒限制、隐私和快捷键说明，并提供命令面板与本地诊断入口。帮助内容使用翻译文本与 DOM 构造，不加载远程帮助脚本。
- 帮助和 `openDiagnostics()` 在数据库保护模式下仍可打开；命令面板保持存储限制。诊断先展示完整 JSON 预览，再由用户下载，不自动上传。报告只包含应用/资源/数据库版本、浏览器能力、权限、存储估计和白名单错误类别，不包含任务内容、标签、项目、查询、备份、完整网址或原始错误消息。诊断文件不计为任务备份。
- `tools/onboarding_playwright.py` 支持 `--browser chromium|firefox|webkit`，默认 Chromium；已在 Chromium 154、Firefox 153 与 WebKit 26.5 验证空启动、显式示例、键盘操作、重复点击、撤销后不重建、另一窗口任务保留、空搜索入口隔离及配额失败原子回滚。整合检查与真实移动设备的结果应以候选版本记录为准。

## 4.6 迁移文件与确认生命周期

- 任务备份格式继续使用 `2.4`，不纳入智能视图、应用偏好或恢复历史。4.6 的视图迁移文件独立使用 `type: saved-views`、`version: 1.0`（4.7 新导出与兼容规则见下文），只包含 `app`、`type`、`version`、`date`、`savedViews` 和 `checksum`；每个视图包含 ID、名称、搜索、状态筛选、项目筛选、排序与布局。
- 视图文件必须不超过 1 MiB、最多 12 个记录，字段、字符串和支持的筛选/排序/布局枚举需通过检查。校验基于现有稳定序列化与完整性哈希，校验失败或类型错误直接拒绝，不将任务备份误作视图文件。它用于一致性检查，不用于加密或身份认证。
- 导出从数据库读取最新视图，导入以当前已保存列表为基础，在 `updateSavedViews()` 的单个配置事务中合并。相同条件的视图跳过，保留已有 ID、顺序与名称；新记录重新生成 ID，超出 12 个上限的记录在预览中明确列为容量跳过，不淘汰原有记录。相同名称但不同条件可以并存。
- 视图导入预览按名称及规范化条件建立语义快照；提交时如果当前列表不同，事务中止、更新计数并等待用户再次确认。成功提交前不更新内存，不改变任务、`taskRevision`、`lastBackupAt`、恢复历史或应用偏好。取消异步文件读取后不得重新打开过期预览。
- `buildImportPreview()` 保存创建时的 `taskRevision`。任务导入确认发现后台刷新后版本变化时，调用 `openTaskImportPreview()` 重建当前预览；之前的替换快照、校验风险确认和冲突选择都不能继续作为新数据的审批。替换需要重新下载包含最新任务的安全快照，然后显式确认。
- `confirmTaskChanges()` 为删除任务、批量删除、清空/归档已完成任务及恢复点替换捕获打开时的任务版本。如果确认期间版本改变，关闭过期确认并提示重新检查；尚未载入内存的其他窗口写入仍由数据库事务版本检查拦截。
- `writeTaskTransaction()` 的 `expectedRevision` 必须在创建事务时同步捕获。排队期间的只读刷新可能更新 `state.taskRevision`，不得因此把旧任务载荷变成合法的新写入。任务与恢复点仍共同提交或回滚。
- 视图迁移文件会保留私密搜索词、项目名或标签，不能与不含用户内容的诊断文件混为一谈；用户公开报告应使用示例文件。任务文件的读取生命周期也必须防止取消或被较新读取取代后覆盖当前任务草稿或导入预览。
- `getCurrentSmartViewSnapshot()` 直接读取搜索输入框当前值，`getDefaultSavedViewName()` 也使用同一输入来源。搜索列表本身仍有防抖，但立即点击保存不能把较早的 `state.searchQuery` 作为视图内容。
- 任务文件读取使用 `taskImportReadStatus` 展示状态，`pendingTaskImportReader` 记录本次读取；取消弹窗会中止它，回调还需核对当前 reader 与来源 DOM，防止旧读取抢占新表单或较新的导入预览。
- 同名导入冲突控件只在首次启用合并时初始化，每批显示 100 项并保留已选行。`importConflictDefaultAction` 为全部冲突提供 keep/skip/replace 默认值，包括未渲染项；更改默认值会重置已显示行的单独选择，之后可继续逐项覆盖。关闭再开启合并只隐藏/显示原控件，不能丢失策略。
- `renderTaskList()` 的分页键包含当前视图，搜索、筛选、排序、项目、今日计划、批量状态或视图改变时将 `listRenderLimit` 重置为 100。普通时间线在完整日期分组后按余量截取卡片，`createTimelineGroup(key, tasks, totalCount)` 分别接收已显示记录与完整组数量；手动排序和批量模式保留完整匹配渲染。时间线显示更多沿用列表控件，并把焦点移到新增卡片，不能通过分页改变数据库。
- `tools/timezone_playwright.py` 覆盖纽约 DST 间隙/重叠、加德满都四分之一小时偏移、豪勋爵岛半小时转换、基里蒂马蒂跨日和当前时区变化后的无效值回退。程序存在不代表已通过，实际结果以候选记录为准。
- 新增检查覆盖视图文件往返、过期导入/删除/恢复确认、排队写入版本、任务文件读取生命周期、延迟冲突控件与批量策略，以及含子任务的任务导出/导入/恢复往返。各程序实际结果与大工作区测量以 [4.6 候选说明](releases/4.6.md) 为准，不能仅凭脚本存在宣称通过。


## 4.7 备份覆盖、项目范围与翻译回退

- `dbActions.readTaskSnapshot()` 在同一个只读事务中读取任务与 `taskRevision`；JSON 和 CSV 导出都使用这个快照，不更新 `state.tasks`、`state.taskRevision` 或当前任务界面。普通任务刷新仍通过 `getAllTasks()` 推进内存版本，不能在导出路径混用。
- `recordTaskBackup(date, taskRevision)` 在同一配置事务中写入日期和对应版本，较早完成的下载不得覆盖较新的导出记录。`getTaskBackupStatus()` 与 `getBackupHealthStatus()` 联合核对当前版本、日期匹配和时间间隔；旧的仅日期记录或任务已改变时，不得显示当前任务已覆盖。浏览器发起下载不能证明用户保存了文件；CSV、视图和诊断导出不更新任务备份覆盖。
- 保存视图在配置事务里检查最新列表。新增不同条件时若已有 12 项，抛出 `SavedViewsLimitError`，不驱逐原视图；失败后保留名称草稿。条件相同的视图保留原 ID 与位置，只更新对应记录。
- `normalizeProjectFilter()` 生成 `{ kind: 'all' }`、`{ kind: 'unassigned' }` 或 `{ kind: 'project', name }`。`projectFilterKey()` 用规范化对象建立比较键，不能用项目名与控制值共用的字符串来比较。真实项目名 `all`、`__none__` 或 JSON 字面文本必须仍可精确选择；缺失的命名项目保留空范围。
- 新视图文件版本为 `1.1`，`isValidProjectFilter()` 严格检查范围对象及字段数量；导入也接受 `1.0` 的旧字符串。旧配置里的字符串按原语义读取，无关操作不得改写配置。任务 JSON 仍为 `2.4`，数据库仍为 `2`；旧版应用不能读取新的视图文件。实际 4.6 会把非字符串 `projectFilter` 当作 `all`，旧窗口写配置还可能将新范围折为全部项目；修改新保存视图前必须关闭或刷新旧窗口。降级前导出并保留 1.1 文件，回到 4.7 或更新版本后恢复。任务字段升级/回滚证据不能泛化为新视图配置向旧 UI 兼容。
- `captureTaskFormDraft()` 与 `isTaskFormDirty()` 比较当前会话表单基线；`requestCloseTaskDialog()` 在同一弹窗显示继续编辑/放弃，保存进行中不通过普通关闭入口退出。`handleTaskDraftBeforeUnload()` 在脏表单或存在待恢复队列时请求浏览器离页提示，浏览器仍可限制该提示。表单会话没有持久化自动保存。
- `loadTranslations()` 优先请求当前资源版本；请求失败时，从同一 HTML 的 `bundledTranslations` 非执行 JSON 数据读取相同版本的语言。它不能借用旧版本语言代替当前 UI 文案。
- 修改翻译、语言列表或资源版本后，依次运行 `python3 tools/translation_fallback.py --write` 和 `python3 tools/security_policy.py --write`，再执行静态检查。生成器编码所有 `<`，避免翻译文本中的关闭脚本标记结束数据块；静态验证核对版本与完整内容一致。此维护过程不改变应用免构建的静态运行方式。
- 新 worker 只在必需资源全部缓存后完成安装，安装失败保留已完整安装的版本；活动旧窗口仍可能使用自己的缓存策略。真实 4.6 发行包到当前候选的中断升级与离线启动必须单独验证，不能用只改版本号的新 worker 替代旧发行包；默认检查自含 fixture，`--legacy-archive dist/task-tracer-4.6.zip` 才选择实际旧包。当时的最终结果见 [4.7 候选记录](releases/4.7.md)，不能从源码存在推断浏览器验证通过。

- `handleStorageUnavailable()` 在清空任务显示、关闭表单前调用 `preserveTaskDraftForRecovery()`。`recoverableTaskDrafts` 只保存在内存，包含原始表单值、未提交子任务输入、编辑 ID 和原记录快照；重复失败按会话恢复 ID 更新同一份。`downloadRecoverableTaskDrafts()` 下载独立 `type: task-draft`、`version: 1.0` 文件，不含 `tasks` 数组，不计作备份且不能走任务导入。
- 有待恢复队列时，`retryStorageAvailability()` 必须在原页面重连数据库、重新加载设置与任务，不能刷新页面丢掉队列。`restoreRecoverableTaskDraft()` 显式恢复下一份，保留 `editingTaskSnapshot` 以继续拦截过期编辑；已有表单打开时不得覆盖。`discardRecoverableTaskDraft()` 逐份确认放弃，不能因为恢复数据库成功就隐式丢弃。页面刷新、关闭或崩溃仍会失去未下载的内存草稿。

- `dbActions.recordReminderDelivery(expected, lastReminderAt)` 不使用普通全记录写事务的全局预期版本；它在同一任务/配置读写事务里读取当前版本与新鲜记录，仅当提醒键、稍后提醒时间和上次提醒时间仍匹配且任务未完成/归档时补写提醒字段与 `taskRevision + 1`。不匹配时不写入、不推进版本，删除记录也不能复活。`deliverTaskReminder()` 随后执行全量 `refreshTasks()`，不能只把内存版本提升后继续保留旧任务数组；后续普通 UI 保存仍须拦截过期任务，避免覆盖其他窗口的新字段。事务中止或配额失败保持原任务与版本。

- `scheduleBackupReminder()` 的启动提醒是可选提示：延迟状态读取前及完成后都检查存储可用、无打开的弹窗、无已显示的通知，不满足则静默跳过，不能覆盖非法文件等操作错误或打断草稿。跳过提示不清除菜单备份健康状态，也不伪造导出记录。`tools/backup_reminder_priority_playwright.py` 控制真实定时回调与 IndexedDB 读取完成，覆盖读取期间新打开表单或新错误等竞态；当前候选结果仍以发行记录为准。


## 4.8 日历、输入法、撤销与恢复管理

- `renderCalendarView()` 仍对完整匹配集合分组。`createUndatedSection()` 在普通模式按 `listRenderLimit` 截取无日期卡片，`createCalendarDayDetail()` 按独立的 `calendarDetailRenderLimit` 截取某天详情；二者初始均为 100，各自通过 `createCalendarPagination()` 的显示更多增加 100。完整计数和搜索范围不能随显示上限缩小。
- `handleCalendarActionClick()` 在加载更多前记录已有任务 ID，重绘后将焦点移到新增项；`handleCalendarDetailClick()` 切换日期时重置详情上限，关闭详情后 `focusCalendarMoreButton()` 优先返回该日期的更多按钮；按钮已消失时回退到该日期的添加按钮。筛选、视图等范围变化必须重置对应分页状态。手动排序和批量模式保留完整匹配渲染，不能因分页悄悄改变选择语义。
- `calendarSearchNeedsSync` 仅在搜索词变化后允许一次月历同步；若有日期匹配且当前 42 格范围内没有任何匹配，则跳到最早匹配日期所在月份并关闭旧详情。手动翻月不会反复触发该跳转，无日期匹配不强行改变月份。
- `state.composingInputs` 用 `WeakSet` 跟踪捕获阶段的 `compositionstart` / `compositionend`。`isCompositionKey()` 同时检查 `event.isComposing`、兼容值 `keyCode === 229` 和正在组合的目标；`hasActiveComposition()` 保护原生表单提交。快速添加、任务表单、子任务输入/编辑和命令面板不得将候选阶段的 Enter、Escape、方向键误用为应用命令。
- 自动输入法检查发送 DOM 组合/键盘事件，只验证应用分支，不能替代真实操作系统输入法或手机候选栏测试。 内联子任务输入框出现后，还须等待其实际获得焦点再调用测试 `fill()`；既有零延迟焦点/光标初始化可能在原生全选与插入间改变选择，不能只等可见或放宽精确文本断言。4.8 首轮失败与定向修正见 [4.8 记录](releases/4.8.md)，后续完整通过结果见 [4.8.1 候选记录](releases/4.8.1.md)；旧报告保留原版本与实际结果。
- `captureUndoSnapshot()` 继续返回数组，并以不可枚举属性保存 `persistedSnapshot` 与 `undoTaskRevision`：前者在同一只读事务读取任务和版本，后者记录动作发起时版本。`registerUndoSnapshot()` 只接受本次写入恰好推进一个版本的状态；若动作完成后刷新已包含另一窗口的提交，不得将旧动作登记到较新版本。
- Undo 的 after 快照也使用 `readTaskSnapshot()`，不能推进全局版本。执行时核对 before、after 与当前版本，任一不匹配保守拒绝，不能写任务、配置或恢复历史。此限制只使过期动作失效，后续新动作及其 Undo 仍可正常使用。批量选择跟随当前项目/状态/搜索范围修剪；筛选后的手动排序不能改写隐藏任务的槽位和其他字段。
- `openRecoveryHistory()` 在同一弹窗内以 `renderPreview()` 分页展示选中恢复点的名称/状态；初始 100 项、每次加 100，完成/归档计数基于全部记录并复用 `normalizeBoolean()` 兼容旧值。切换点重置分页和恢复勾选；新增行接受焦点，长名称需在窄视口换行。恢复列表使用上限 32vh/18rem 的内部滚动和焦点留白，避免 100 行内容把导出、清空与恢复操作推到远处；空列表隐藏但仍显示空点说明。
- 恢复点导出规范化克隆的旧任务，通过 `createTaskDataPayload('backup', ...)` 生成现有 2.4 备份；文件名带 `recovery-backup`，但不能调用 `recordTaskBackup()` 或刷新当前任务状态。空点也可导出，任务导入需保留受支持字段。
- `confirmClearRecoveryHistory()` 发起独立确认；`getRecoveryHistoryKeys()` 记录已审顺序 ID，`clearReviewedRecoveryHistory()` 在仅 `config` 的读写事务中与最新历史比较。变化时抛 `RecoveryHistoryConflictError`、保留历史并重开预览，旧确认不能沿用。成功仅删除 `recoveryHistory`，不能写任务、版本、偏好、备份或撤销；后续正常任务写入仍能建立新点。异步完成回调还需核对原弹窗，不能覆盖随后打开的草稿。


## 4.8.1 快速添加的存储恢复

- `hasUnsavedQuickAddText()` 只用 `value.trim()` 判断是否有待提交内容，不改写输入框原始 `value`。存储不可用且有文字时，`setQuickAddSaving()` 保持输入框启用但 `readOnly`，提交按钮仍禁用，并通过 `quickAddRetainedMessage` 关联说明当前页内存和刷新/崩溃限制。
- `retryStorageAvailability()` 在完整表单队列非空或快速添加有文字时，在同一 document 重连存储、恢复设置和任务，不走 reload。两种草稿并存时优先聚焦表单恢复入口，否则展开快速添加并聚焦原文。失败后的重试仍保留原文与 `quickAddCaptureDraft`；恢复不自动调用保存。
- `handleTaskDraftBeforeUnload()` 加入非空快速添加，仍由浏览器决定实际离页提示。`getQuickAddCaptureOptions()` 在原文保留时继续使用已有捕获描述；成功明确提交后才清空文字和捕获上下文。完整表单 `task-draft` 下载的范围不因此扩大到快速添加。
- 4.8.1 该轮版本为 app/cache/package `4.8.1`、资源 `4.33`，数据库/任务文件/视图文件格式不变。统一 runner 共 39 项，主工作区最终 Chromium 完整运行全部通过，发行包可复现构建及解压后的持久保存、离线验证也已通过；三引擎专项与完整运行的具体范围见 [4.8.1 候选记录](releases/4.8.1.md)。实机、远程 CI 与实际部署验证仍未执行。

## 4.8.2 日期、持续刷新与发行边界

- 4.8.2 该轮版本为 app/cache/package `4.8.2`、资源 `4.34`，DB `2`、任务 JSON `2.4`、视图文件 `1.1`/旧 `1.0` 导入保持不变。runner 登记 46 项，首轮 45 项通过、英文无障碍一项失败；原生名称修正后重新冻结的第二次完整运行已全部通过，46/46、合计 904.491 秒；上一节的 4.8.1 通过记录保留其版本边界。当前专项与待办见 [4.8.2 候选记录](releases/4.8.2.md)。
- `calculateNextRepeatDueFields()` 将任务日期转为 UTC 午夜的纯日期载体，使用 `setUTCDate()` 等 UTC 日历运算，再将结果日期与原时间、原任务时区交给 `createDueFields()`。`getNextWeeklyRepeatDate()`、`getLastDayOfNextMonth()`、`addMonthsClamped()` 和 `getDaysInMonth()` 使用一致的 UTC 字段；`getTaskRepeatWeekdays()` 的旧缺省星期也取任务日期的 `getUTCDay()`，不能先构造宿主本地午夜。
- `utils.localDateTimeToInstantISO()` 比较目标时区偏移产生的候选：精确匹配时选最早时间点，gap 则选向前的最小墙钟差。`createDueFields()` 通过 `createDueFieldsFromInstant()` 回算规范字段，不保存与 `dueAt` 矛盾的输入日期/时间；`normalizeTaskDueFields()` 优先以已有时间点回算。`getFormDueFieldsForSave()` 仍在日期/时间未更改时保留原时间点，不把已存 late fold 重解释为第一次。日期控件的双语 hint 说明新输入的转换政策。
- `calculateTaskStats()` 的 `deadlineTasks` 只统计未归档、未完成且有截止日期的任务；逾期分子使用相同范围再加已到期条件。完成率、归档计数与完成趋势各保留原范围，不因修正逾期率而混用分母。统计与范围切换只读，不写任务或配置。
- `planTaskTimeRefresh()` 在渲染后记录下一次本地午夜、到期、3 日和 7 日状态阈值，以及当前日期、时区偏移和检查时钟。`refreshTaskTimers()` 每分钟及可见性事件重查边界、时钟回退和本地偏移变化；普通无边界分钟不重建整个视图。`scheduleTaskTimeRefresh()` 在已挂起刷新时合并交互事件至一个 animation frame。
- `canRefreshTimeDependentView()` 在隐藏页、存储不可用、弹窗、写操作、已选批量任务、列表行内编辑、拖动或任务文字选择期间暂缓重建。`hasTaskTimeTextSelection()` 也保护逐项时间文案更新；释放交互后再应用。`getTimeRefreshFocusSelector()`/`refreshTimeDependentView()` 查找对应新控件或退回当前视图按钮，保留可用焦点。刷新只重新计算视图，不能写日期、配置、revision 或历史；后台 suspension 不等于系统定时服务。
- `deleteSavedView(id)` 用 `textContent` 插入准确名称，确认默认聚焦取消；关闭不写入。明确提交后在 `dbActions.updateSavedViews()` 最新配置中按稳定 ID 过滤，保留同名视图和另一窗口新增项；它不改任务、备份覆盖、revision 或 Undo。成功后返回邻近视图/保存按钮，旧异步完成必须通过 `isCurrent()` 才能处理当前弹窗焦点或通知。
- `#savedViewDeleteConfirm` 使用 `overflow-wrap: anywhere` 防止无空格长名在窄屏越出弹窗；`.saved-view-delete` 的 `flex: 0 0 32px` 与 `min-width: 32px` 防止长名将删除目标压缩至实测的 20.92px。`createSavedViewChip()` 的 apply 按钮改由可见 name/meta 和 CSS 分隔符生成原生可访问名称，动作描述留在 `title`，不另用 `aria-label` 覆盖。只写名称会漏 meta，手工拼接 meta 仍可能与英文完整可见名称不符；先前中文四场景通过未覆盖首轮整合里的英文失败。永久专项已扩为双语共八场景，原生名称修正后八场景全部通过；完整 standalone 无障碍程序及重新冻结后的第二次完整 46 项也已通过，首轮失败报告仍保持原样。
- `captureFocusReturnTarget()` 对保存视图控件记录 `{ type: 'saved-view', id, action: 'apply'|'delete' }`，`resolveFocusReturnElement()` 在返回时按稳定 ID/action 查找当前 DOM，视图已移除则返回保存视图按钮。不能只保留 Element：搜索的 300ms debounce 可在确认期间重建 chips，令旧 × 脱离页面；删除取消与成功后的焦点均使用该描述符。新增确定性 debounce 专项使用真实搜索 input/300ms timer 和 hit-test 后 mouse click，确认旧节点确实脱离后返回同 ID 新 ×，三引擎均通过。
- 时间刷新专项 12 组已在三引擎通过；其可见性测试覆盖受控 `document.hidden` 和显式 `visibilitychange` 事件，不模拟系统真实挂起。长名删除的中文四场景 axe 及七组删除/debounce 三引擎专项曾通过，但首轮完整 46 项仍在英文无障碍失败；不能据旧定向结果改写该报告。
- `tools/build_release.py` 的 `DISTRIBUTION_SOURCES` 是 22 项明确源→ZIP 映射，包括两份发行 README；加生成的 `integrity.json` 后严格为 23 项。`relative_distribution_path()` 拒绝越界/非规范目标，`validated_source()` 验证源及每级父路径无 symlink、位于根目录内且为文件。不得恢复递归资源目录打包，清单哈希正确也不能证明没有打入多余私密文件。
- `tools/verify_deployment.py` 从 `ASSETS_TO_CACHE` 读取实际请求 URL，保留语言资源 `?v=` 查询，验证根 HTML/配置响应头及每个资源的完整字节；也检查 worker、manifest 和无查询的语言文件。禁止外部、绝对、越界及非规范资源路径。独立本地 HTTP fixture 只验证工具的接受/拒绝行为，不证明生产域名已部署；它属于完整 runner，`--static-only` 保持四项且不启动监听 socket。
- 独立 `tools/quick_add_workspace_playwright.py` 不属于 46 项 runner。可选 `--expect-app-version`/`--expect-resource-version` 固定目标版本，同时记录实际源码 hash 并在结束时验证未变化；不能把旧版本固定 guard 简单删除后把历史结果改名为新版本证据。新的已冻结源码必须实际运行，结果只证明专项大工作区正确性。

## 4.8.3 外来钟面时间、日历与工具元数据

- 新候选 app/JSON-LD/cache/package 已统一为 `4.8.3`，翻译资源仍为 `4.34`；DB `2`、任务 JSON `2.4` 和视图 `1.1`/旧 `1.0` 导入不变。4.8.2 的 46 项及发行包属于历史成功；当前完整 49 项已在 Chromium 全部通过，合计 925.720 秒；两次独立构建及解压持久/离线通过，22 个发行源与 57 个工具/配置输入指纹均未变，实际进度见 [4.8.3 候选记录](releases/4.8.3.md)与[输入指纹](releases/inputs-4.8.3.json)。
- `prepareEditTaskForm()` 将 `getTaskDueDateKey()` 和 `getTaskDueTimeValue()` 直接交给 `setDeadlineControls({ dateKey, time, ... })`，编辑回填不能先经过宿主本地 `Date`。一个 UTC 日期/时间可能恰好在设备时区不存在；本地 `Date` 会自动归一化，使只改备注也被误判为改了截止时间，继而改写时间点。
- `matchesTaskDueSearch()` 对精确日期与相对日期范围直接比较任务日期 key；`formatTimelineDate()` 用 UTC 中午载体并显式 `timeZone: 'UTC'` 格式化该 civil date。已有时间点保持不变；旧错误时间点的原意不可可靠反推，不能因 UI 修复批量猜测并写回。
- 日历已统一纯日期 UTC 载体：`getCalendarTodayDate()` 由设备当前日期建立载体，`getCalendarDays()`/`getCalendarDateKey()`、月份导航和标签使用一致 UTC 字段。日历添加传 `dueDateKey` 到新表单，不经设备本地日期重构；实际保存不存在的设备日历时间仍按既有 gap-forward 政策。Chromium 的真实 CDP 三种时区切换、Apia 42 格及静态 civil-date 组已通过；Firefox/WebKit 静态组及原 calendar navigation/performance 三引擎回归也全部通过；只有 Chromium 使用真实 CDP，不冒充真实 OS 时区切换验收。
- `validate_static.app_version()`、`resource_version()`、`configured_languages()` 与 `default_language()` 从 `translation_fallback.main_script()` 选中的主运行 IIFE读取对应 CONFIG 区块；`build_release.py` 共用 `app_version()`，不再扫描整个 HTML 的首个 VERSION。合法翻译字符串中的 `VERSION: '99.99'` 在隔离 4.8.2 fixture 中令真实构建产出错误版本包，历史主树包未改写；完整性哈希本身不能识别语义版本取错。Help/SW update/upgrade/quick workspace 工具的 reader 也统一限定运行脚本，保留 DOM/controller、显式 expected 版本和 source hash 断言。
- `validate_package_versions()` 要求 `package.json` 顶层、`package-lock.json` 顶层及 `packages['']` 三处均为三段数字版本，并与 app 规范化版本一致：app `X.Y` 对应 npm `X.Y.0`，app `X.Y.Z` 原样匹配。`release_versions_test.py` 已登记并通过真实静态检查/构建回归，十种 metadata drift/missing 被拒绝，两段 app/npm 补零兼容及合法配置示例文本不污染元数据均通过；五项 static-only 与其后完整 49 项均已实际通过；三引擎专项不能扩称所有 49 项都在三引擎执行。
- 既有 JavaScript checksum 按 UTF-16 code units 计算 FNV；Python `for char in text` 按 Unicode code point 遍历，astral 字符会产生测试假阴性。emoji/ZWJ/长文本的实际任务 JSON、CSV 和视图文件探针未复现运行时错误；smoke helper 已按 UTF-16 little-endian 字节对迭代 code unit；原 CSV 程序已加入实际 Unicode JSON 下载、独立干净 profile 导入/全字段/重载并在三引擎通过，不新增第 50 个程序。此处不修改任务/视图格式或 checksum 算法，也不宣称 Python 断言失败就是用户文件损坏。

## 4.8.4 导入字段、重复链与报告生命周期

- 新候选为 app/cache/package `4.8.4`、资源 `4.35`；DB `2`、任务 `2.4`、视图 `1.1`/旧 `1.0` 导入不变。完整 56 项已在 Chromium 全部通过，合计 1081.277 秒，静态 7 项及发行包可复现/解压持久离线均通过；三引擎专项不能扩称完整 56 项三引擎。实际进度见 [4.8.4 候选记录](releases/4.8.4.md)和[87 项输入来源记录](releases/inputs-4.8.4.json)，4.8.3 的成功记录保留为历史。
- `getTaskTextFieldsForFormSave()` 先生成正常编辑值，再按 `taskFormSession.baseline` 中浏览器实际表单值逐字段比较；未变化字段从 `editingTaskSnapshot` 保留原 `name/description/project/tags`。浏览器对输入换行的显示归一不能视作用户主动修改。恢复草稿须带回原 snapshot/baseline，并继续执行并发编辑保护；真正编辑的字段仍使用原 normalizer。
- `formatTagsInput()` 对含逗号/双引号的标签加双引号，内部引号写两次；`parseTagsInput()` 按 quoted 字段或普通逗号字段读取后交 `normalizeTaskTags()`。例如单个逗号标签写作 `"research, notes"`，引号标签写作 `"a""b"`。快速添加与 JSON `tags` 数组不变；不能将这项表单编辑语法误称为新的迁移文件格式。 标签 hint 在独立 `p` 通过 `aria-describedby` 关联，不能挤进窄屏 label。
- `setReminderSelectValue()` 为合法已有数值添加临时 option；`syncReminderSelectLabels()` 使用双语分钟说明并保留精确 value。`getTaskReminderFieldsForFormSave()` 以有限 `Number` 读取、按原 snapshot/baseline 保留未改的 inactive 值，不能将空 select 经 `parseInt()` 写成 NaN/null 或把小数截断。草稿恢复先重建 saved-value option 再回填。
- `formatQuickDateParts()` 用 `normalizeDueDateValue()` 检查 civil 日期；无年份月/日最多向前找八年中首个不早于提交当天的合法日期，年上限 9999，跨 2100 闰年例不能只加一年。显式年份不滚年，交共享 gap-forward/fold-first 解析；非法 token 留作名称，独立时间 token 保留既有语义。相对日期以实际提交时的本地日为准。
- `getRepeatLineageIndex()` 按当前任务数组建立 byId、created-from children 与 root-ID 索引；`findExistingRepeatSuccessor()` 沿显式 next/children 有向可达关系和受限 root evidence 判断后继，访问集防止环，ID 0 仍有效。完成旧任务可更新自身状态而不另建平行后继，已有后继时 Skip 不应把旧任务搬到未来形成平行条目。日期/createdAt 不是关系证据；早期 guard 的删 middle 非 root 回导仍曾 RED；最终同事务删除重接补齐后，lineage 九组与 delete 十二例已全部在三引擎通过，最终完整整合也已通过。
- `tools/check.py` 的 `atomic_report()` 在同目录临时文件写入、flush/fsync 后 `os.replace()`；新 run 在 source identity 初始化前先发布 `schema_version: 2`、UUID `run_id`、时间戳、planned_checks 和未完成/未通过状态。每个 child 前写 `current_check`，结束后记录 exit/duration、重验输入；`--keep-going` 不改变失败语义。
- 机器报告的 source 指纹从 literal `DISTRIBUTION_SOURCES` 的源映射取得；verification 覆盖工具 Python、工作流及开发依赖配置。首尾和每个程序间检查漂移，已观察到的漂移不能因后续恢复原字节而重新算通过。SIGINT/SIGTERM 记录 interrupted 并清理 child group；初始化/运行异常记录 error，SIGKILL 后可能保留 running/incomplete，不能把未完成当作成功。POSIX stdlib 生命周期回归已通过（INT130/TERM143/KILL incomplete、输入变化及恢复、原子发布、exit7/9 等），完整 56 项候选也已实际通过。

- 删除事务基于 checkpoint 同一份 `beforeTasks`，沿显式 next/created-from 图跨连续删除点重接唯一存活端点；无端点清 null，歧义分支保留 ghost，不在 cycle 的显式连通组件里重接。不使用 repeatSourceId/due/createdAt 猜端点，repeatSourceId 保持不变。single/clear 提交后从 DB 刷新再登记 Undo，正常可执行的 Undo 精确恢复删除前 metadata；tx abort/stale 保持 tasks/config/history/revision 整体一致。
- `static_syntax_test.py` 覆盖 30 个合法 JavaScript literal/regex 等语法例、真实注释拒绝和八种 scoped UTC-date mutation。lexer 修正不懂 regex 内引号的误判，日期 guard 限定目标函数，不能再依赖 quick parser 中偶然出现的全局字符串；运行时 comment-free 规则不变。
- 当前 runtime 源 22 项在运行前冻结；runner 启动捕获 65 个 verification 输入（含 requirements-dev）并经当前文件复核，总计 87 项。不能写成另有 65 个外部文件预先冻结；完成的 schema-2 report 已记录两类输入 unchanged=true、56/56 通过；单独[来源记录](releases/inputs-4.8.4.json)保留这一捕获时序、文件 map/aggregate 和原始证据绑定。

## 4.8.5 GOAL 五项验收完成与合并替换链

- 客户端完成日期为2026-10-24（北京时间），原始UTC时间戳不重写。当前app/JSON-LD/cache/package为4.8.5、资源4.36；[完整58/58报告](releases/check-results-4.8.5.json)通过、程序耗时合计1301.444秒，GOAL五项全部完成。native请求与manual-abort修复后，[integrated静态预检](releases/check-results-4.8.5-static-integrated.json)先自捕获91项并过7项，随后[第四次外部冻结](releases/frozen-inputs-4.8.5-integrated.json)固定同映射（source588b/verif7956），早于全部最终验收；起末与当前91输入一致。[来源记录](releases/inputs-4.8.5.json)绑定314份原始证据、环境及同一候选。23文件/812,056字节/SHA08bf…5a0d的两次独立构建一致，解压持久/离线及实际4.8.4档升/降/再升均过，完整身份见[4.8.5发行记录](releases/4.8.5.md)。旧成功、失败、中断及4.8.4的56项/87输入和包不改。
- 新真实 RED 在 `dbActions.mergeImportedTasks()`：merge replace 删除中间 occurrence 时未调用普通删除已有的 metadata bridge，backup/reimport 清理 dangling refs 后重新完成 old 会产生平行后继。callback 现接收 `(store, beforeTasks)`，删除后调用 `getRepeatDeletionUpdates(beforeTasks, idsToDelete)` 修复明确幸存旧链，最后写 incoming，保留导入显式受支持字段优先；checkpoint/delete/repair/incoming/revision 必须同事务。当前冻结源码十一组已在三引擎最终矩阵通过，初期修复源码的Chromium结果仍留原身份，不能用4.8.4普通delete专项代替。
- merge bridge 沿用唯一显式端点、歧义 ghost 和 cycle 保守边界，不从 due/createdAt 或 shared root 猜后继，也不重定根。`repeat_merge_playwright.py` 覆盖 replace round trip、连续删除、keep/skip/distinct、repair/incoming/checkpoint abort、stale、ambiguity 与 cycle，真实原始 RED 另行保留。
- 增强 `workspace_roundtrip_playwright.py` 保留 rootID0 四期链、九个显式 repeat refs、批量操作与全字段签名，实际下载、替换、删除恢复与完整视图。分页后的开发 10,000×6 九项检查和默认 1,000×6 preflight 均通过；更早缺关系/batch覆盖的probe与开发跑均另留。freeze3的[旧10,000×6报告](releases/workspace-4.8.5-10000.json)保留其身份；当前freeze4的[integrated九项报告](releases/workspace-4.8.5-10000-integrated.json)也全部通过，闭合GOAL1：实际JSON17,383,726字节、四期/九链接、全10,000匹配选择但100→200渲染、1,000过滤项批量持久动作/精确Undo/checkpoint及完整视图逐字段核对，起末输入未变且无page/integrity error。并行正确性跑elapsed不能充当受控性能。
- `workspace_failure_playwright.py` 默认 200×6、显式最大 10,000，八类开发小跑已三引擎通过。当前冻结源码[10,000×6完整九例](releases/storage-4.8.5-10000-integrated.json)全部通过，闭合GOAL2：受控已入队write/abort/QuotaExceededError注入保留完整tasks/config/revision/history断言，form/quick-add原页恢复、真实两窗口stale及native duplicate-key ConstraintError均过，source/tool未变、error/integrity为空。原生quota override探测未导致abort，不视为真实配额耗尽或驱逐已验证。
- `browser_matrix.py` 的 31 程序 registry 复用 check 的原子报告/中断/identity helpers；每 child 结果与日志绑定，portable relative_path/log_directory 必须随报告一起保留。仅core compatibility用1280×800/390×844，其他专项按自己范围，性能另用1280×900/390×900；FF/WK live CDP的4个engine/program覆盖组（2引擎×timezone/calendar_timezone）记not_run，不是4条单独断言。开发 core child exit0 但源/工具漂移使 overall failed 的原报告保留，不改成候选通过；fake-engine lifecycle fixtures 仅证明 driver 行为。
- 当前冻结源码[最终矩阵](browser-compatibility.md)在Chromium154.0.8037.57、Firefox153.0、WebKit26.5各31/31全过，93程序/96个probe-program日志一同保留、91输入起末及当前均匹配freeze4，闭合GOAL3。首次Firefox完整矩阵30pass/1reload timeout原报告、诊断与四context traces另存；未改源码/30s wait/原断言，完整新跑通过只属重验，首失败原因仍未定。
- 新controlled workspace harness使用CPU4×、三次、两视口；前一冻结的[桌面10,000×6报告](releases/performance-4.8.5-desktop.json)与[390×900报告](releases/performance-4.8.5-mobile.json)各42项测量及history10三次edit均通过，三份report保持各次输入未变与fixture一致。a52c事务错误修复后的87项也全过（[desktop](releases/performance-4.8.5-desktop-final.json)/[390px](releases/performance-4.8.5-mobile-final.json)/[history10](releases/performance-4.8.5-history10-final.json)），矩阵随后新增手动abort回归使source再次变化，因此已另行完成当前源码新测量，不将a52c旧成功移作当前候选。只有reload/search已有15000/5000ms预算，其余12项/history编辑保留baseline_only；history断言仅点ID/顺序/count/完整任务SHA，不能扩成所有point metadata/config原子性。两视口均桌面Chromium，受GC影响的heap不等于RSS/峰值/内存上限或实机。首次0measurement准备失败另留。GOAL五项分别收证据，不承诺后台执行。
- 当前588b源码[桌面42项](releases/performance-4.8.5-desktop-integrated.json)＋[全新390px三轮42项](releases/performance-4.8.5-mobile-resumed.json)＋[history10三次edit](releases/performance-4.8.5-history10-integrated.json)共87条已全部通过，输入起末未变且fixture一致，闭合GOAL4；[14项表](performance.md)保留测量和DOM/heap范围。首次390px在环境切换后无进程，run1的14项与run2的11项保留在[原生running/incomplete/false报告](releases/performance-4.8.5-mobile-integrated-interrupted.json)，[环境观察及保留哈希](releases/performance-4.8.5-environment-interruption.json)另存，不改原生状态、不并样或计为通过。宿主限制为4 CPU cgroup配额、32 GiB、affinity含5个logical CPUs；CPU测量为CDP4×，恢复前后两个独占窗口不能作为速度比较。

- 新原生错误契约：duplicate `add()` 请求可在 `transaction.onerror` 时已有 `request.error.name === 'ConstraintError'`，而 `transaction.error` 仍为null。旧handler直接以null reject；八处handler现保留首错、等待 `onabort` 后再reject；若已记录并发冲突，优先保留该冲突错误，确保失败处理使用完整错误与已结束的事务。新增第九专项曾三引擎过（ConstraintError/abortObserved、rollback/raw/一次提交），但matrix真实config.put→手动abort证明secondary请求AbortError被误作存储故障而关预览。现已忽略secondary AbortError、onabort的tx.error保留真正原生abort且冲突优先，dbOp request.onerror也不再早reject；原views_portability八组三引擎、10,000×6完整九例故障、最终31×3矩阵与完整58整合均通过；不能用旧受控quota注入通过代替原生事件链验证。

- 新 batch 渲染合同：list/timeline/calendar 无日期与日期详情初始 100＋Show more，batch 任意 sort 均有限；只有非 batch manual 继续全量。`getVisibleTasks()` 仍是完整当前条件匹配集，Select all matching/全选匹配项与持久动作不依 DOM 页截断。list/timeline/无日期区新增批量页聚焦 checkbox，日期详情保持新行按钮焦点；filter/search/project 的已选 ID prune 原合同保留。跨页240项、过滤后隐藏238项、manual退出与calendar/timeline最终三引擎矩阵和完整58整合均通过；当前integrated一万任务也验证全matching选择、真实持久写入/精确Undo，不能只把旧DOM全量断言删掉。
