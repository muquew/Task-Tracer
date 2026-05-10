# Task Tracer 任务跟踪器

**[English README](./README.md)**

Task Tracer 是一个基于截止日期的任务管理 PWA，适合个人计划、学习安排和周期性事项跟踪。它把任务数据保存在浏览器本地，加载后支持离线使用，并围绕截止日期状态、提醒、子任务、排序和本地备份组织体验。

[在线体验](https://todo.muquew.com/)

## 功能速览

- 截止日期跟踪：显示安全、警告、紧急、已过期、已完成、无截止日期等状态。
- 任务管理：支持新增、编辑、删除、完成和恢复任务。
- 子任务：把任务拆成多个步骤，单独勾选并显示进度。
- 提醒设置：可选择不提醒、截止时、提前 15 分钟、提前 1 小时或提前 1 天。
- 搜索与筛选：按关键词搜索，按进行中、已完成、已过期、无截止日期快速筛选。
- 排序方式：支持智能排序、新创建、截止日期、名称排序和手动拖拽排序。
- 本地数据：使用 IndexedDB 持久化，支持 JSON 导入和导出。
- PWA 能力：支持应用缓存、离线加载和安装到浏览器。
- 主题与语言：支持明暗主题、简体中文和英文。
- 无障碍体验：支持键盘操作、焦点管理、读屏标签和状态播报。

## 截图

截图用于快速展示当前界面，让 GitHub 项目页更容易浏览。

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

- 主应用：`index.html`
- 语言资源：`resources/zh-CN.json`、`resources/en.json`
- PWA Service Worker：`sw.js`
- 验证：静态一致性校验与 Playwright 浏览器冒烟测试

## 许可

Task Tracer 采用个人非商业使用许可。个人任务管理、学习、研究和评估可以使用；商业使用、付费分发或集成到商业服务需要获得 `muquew` 的事先书面授权。

完整条款见 [LICENSE](./LICENSE)。
