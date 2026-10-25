---
name: Task Tracer
description: 层次清晰、便于连续操作的个人任务工作区
colors:
  primary: "#5961c6"
  primary-hover: "#4d55b5"
  on-primary: "#fff"
  accent: "#2b7367"
  success: "#287d64"
  success-text: "#216950"
  warning: "#9c5939"
  danger: "#b6374b"
  danger-text: "#a32d40"
  info-surface: "#eef0fc"
  success-surface: "#eaf5f0"
  warning-surface: "#fff0e6"
  danger-surface: "#fceef0"
  page: "#f3f5fa"
  sidebar: "#f0f2f8"
  surface: "#fff"
  surface-alt: "#f7f8fc"
  surface-raised: "#fff"
  hover: "#f0f2fa"
  active: "#e9ecff"
  overlay: "rgba(31,38,64,.42)"
  focus-ring: "rgba(89,97,198,.20)"
  text: "#263047"
  text-secondary: "#606c84"
  text-tertiary: "#657189"
  border: "#7a869d"
  border-light: "#e7eaf2"
  project-purple: "#6d58b3"
  project-ochre: "#805e2b"
  project-ochre-surface: "#faf1df"
  dark-primary: "#a7afff"
  dark-primary-hover: "#bbc1ff"
  dark-on-primary: "#1c2343"
  dark-accent: "#97d4c2"
  dark-success: "#2e8d6f"
  dark-success-text: "#97d4c2"
  dark-warning: "#f0bd9a"
  dark-danger: "#f1a9b6"
  dark-danger-text: "#f1a9b6"
  dark-info-surface: "#3b3450"
  dark-success-surface: "#2a423e"
  dark-warning-surface: "#44372f"
  dark-danger-surface: "#48303b"
  dark-page: "#181c29"
  dark-sidebar: "#1d2232"
  dark-surface: "#252b3d"
  dark-surface-alt: "#202637"
  dark-surface-raised: "#2c344a"
  dark-hover: "#2c344a"
  dark-active: "#333d66"
  dark-overlay: "rgba(9,13,24,.68)"
  dark-focus-ring: "rgba(167,175,255,.22)"
  dark-text: "#edf0fb"
  dark-text-secondary: "#b0bad0"
  dark-text-tertiary: "#a3aec5"
  dark-border: "#a0adc6"
  dark-border-light: "#363f55"
  dark-project-purple: "#c0b0ef"
  dark-project-ochre: "#e7ca95"
  dark-project-ochre-surface: "#443d30"
typography:
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.7px"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  task-title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.5
  label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "13px"
    fontWeight: 500
  metadata:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "12px"
    fontWeight: 400
rounded:
  tag: "4px"
  compact: "6px"
  control: "8px"
  navigation: "9px"
  surface: "12px"
  panel: "16px"
  pill: "999px"
spacing:
  micro: "4px"
  tight: "6px"
  xs: "8px"
  sm: "10px"
  control: "12px"
  md: "16px"
  content: "18px"
  section: "24px"
  gutter: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  navigation-active:
    backgroundColor: "{colors.active}"
    textColor: "{colors.primary}"
    rounded: "{rounded.navigation}"
    padding: "8px 12px"
  project-chip:
    backgroundColor: "{colors.info-surface}"
    textColor: "{colors.project-purple}"
    rounded: "{rounded.tag}"
    padding: "1px 6px"
  task-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
  task-menu:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    padding: "5px"
---

# Design System: Task Tracer

## Overview

**Creative North Star: "有层次的任务工作区"**

界面以持续处理真实任务为中心：侧栏确定范围，主区承载筛选与任务，日程提供辅助参照。淡色工作区底面、清晰的内容表面、轻分隔线与少量功能色形成层次；信息密度来自整齐的任务行和紧凑工具，而不是把每项内容独立做成卡片。

亮暗主题共享布局、控件和语义。中英文共享视觉系统，文字按真实长度换行；任务正文、项目名与标签不作为装饰性文案改写。丰富而克制的层次与完整组件细节支持连续操作。

**Key Characteristics:**

- 侧栏、任务表面与日程参照各有明确位置。
- 任务采用可扫描的行结构，标题、日期、项目、标签和子任务保持关联。
- 主色用于主要操作与选中状态，功能色帮助理解期限、完成与项目。
- 浮层有明确层级，键盘焦点与窄屏操作属于同一套组件行为。

本记录从 4.9.0 实际应用 [index.html](index.html) 提取，源码 SHA-256 为 c74e68e59b7705e8c22877e6a0170d5d6d6803405a49ff418549fd2a96ab3af7。数值以本文件 frontmatter 对应的源码角色为依据；dark- 前缀表示暗色主题覆盖值，组件引用默认亮色角色，运行时由源码 CSS 变量切换。此记录不代表 Impeccable 引擎或 detector 已运行。

