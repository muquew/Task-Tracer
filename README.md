# Task Tracer 任务跟踪器

Task Tracer 是一个基于截止日期的任务管理 PWA。它把任务、截止时间、提醒、子任务、筛选排序和本地数据备份放在一个轻量界面里，适合个人任务规划、学习安排和周期性事项跟踪。

[在线体验](https://todo.muquew.com/)

## 功能速览

- 截止日期跟踪：按剩余时间显示安全、警告、紧急、过期、无截止日期等状态。
- 任务管理：支持新增、编辑、删除、完成/恢复任务，以及完成任务划线展示。
- 子任务：为任务添加子步骤，单独勾选完成并显示进度。
- 提醒设置：可选择截止时、提前 15 分钟、提前 1 小时、提前 1 天或不提醒。
- 搜索与筛选：按关键词搜索，按进行中、已完成、已过期、无截止日期快速筛选。
- 排序方式：支持智能排序、创建时间、截止日期、名称排序和手动拖拽排序。
- 本地数据：使用 IndexedDB 持久化，支持 JSON 导入和导出。
- PWA 能力：支持离线加载、安装到桌面或移动设备。
- 多语言与主题：内置简体中文、英文，支持明暗主题切换。
- 无障碍体验：支持键盘操作、焦点管理、读屏标签和状态播报。

## 截图

截图用于快速展示实际界面；项目功能仍以应用本身为准。

| 任务列表 | 添加任务 |
| --- | --- |
| <img src="./screenshots/task-list.png" alt="Task Tracer 任务列表界面"> | <img src="./screenshots/add-task.png" alt="Task Tracer 添加任务弹窗"> |

## 使用方式

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

## 数据与隐私

Task Tracer 默认把任务数据保存在当前浏览器的 IndexedDB 中，不需要账号，也不会把任务内容上传到服务器。更换浏览器、清理站点数据或更换设备前，请先使用导出功能备份 JSON 文件。

## 技术形态

- 单文件主应用：`index.html`
- 外置语言资源：`resources/zh-CN.json`、`resources/en.json`
- PWA Service Worker：`sw.js`
- 自动检查：静态一致性校验与 Playwright 浏览器冒烟测试

## 许可

本项目采用个人非商业使用许可。个人学习、研究和个人任务管理可以使用；商业使用、盈利性分发或商业服务集成需要获得 `muquew` 的事先书面授权。

完整条款见 [LICENSE](./LICENSE)。
