# Task Tracer · 任务跟踪器

一个本地优先的个人任务工作台，用来记录、安排和回顾日常工作，无需账号。

[打开应用](https://todo.muquew.com/) · [下载发行包](https://todo.muquew.com/downloads/task-tracer-5.0.1.zip) · [版本发布](https://github.com/muquew/Task-Tracer/releases) · [English](README.md)

| 工作区 | 任务面板 |
| --- | --- |
| ![今天工作台](screenshots/task-list.png) | ![任务面板](screenshots/add-task.png) |

## 功能

- **今天：** 安排今日计划，完成任务，查看此前计划中未完成的任务和尚未安排的紧急待办。
- **任务：** 列表、日历、时间线，以及搜索、已有标签复用、保存视图、批量操作与归档；点击标题即可编辑。
- **项目：** 查看真实工作量、完成与归档数量，搜索项目并进入相关任务。
- **回顾：** 查看完成、逾期和近七天进展；点击完成总数或每日柱状图查看对应任务，再返回原来的回顾位置。
- **快速记录：** 文本输入、描述、子任务、截止日期、提醒和重复任务。
- **备份数据：** JSON 导出、导入预览、合并、恢复历史和 CSV 报表。
- **选择外观：** 四套主题、浅色／深色模式、中英文界面、键盘操作与响应式布局。
- **离线使用：** 数据保存在浏览器中，可按需安装为 PWA。

## 开始使用

1. 点击顶栏 **添加任务**。旁边的箭头打开快速记录，例如 `明天 20:00 阅读 #学习 /个人`。
2. 在 **今天** 安排要做的事，在 **任务** 和 **项目** 整理工作，在 **回顾** 查看进展。
3. 从侧栏底部打开 **设置与数据**，调整外观、备份、提醒、安装与更新。

快速记录支持日期、时间、`#标签` 和 `/项目`。含空格的已有名称可以直接沿用；新名称用双引号包围，例如 `阅读 /"个人 学习" #"深度 工作"`。在任务搜索中，使用 `project:"个人 学习" tag:"深度 工作"` 查找完整名称；普通单词仍可搜索任务文字。

使用 `completed:week` 搜索含今天在内的近七个本地日期完成的任务，或用 `completed:2026-11-17` 查找某一天。这些条件也包含已归档的完成记录；明确设置的状态和项目筛选仍然有效。

## 备份与恢复

- 任务保存在当前网站的浏览器存储中，没有账号、服务器备份、自动跨设备同步或共享工作区。不同浏览器配置、域名或端口使用独立的数据。
- 在 **设置与数据 → 备份与迁移** 分别导出 **任务 JSON** 与 **保存视图 JSON**。清理站点数据、换设备或降级前，将下载文件保存在浏览器之外。
- 任务 JSON 不包含保存视图、外观偏好和恢复历史；CSV 是报表，不能恢复任务。
- 恢复时先检查导入预览，再选择合并或替换。替换前导出当前任务；保存视图需单独导入。
- 本地恢复历史与任务共用浏览器存储；清除网站数据、结束隐私浏览会话或浏览器清理存储，都可能同时删除这些数据。确认下载文件已保存；草稿和恢复历史不能代替外部备份。

## 常见问题

- **更新应用：** 打开 **设置与数据 → 帮助与关于 → 检查更新**，先保存未提交内容，待更新准备好后刷新，并关闭旧应用窗口。
- **任务不见了：** 检查项目、搜索、状态及归档筛选，再确认浏览器配置和网站地址。
- **无法保存：** 先复制重要文字，或下载可用的紧急备份／草稿，再调整存储权限并重试。刷新可能丢失未保存表单和快速记录；草稿文件不能作为任务备份导入。
- **离线与安装：** 首次使用需联网完成缓存；浏览器清理存储后需重新联网。安装方式取决于浏览器与系统支持。
- **提醒：** 检查应用设置与浏览器权限；应用关闭后不保证系统级准时投递。

## 本地运行与部署

下载并完整解压发行包，或打开源码仓库，在**解压后的应用目录或仓库根目录**运行以下命令。使用应用无需安装 Node.js 依赖、构建或后端服务：

```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

打开 [localhost:8080](http://127.0.0.1:8080/)。通过 HTTP 服务访问，直接打开 `index.html` 文件不能提供完整体验。Windows 上若没有 `python3` 命令，可使用 `py -3 -m http.server 8080 --bind 127.0.0.1`。按 Ctrl+C 停止服务。

- 部署时将完整应用放在独立的 HTTPS 站点；使用 Vercel 时保留 `vercel.json`，以应用其中的安全响应头。
- 保留 service worker、语言文件和图标。域名或端口改变后，浏览器存储也会独立，需要通过 JSON 备份迁移。
- 使用下载的发行包前，对照配套 SHA-256 文件校验 ZIP。

## 开发与贡献

在 **源码仓库** 中使用 Python 3.12+、Node.js 22+；下载的应用发行包不包含开发工具。以下命令在仓库根目录的 POSIX shell 中运行：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python -m playwright install --with-deps chromium
npm run check
```

- Windows PowerShell 中先运行 `py -3 -m venv .venv`，再用 `.venv\Scripts\Activate.ps1` 激活，然后执行其余安装命令。npm 脚本使用 `python3`；若此命令不可用，可参照 `package.json` 中对应命令，用已激活环境中的 `python` 直接执行，例如 `python tools/check.py --static-only`。
- 使用 `npm run dev` 或 `npm run preview`，打开 [localhost:8080](http://127.0.0.1:8080/)。两者都直接提供当前应用文件，不含编译或热更新。修改后刷新页面；若 service worker 仍提供旧副本，可在浏览器开发者工具中注销此本地网站的 service worker，再重新加载。测试数据与个人任务分开保存。
- 修改 `styles/workspace.css` 后运行 `npm run styles`，提交 `resources/workspace.css` 前用 `npm run styles:check` 核对编译结果。

| 命令 | 范围与输出 |
| --- | --- |
| `npm run check` | 静态一致性、发行与安全约束、语法及日期语义检查，不启动浏览器。 |
| `npm test` | 完整的已注册检查，包含 Chromium 操作流程；遇到失败即停止。 |
| `npm run test:report` | 完整的已注册检查，失败后继续执行并写入 `dist/check-results.json`；有失败时仍返回非零退出码。 |
| `npm run test:browsers` | 已注册的 Chromium、Firefox 和 WebKit 操作流程，写入 `dist/browser-matrix.json` 及各程序日志。 |
| `npm run test:a11y` | 使用 Chromium 与本地 axe-core 的无障碍和语言专项检查。 |

- 运行全部浏览器前，先用 `python -m playwright install --with-deps chromium firefox webkit` 安装。按需缩小范围，例如 `npm run test:browsers -- --browser chromium --group capture --report dist/capture-chromium.json`；追加 `--list` 可只查看范围而不启动浏览器。
- 本地 Chromium 检查可先运行 `export TASK_TRACER_BROWSER_EXECUTABLE=/absolute/path/to/chromium` 指定已安装的浏览器（PowerShell：`$env:TASK_TRACER_BROWSER_EXECUTABLE = 'C:\path\to\chrome.exe'`），再执行检查命令。此设置仅影响 Chromium；CI 安装 Playwright 固定的浏览器版本。模拟手机视口不能代替真机或 Safari/iOS 验证。
- 兼容性检查，以及 Today 的历史计划与任务选择、手机筛选、输入名称、直接打开任务、标签候选和回顾历史专项，还可通过 `TASK_TRACER_CHROMIUM_EXECUTABLE`、`TASK_TRACER_FIREFOX_EXECUTABLE` 或 `TASK_TRACER_WEBKIT_EXECUTABLE` 指定所选引擎的程序。Chromium 专属值优先于旧的 `TASK_TRACER_BROWSER_EXECUTABLE` 别名；自定义程序需要的原生库路径由外部测试进程环境提供。
- 界面修改同时检查中英文、键盘操作和窄屏；导入与恢复使用独立测试配置和示例数据。
- 修改内联脚本后运行 `python tools/security_policy.py --write` 更新 CSP；修改翻译后先运行 `python tools/translation_fallback.py --write`，再更新 CSP。
- 使用 `npm run build` 打包；ZIP、其中的完整性清单和 SHA-256 校验文件位于 `dist/`。打包会检查静态文件和 CSP，不执行浏览器测试，也不会发布或部署。打包前完成相关检查，保留已发布下载包及其校验值。

## 反馈与许可

- [问题反馈与功能建议](https://github.com/muquew/Task-Tracer/issues/new/choose)：附应用版本、浏览器／系统及复现步骤。“帮助与关于”可预览并下载诊断信息，分享前检查内容，不要公开个人备份或草稿。
- 安全漏洞请按 [安全说明](https://github.com/muquew/Task-Tracer/blob/main/SECURITY.md) 私密报告。
- [LICENSE](LICENSE) 允许个人非商业使用；商业使用需事先取得 **muquew** 的书面授权。按许可分发时保留 [第三方声明](THIRD_PARTY_NOTICES.md)。
