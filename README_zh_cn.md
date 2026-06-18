<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer 图标">
</p>

<h1 align="center">Task Tracer 任务跟踪器</h1>

<p align="center"><strong>一个本地优先的个人任务工作台，用于记录、规划、例行事项、提醒和回顾。</strong></p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer">在线体验</a> ·
  <a href="./README.md">English README</a>
</p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer"><img alt="在线体验" src="https://img.shields.io/badge/Live-Demo-2563eb?style=flat-square"></a>
  <img alt="单 HTML 应用" src="https://img.shields.io/badge/App-Single%20HTML-0f766e?style=flat-square">
  <img alt="可安装 PWA" src="https://img.shields.io/badge/PWA-Installable%20%7C%20Offline-059669?style=flat-square">
  <img alt="中英文界面" src="https://img.shields.io/badge/i18n-ZH%20%7C%20EN-7c3aed?style=flat-square">
  <img alt="无障碍" src="https://img.shields.io/badge/A11y-Keyboard%20%7C%20Screen%20Reader-d97706?style=flat-square">
  <img alt="许可" src="https://img.shields.io/badge/License-Personal%20Use-475569?style=flat-square">
</p>

Task Tracer 是一个运行在浏览器中的个人任务管理应用。任务数据保存在当前设备/浏览器配置内，适合想要完整日常工作台、但不想依赖账号、服务器或云同步的人。

PWA 指 Progressive Web App。浏览器支持时，Task Tracer 可以被安装，像普通应用一样从系统入口打开，并在应用外壳完成缓存后离线加载。

## 能做什么

| 需求 | 内置支持 |
| --- | --- |
| 快速记录任务 | 完整任务弹窗、快速添加解析、URL 捕获、安装快捷捕获、分享捕获、Inbox 默认落点、描述、子任务、项目、标签、截止日期/时间和无日期任务。 |
| 组织当前工作 | 项目分组、多标签、保存智能视图、手动排序、归档和批量操作。 |
| 从不同角度规划 | 列表、日历、时间线和统计视图。 |
| 推进今天要做的事 | 今日计划、任务操作、稍后提醒、跳过本次重复、完成/归档/删除和撤销。 |
| 管理例行事项 | 每天、每周、指定星期、每月、每月最后一天和自定义天数重复；重复规则可以暂停。 |
| 提醒重要事项 | 提前提醒、重复提醒、稍后提醒、错过提醒提示，以及浏览器提醒能力限制说明。 |
| 回顾个人进展 | 完成率、进行中任务逾期率、归档数量、今日完成数、连续完成天数和近期完成趋势。 |
| 保护本地数据 | 导出/备份、备份健康、导入预览、合并/替换冲突处理、完整性校验、替换前快照，以及存储受限时的紧急备份。 |

## 截图

| 任务列表 | 添加任务 |
| --- | --- |
| <img src="./screenshots/task-list.png" alt="Task Tracer 任务列表界面"> | <img src="./screenshots/add-task.png" alt="Task Tracer 添加任务弹窗"> |

## 快速输入

快速添加可以把轻量文本解析成结构化任务字段：

```text
明天 20:00 复习英语 #学习 /个人
```

这会创建一个名为“复习英语”的任务，截止到明天 20:00，标签为“学习”，项目为“个人”。

快速添加文本里没有 `/项目` 时，任务会保存到 `Inbox`，让还没整理的想法先进入固定入口。

命令面板使用 `Ctrl/Cmd + P` 打开，可以新建任务、聚焦快速添加、切换视图、打开保存的智能视图、进入今日计划、进入批量操作、撤销最近一次任务更改、导出/备份、搜索和跳转项目。

Task Tracer 也支持直接捕获链接：

```text
https://todo.muquew.com/?capture=1
https://todo.muquew.com/?add=买牛奶
https://todo.muquew.com/?add=买牛奶&save=1
```

`capture=1` 会打开应用并聚焦快速添加。`add=` 会预填快速添加并等待确认。`save=1` 会在应用打开后立即保存。捕获参数处理后会从地址栏移除，因此刷新页面不会重复创建任务。

安装为 PWA 后，系统入口会提供 `Quick Capture` 快捷方式，打开 `./?capture=1`。支持 Web Share Target 的浏览器可以把标题、正文和 URL 分享到 Task Tracer，分享内容会进入快速添加框供确认。

## 项目、标签与搜索

项目是主要分组。一个任务属于一个项目，例如 `Inbox`、`工作`、`个人` 或某个具体计划。项目选择器可以收窄工作空间，全部项目列表会按项目分组展示可见任务。

标签是灵活的辅助标记。一个任务可以有多个标签，例如 `学习`、`设计`、`复盘`，用来连接不同项目里的同类任务。

搜索会匹配任务名称、任务描述、项目名称、标签和子任务文本。限定搜索可以和普通关键词一起使用：

