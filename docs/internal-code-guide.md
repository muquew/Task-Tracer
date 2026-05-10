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
   - Controls bar 放搜索、筛选、排序。
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
  - `dueDate`: UTC ISO 字符串或 `null`。
  - `reminderOffset`: 提前提醒分钟数，`-1` 表示不提醒。
  - `subtasks`: 子任务数组，每个子任务有唯一 `id`。
  - `completed`: 完成状态。
  - `createdAt`: 创建时间。
  - `order`: 手动排序权重。

- 运行时状态:
  - `filter`、`sort`、`searchQuery`: 当前列表视图条件。
  - `editingTaskId`: 当前编辑任务 ID。
  - `tempSubtasks`、`editingSubtaskIndex`: 弹窗内的临时子任务草稿。
  - `notificationsEnabled`、`notifiedTasks`、`pendingNotificationKeys`: 通知投递状态。
  - `currentLanguage`、`translations`、`dateTimeFormatters`: i18n 与本地化缓存。

## 初始化流程

`initApp()` 的顺序很重要：

1. `cacheDOM()` 缓存节点。
2. `loadTranslations()` 加载语言文件。
3. `createLangButtons()` 创建语言菜单项。
4. `initDB()` 初始化 IndexedDB。
5. `loadSettings()` 恢复语言、通知和已提醒签名。
6. `initLanguage()` 同步 `lang`、`dir` 和页面文案。
7. `loadNormalizedTasks()` 读取任务并修复历史子任务重复 ID。
8. 必要时 `addSampleTasks()` 添加示例。
9. `bindEvents()` 绑定事件。
10. `renderTaskList()` 首次渲染。
11. `startProgressTimer()` 启动倒计时刷新。

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
- `bindSearchEvents()`: 搜索和清除完成任务入口。
- `bindNotificationEvents()`: 通知按钮。
- `bindMenuEvents()`: 主菜单、语言子菜单、导入导出。
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
- `handleClearCompleted()`: 批量清除已完成任务。

### 子任务

- `cloneSubtasks(subtasks)`: 浅克隆子任务。
- `cloneSubtasksWithUniqueIds(subtasks)`: 克隆并保证 ID 唯一。
- `createUniqueNumericId(usedIds)`: 生成唯一数字 ID。
- `normalizeUniqueNumericId(value, usedIds)`: 保留合法唯一 ID，否则生成新 ID。
- `createUniqueSubtaskId(subtasks)`: 新增草稿子任务时生成 ID。
- `normalizeTaskSubtaskIds(tasks)`: 读取历史数据时修复子任务 ID。
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
- `getTaskReminderOffset(task)`: 读取任务提醒偏移。
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
- `patchTaskList(tasks)`: 增量更新列表。
- `createTaskNode(task)`: 克隆任务模板。
- `renderTaskItem(el, task)`: 单任务渲染总入口。
- `getTaskRenderStatus(task, t)`: 获取任务状态对象。
- `renderTaskHeader(el, task, statusObj, t)`: 标题、提醒、截止日期。
- `renderTaskDescription(el, task)`: 描述区域。
- `renderTaskProgress(el, task, statusObj)`: 进度条。
- `renderTaskStatus(el, task, statusObj, timeLeft)`: 状态文字。
- `renderReminderIcon(el, task)`: 提醒图标。
- `renderTaskActionTitles(el, task, t)`: 操作按钮标签。
- `renderTaskToggleButton(button, completed)`: 完成/恢复图标切换。
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
- `setDeadlineControls({ enabled, date, time, reminderOffset })`: 截止日期控件联动。
- `closeDialog()`: 关闭并清理弹窗。
- `resetDialogToFormMode()`: 从确认模式恢复表单模式。
- `utils.confirm(title, msg, onConfirm)`: 复用任务弹窗显示确认流程。
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
- `runTaskAction(action, taskId)`: 执行完成、编辑、删除。
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

### 导入、导出、示例与定时器

- `startProgressTimer()`: 启动定时刷新。
- `refreshTaskTimers()`: 局部刷新倒计时和状态样式。
- `handleVisibilityChange()`: 页面恢复时刷新。
- `exportTasks()`: 导出 JSON。
- `importTasks(file)`: 读取并确认导入 JSON。
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
