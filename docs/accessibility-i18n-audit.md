# Accessibility and i18n Audit

本文档记录 Task Tracer 的无障碍、键盘操作、读屏器语义和国际化审计基线。

## 审计范围

- 页面 landmarks、标题层级和主要区域命名。
- Header、快速添加、命令面板、菜单、语言菜单、自定义下拉、视图切换、任务卡片、日历、统计、弹窗、toast 和存储不可用状态。
- 仅键盘操作路径，包括 Tab、Shift+Tab、Escape、Enter、Space、方向键、Home 和 End。
- axe-core WCAG 2 A/AA、WCAG 2.1 A/AA 和 best-practice 扫描。
- 中英文界面、移动宽度、减弱动画环境、基础控件尺寸和横向溢出。

## 自动化命令

```bash
python3 tools/validate_static.py
python3 tools/date_semantics_test.py
/data3/wangyaokun/miniconda3/bin/conda run -n task python tools/smoke_playwright.py
/data3/wangyaokun/miniconda3/bin/conda run -n task python tools/accessibility_i18n_audit.py
```

`tools/accessibility_i18n_audit.py` 会通过 Playwright 打开真实浏览器并注入 axe-core。首次运行时如果本地没有 axe-core，会用 `npx --yes @axe-core/cli --version` 拉取到 npm 缓存。

## 当前保障

- 文档语言和方向会随语言切换同步更新。
- 主内容使用 `main` landmark，任务视图内容作为当前 tab panel。
- 视图切换使用 roving tabindex，并支持左右方向键、Home、End。
- 主菜单和语言子菜单支持菜单语义与方向键操作。
- 自定义项目、状态和排序下拉支持方向键、Enter、Space、Escape。
- 命令面板支持 `Ctrl/Cmd + P` 打开、列表候选、焦点陷阱、Escape 关闭和关闭后的焦点恢复。
- 快速添加、今日计划、批量操作、撤销和任务卡片动作都有键盘入口。
- 任务卡片暴露为 article，并关联任务名、截止日期和状态文本。
- 图标按钮有可访问名称；纯装饰 SVG 会从可访问树隐藏。
- 弹窗有 `aria-modal`、标题关联、确认内容描述和焦点陷阱。
- toast 和键盘排序反馈通过 live region 宣告。
- 统计 meter 有可访问名称，趋势柱有文本替代。
- 颜色对比度、焦点可见性、控件最小尺寸和移动端横向溢出已纳入自动审计。
- 存储不可用模式会保留可读错误状态，禁用不可保存的控件，并让重试和紧急备份保持键盘可达。

## 已知边界

- 自动化不能完全替代真实读屏器手测。发布前如需更严格验收，应使用 NVDA + Chrome/Edge、VoiceOver + Safari/Chrome、移动端 VoiceOver/TalkBack 做人工复测。
- 浏览器后台提醒能力仍受系统和浏览器策略限制，界面已用文案说明。
- 当前语言为简体中文和英文；RTL 方向同步能力已保留，但尚未加入 RTL 语言资源。

## 发布前检查

- 跑完上述四条自动化命令。
- 用键盘完成快速添加、命令面板、新增、编辑、完成、归档、批量操作、导入、导出/备份、筛选、排序、日历详情和统计跳转。
- 在亮色和暗色主题下检查焦点环、状态文本和完成任务删除线。
- 使用中英文分别检查移动端布局和弹窗滚动。