## Colors

主色为克制的鸢尾紫，灰蓝中性色提供工作区层次，绿、赭与红只承担明确的功能或项目含义。

- **Primary：** primary 用于新增任务、选中导航、日期与焦点；primary-hover 为主要按钮悬停色；on-primary 保证主题下的按钮文字关系。
- **Secondary：** accent、success 与 success-text 支持完成、重复任务等状态；warning 与 danger 系列区分临近期限、逾期和危险操作。状态同时具有文字或图标表达。
- **项目色：** 紫、绿、赭三组颜色同时用于侧栏点、项目标签和日期事件点；它们标识项目，不表示任务紧急程度。
- **Neutral：** page 和 sidebar 形成外层，surface 承载内容，surface-alt 用于搜索、表单分组与次要控件；border-light 是行分隔，border 是需要辨认的控件轮廓。正文、辅助文字、三级文字分别使用对应 text 角色。
- **暗色主题：** 使用 dark- 对应角色；完成勾选仍使用实色绿色底与白色勾号，不能把深色主题主按钮的深色文字复用于勾选图标。

**The Semantic Color Rule.** 保留颜色与既有含义的对应关系；日期、状态和项目仍要能通过文字或图标辨认。

## Typography

全界面使用 frontmatter 的平台无衬线字体栈。Arial 是拉丁字体回退之一，其后是中文系统字体与 Noto CJK 回退；应用不依赖在线字体下载。快捷键示例使用系统 monospace。

- **Headline：** 工作区标题；窄屏降为 24px。
- **Task title / Body：** 任务名比正文加重。窄屏任务名为 14px，行高 1.6；完成任务以文字划线表达，任务行本身保持完整不透明度。
- **Label / Metadata：** 表单与菜单以 13px 为主，标签与次要元信息以 12px 为主。窄屏紧凑工具允许 11px，不能据此缩小任务正文。
- **描述：** 桌面为 13px、行高 1.8、最大 70ch；窄屏为 12px。长标题、项目、标签与描述允许换行，不把任务主体挤入隐式列。
- **数字：** 日期、计数与日程日期使用等宽数字特性，便于纵向浏览。

## Layout

桌面应用壳由 210px 侧栏与可收缩的主工作区组成。侧栏在视口内保持可滚动；顶部工具条为 70px 最小高度。主内容最大宽度为 1440px，常规边距为上下 30px/24px、左右 32px。列表主区与 280px 日程栏之间留 24px，日程栏只在列表视图且视口至少 1180px 时显示。

工作区标题旁的未来七天索引是日期入口；1000px 及以下改用日期摘要条和日程入口。1179px 及以下主内容回到单列。779px 及以下侧栏改为按钮打开的抽屉，主内容左右边距为 16px；背景主区在抽屉打开时 inert，关闭后回到触发按钮。日程通过原生 dialog 显示，不能把隐藏侧栏或日程继续留在键盘顺序中。

任务表面把工具栏、任务行和快速添加组合为一个连续区域。桌面任务行明确使用 40px / minmax(0, 1fr) / 40px 三列；窄屏使用 36px / minmax(0, 1fr) / 32px。批量模式隐藏完成按钮，主体与菜单改为两列。不要让显式 grid-column 与单列定义产生隐式轨道。

窄屏工具栏第一行是图标视图组、可收缩搜索框与保存视图按钮；保存按钮为 32px × 36px，桌面为 42px 基础尺寸。第二行容纳项目、状态、排序、批量与工具栏操作，长筛选文字可省略，但选项内容仍完整。600px 及以下表单字段、日期时间、统计及导入对比改为单列，批量操作保持两列按钮。640px 的局部规则调整清除按钮和筛选菜单对齐；旧快速添加区间规则不构成新的页面布局断点。

间距 tokens 记录源码反复使用的实际值，不要求每个组件机械套入等比尺度。

## Elevation & Depth

深度以表面色差和分隔线为主，阴影只给主要任务表面及浮起的菜单、对话框、通知。单个任务行保持平面，悬停不整体位移或抬升。

- **任务表面：** 使用 workspace-shadow 的双层轻阴影；亮暗主题采用各自的阴影颜色。
- **菜单：** 操作菜单使用 0 12px 32px 的浮层阴影，顶部总菜单为 0 12px 38px。
- **对话框：** 使用 0 24px 90px 的较深阴影；遮罩由实际 modal 状态统一承载。
- **焦点：** 通用键盘焦点为主色 2px 轮廓、偏移 2px；常用操作控件另有 4px focus-ring。文本字段聚焦时改变边框、表面并加 3px 信息色环。