| 输入 | 匹配内容 |
| --- | --- |
| `project:工作` | 项目名包含“工作”的任务。 |
| `tag:学习` 或 `#学习` | 拥有对应标签的任务。 |
| `status:active` | 进行中的未完成任务。 |
| `status:completed` | 已完成任务。 |
| `status:archived` | 已归档任务。 |
| `status:overdue` | 已过期且未完成的任务。 |
| `status:no-deadline` | 无截止日期任务。 |
| `status:repeat` | 重复任务。 |
| `due:today` | 今天截止的任务。 |
| `due:tomorrow` | 明天截止的任务。 |
| `due:week` | 未来七天内截止的任务。 |
| `due:2025-05-20` | 指定本地日期截止的任务。 |
| `due:no-deadline` | 无截止日期任务。 |
| `project:工作 tag:报告` | 同时满足两个限定条件的任务。 |

保存智能视图会记录当前搜索、项目筛选、状态筛选、排序方式和视图。它适合固定工作范围，例如逾期工作、本周学习，或某个项目的日历视图。

## 视图

| 视图 | 适合做什么 |
| --- | --- |
| 列表 | 日常执行任务，包含任务操作、子任务、提醒、状态片段、进度条、归档控制、批量操作和手动排序。 |
| 日历 | 按真实月历规划，支持上一月/下一月、上一年/下一年、回到今天、日期详情和无日期分组。 |
| 时间线 | 按日期顺序浏览即将到来的任务和已完成历史。 |
| 统计 | 查看完成率、进行中任务逾期率、归档历史、今日完成数、连续完成天数和近期趋势。 |

## 今日计划、批量操作与撤销

今日计划是轻量执行层。把任务加入今日计划不会改变项目、标签、截止日期、归档状态或重复规则，只是把它标记为今天要处理的任务。

批量操作模式会在当前可见列表中显示选择控件。选中的任务可以一起加入今日计划、标记完成、归档或删除。

撤销会恢复最近一次任务写入操作前的任务快照。它可以从顶部撤销按钮、通知条、命令面板，或在焦点不在输入框内时使用 `Ctrl/Cmd + Z` 执行。

## 重复任务与提醒

重复任务支持每天、每周、指定星期、每月、每月最后一天和自定义天数周期。重复任务可以暂停，也可以跳过本次，而不需要删除重复规则。

当浏览器支持通知且用户授予权限时，Task Tracer 可以在应用打开期间检查提醒、按设定间隔重复提醒、将提醒稍后处理，并在应用重新运行时提示错过的提醒。

浏览器提醒不是系统级闹钟。提醒是否准时投递会受到浏览器策略、操作系统行为、电池设置、标签页生命周期，以及应用是否处于打开或被浏览器唤醒状态影响。

## 导入、导出与备份

`导出/备份` 会下载完整任务 JSON，包含导出 ID、完整性校验、版本说明，并更新最近备份状态。

`导入` 会在写入前预览 JSON 文件。预览内容包括恢复检查、任务数量、导入差异、重复 ID、同名重复项、当前数据影响、完整性校验状态和同名冲突处理选项。

替换导入会在覆盖现有任务前下载导入前快照。完整性校验失败时，替换导入需要显式风险确认；合并模式仍可用于更稳妥地恢复数据。

如果浏览器存储被阻止或运行中变得不可用，Task Tracer 会进入存储不可用模式。只要页面内仍有任务内存快照，紧急备份按钮就可以在刷新或关闭页面前下载该快照。

## 安装、离线与更新

可以从应用菜单安装 Task Tracer。如果当前浏览器没有提供自动安装弹窗，同一个入口会显示桌面 Chrome/Edge、Android Chrome 和 iOS Safari 的手动安装方式。

应用外壳缓存完成后，Task Tracer 可以离线加载。当新的缓存版本准备好时，应用会显示更新提示，并提供刷新更新操作。

## 无障碍与语言

Task Tracer 提供中文和英文界面，同步页面语言，支持键盘友好的控件、有标签的图标按钮、弹窗焦点陷阱、读屏 live region 播报、减少动态效果和桌面/移动端响应式布局。

## 数据与隐私

任务数据保存在当前浏览器的 IndexedDB 中。Task Tracer 不需要账号，默认不会把任务内容上传到服务器。

更换浏览器、清理站点数据、重新安装应用或迁移设备前，请先使用 `导出/备份` 下载 JSON 文件。

## 运行方式

直接访问在线地址：

```text
https://todo.muquew.com/
```

或本地运行：

```bash
git clone https://github.com/muquew/Task-Tracer.git
cd Task-Tracer
python3 -m http.server 8080
```

然后打开：

```text
http://127.0.0.1:8080/
```

## 许可

Task Tracer 采用个人非商业使用许可。个人任务管理、学习、研究和评估可以使用；商业使用、付费分发或集成到商业服务需要获得 `muquew` 的事先书面授权。

完整条款见 [LICENSE](./LICENSE)。