实际阴影、遮罩、焦点色与动效值保存在 sidecar 的组件 CSS 或 extensions 中，不增加 frontmatter 未支持的 token 组。

## Shapes

控件以 control 圆角为基础；导航略柔和，主要任务表面与桌面对话框使用 panel 圆角。窄屏任务表面为 surface 圆角，对话框为 14px。标签小圆角，完成框更紧凑，日程点为圆形。圆角表达容器层次，不给每一任务行单独增加外框。

图标采用当前应用的 Tabler 线性 SVG：标准图标 18px，圆端、圆连接、2px 描边；紧凑工具按实际尺寸缩至 14px。图标跟随文字色，纯图标按钮必须保留可访问名称。

## Components

### Buttons and navigation

主按钮使用主色与 on-primary，基础最小高度 40px；次按钮使用次表面，图标按钮使用透明底。悬停改变表面或颜色，不平移。禁用态降低不透明度至 0.56 并保留真实 disabled。侧栏导航最小高度 42px，当前范围以 active 底色、主色文字和选中语义共同表达。

顶栏保留语言、外观、常驻撤销与菜单入口。语言为“简体中文 / English”原生 select；界面文字、可访问名称、日期格式和单复数跟随当前语言，用户内容保持原文。外观为“浅色 / 深色 / 跟随系统”，缺省为系统；系统模式响应系统变化与其他窗口的偏好变化，显式选择保持不变。主题切换只应用样式，不重建当前表单。

### Fields and form

普通字段使用 42px 最小高度、control 圆角和明确边框。搜索框使用次表面与低对比边界。标签、提示和错误各有真实文字，日期与时间各自具有可访问名称。编辑器分组使用轻微色差；桌面可成对排列，窄屏按 Layout 的规则折叠。无日期、重复、提醒与子任务继续使用实际控件，不以展示用标签替代。

装饰图标与输入文字分别留出空间：快速添加与命令搜索左侧内边距为 40px，最小高度分别为 40px、44px。任务搜索桌面使用 13px 字号、40px 最小高度与 86px 右内边距；779px 及以下使用 12px 字号、36px 最小高度与 40px 右内边距，清除按钮右距 10px，快捷键提示隐藏。快速添加窄屏字号为 12px。通用 input 规则不能覆盖这些字段的实际内边距、字号或高度。

### Task rows and chips

完成按钮的点击区域为桌面 40px，内部完成框为 20px；选中后绿底白勾。子任务使用 18px 完成框并保留可见勾号。任务标题、元信息、描述与子任务在中间列自然展开；日期保持文字形态，项目与重复用浅底标签，普通标签使用次表面。完成与归档行不通过整体透明度削弱文字。

任务更多菜单包含真实操作；首开先同步测量和定位，在视口边缘向上或向内调整。菜单明确使用 transition: none，不能给 top、left、max-height 或所有属性增加 transition，以免首次定位滑过画面或产生错误几何测量。方向键与 Home/End 移动项目，Escape 关闭并返回触发按钮。

### Calendar, dialogs and feedback

小日历与七天索引共用项目色：今日描边、选中日主色底、任务日期有点标记。小日历支持日期方向键；窄屏日程 dialog 关闭后还原日历位置并恢复焦点。主要任务编辑器、确认框和命令面板保持独立滚动与焦点管理。

通知使用内容表面与功能色图标。桌面通知位于左下方，窄屏在内容流中，打开对话框时移到上方固定位置。常驻撤销只有顶栏入口；一次操作后的短时通知可提供上下文撤销，footer 不增加常驻副本。

动效服务于操作反馈：常用颜色与表面变化使用 motion-fast（150ms ease），主题颜色变化使用 180ms ease；菜单和对话框沿用短暂出现动画。prefers-reduced-motion 下动画与 transition 压至 0.01ms，程序滚动使用 auto。任务菜单定位始终不做几何动画。

## Do's and Don'ts

### Do:

- **Do** 使用现有语义颜色及对应暗色值，让主区、侧栏与浮层保持可辨层次。
- **Do** 保持任务中间列可收缩、长文本可换行，并在批量模式切换真实列结构。
- **Do** 在中英文、亮暗主题和窄屏中保留焦点、控件名称与相同功能。
- **Do** 尊重 reduced-motion，并在浮层关闭后把焦点返回有效触发元素。

### Don't:

- **Don't** 把逐项任务改成悬浮卡片、给任务行附加位移，或用装饰盖过状态信息。
- **Don't** 将任务菜单的首次测量和定位加入 transition。
- **Don't** 用暗色主按钮文字色绘制完成勾号，或仅靠降低整行透明度表达完成。
- **Don't** 将原型尺寸、在线字体或未实现的色阶当作当前应用的设计事实。
