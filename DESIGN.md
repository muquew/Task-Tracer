---
name: Task Tracer
description: 层次清晰、便于连续操作的个人任务工作区
colors:
  primary: "#5a57c8"
  primary-hover: "#4b47b3"
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
  page: "#f4f5f9"
  sidebar: "#f0f2f8"
  surface: "#fff"
  surface-alt: "#f7f8fc"
  surface-raised: "#fff"
  hover: "#f0f2fa"
  active: "#eeedff"
  overlay: "rgba(25,33,58,.32)"
  focus-ring: "rgba(90,87,200,.22)"
  text: "#263047"
  text-secondary: "#606c84"
  text-tertiary: "#657189"
  border: "#7d8aa2"
  border-light: "#e3e7f0"
  project-purple: "#6d58b3"
  project-ochre: "#805e2b"
  project-ochre-surface: "#faf1df"
  dark-primary: "#b8b5ff"
  dark-primary-hover: "#cbc7ff"
  dark-on-primary: "#1c2141"
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
  dark-page: "#151925"
  dark-sidebar: "#1d2232"
  dark-surface: "#232b3c"
  dark-surface-alt: "#1c2332"
  dark-surface-raised: "#2d374c"
  dark-hover: "#2c344a"
  dark-active: "#34395f"
  dark-overlay: "rgba(4,9,19,.59)"
  dark-focus-ring: "rgba(184,181,255,.25)"
  dark-text: "#edf0fb"
  dark-text-secondary: "#b0bad0"
  dark-text-tertiary: "#a3aec5"
  dark-border: "#7886a1"
  dark-border-light: "#35415a"
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
    backgroundColor: "{colors.surface-raised}"
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

布局与组件语言沿用4.9.0设计基线，该历史提取源码SHA-256为 `c74e68e59b7705e8c22877e6a0170d5d6d6803405a49ff418549fd2a96ab3af7`；4.10.0导航与设置改造保留在[原版记录](docs/releases/4.10.0.md)。frontmatter现记录4.12.0候选默认Iris强调色的基础角色，dark-前缀表示暗色覆盖；四套强调色与材质规则见下文，运行时以源码CSS变量为准。[4.12.0记录](docs/releases/4.12.0.md)单独跟踪本轮实现与验证。本设计文件不代表Impeccable引擎或detector已运行。

## Colors

默认主色为鸢尾紫；Iris、Ocean、Pine、Berry四套强调色独立于浅色／深色／跟随系统模式，用于主要按钮、选中项和键盘焦点。功能状态与项目色保持自己的含义。frontmatter中的 `accent` 是既有绿色功能角色，用户的强调色偏好由 `data-accent` 覆盖 primary 等角色。

- **Primary：** primary 用于新增任务、选中导航、日期与焦点；primary-hover 为主要按钮悬停色；on-primary 保证主题下的按钮文字关系。
- **Secondary：** accent、success 与 success-text 支持完成、重复任务等状态；warning 与 danger 系列区分临近期限、逾期和危险操作。状态同时具有文字或图标表达。
- **项目色：** 紫、绿、赭三组颜色同时用于侧栏点、项目标签和日期事件点；它们标识项目，不表示任务紧急程度。
- **Neutral：** page 和 sidebar 形成外层，surface 承载内容，surface-alt 用于搜索、表单分组与次要控件；border-light 是行分隔，border 是需要辨认的控件轮廓。正文、辅助文字、三级文字分别使用对应 text 角色。
- **暗色主题：** 使用 dark- 对应角色；完成勾选仍使用实色绿色底与白色勾号，不能把深色主题主按钮的深色文字复用于勾选图标。

**The Semantic Color Rule.** 保留颜色与既有含义的对应关系；日期、状态和项目仍要能通过文字或图标辨认。

| 强调色偏好 | 浅色 primary / hover / on-primary / active | 深色 primary / hover / on-primary / active |
| --- | --- | --- |
| Iris／鸢尾紫 | `#5A57C8` / `#4B47B3` / `#FFFFFF` / `#EEEDFF` | `#B8B5FF` / `#CBC7FF` / `#1C2141` / `#34395F` |
| Ocean／海湾蓝 | `#2563A9` / `#1E518C` / `#FFFFFF` / `#E9F1FB` | `#9CCAFF` / `#BEDCFF` / `#152B43` / `#233E59` |
| Pine／松柏绿 | `#24715C` / `#1C5E4B` / `#FFFFFF` / `#E6F3EC` | `#8ED9BA` / `#AFF0D1` / `#15352A` / `#23463C` |
| Berry／莓果红 | `#A94565` / `#913955` / `#FFFFFF` / `#FAECF0` | `#F2AAC2` / `#FFD0DE` / `#402332` / `#543345` |

强调色与亮暗模式均为本地偏好；切换时只应用样式，保留输入、当前任务上下文及离线能力。成功、警告、逾期和危险操作继续使用固定语义色。

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

顶部统一“添加任务”展开快速记录，再通过“更多选项”进入完整表单；内容页保留工具栏与任务行。桌面任务行明确使用 40px / minmax(0, 1fr) / 40px 三列；窄屏使用 36px / minmax(0, 1fr) / 32px。批量模式隐藏完成按钮，主体与菜单改为两列。不要让显式 grid-column 与单列定义产生隐式轨道。

列表、日历、时间线、统计从可折叠工具栏提升为一级导航：桌面位于侧栏，779px及以下位于常驻底栏，图标与文字同时保留。主导航不随搜索／筛选工具折叠，也不在进入设置后失去返回任务的能力。移动内容、回到顶部与更新提示为底栏和安全区留出空间；底栏处于导航抽屉和模态遮罩之下。

窄屏任务工具栏保留可收缩搜索框与保存视图入口，项目、状态、排序、批量与工具栏操作保持紧凑排列，长筛选文字可省略，但选项内容仍完整。600px及以下表单字段、日期时间、统计及导入对比改为单列，批量操作保持两列按钮。640px的局部规则调整清除按钮和筛选菜单对齐；旧快速添加区间规则不构成新的页面布局断点。

“设置与数据”是与任务区并列的独立工作区，使用已有表面、文字、边界和功能色。外观与语言、备份与迁移、提醒与安装、任务维护、帮助与关于五个分类选择实际面板，本页内保留当前分类；手机分类导航为可横向滚动的单行。备份、恢复优先，CSV、视图迁移与数据安全归入其他数据工具。返回任务保留原任务区DOM及草稿、搜索、筛选和选择状态。

间距 tokens 记录源码反复使用的实际值，不要求每个组件机械套入等比尺度。

## Elevation & Depth

深度以表面色差和分隔线为主，任务内容与表单保持稳定可读的实色底。玻璃仅用于顶栏、快速记录层与手机底栏等需要交代遮挡关系的界面层；单个任务行保持平面，悬停不整体位移或抬升。

- **任务表面：** 使用 workspace-shadow 的双层轻阴影；亮暗主题采用各自的阴影颜色。
- **菜单：** 任务操作、下拉、自定义选择与命令面板使用 surface-raised，与母表面形成明确层次；亮色菜单阴影为 0 12px 32px 加较轻的第二层，暗色使用独立阴影。全局设置使用独立工作区。
- **对话框：** 使用 surface-raised 与 0 24px 70px 阴影。模态、抽屉与原生日程dialog使用统一语义的scrim，背景模糊5px；日程dialog不再叠一层页面遮罩。玻璃层模糊12px，不支持模糊或偏好降低透明度时使用实色回退。
- **焦点：** 每个控件只保留一个清晰的主色2px轮廓、偏移2px，不叠加光环与第二道强调色描边。快速记录只在输入包裹层显示焦点轮廓，内部input不重复描边；菜单定位不因焦点变化跳动。

实际阴影、遮罩、焦点色与动效值保存在 sidecar 的组件 CSS 或 extensions 中，不增加 frontmatter 未支持的 token 组。

## Shapes

控件以 control 圆角为基础；导航略柔和，主要任务表面与桌面对话框使用 panel 圆角。窄屏任务表面为 surface 圆角，对话框为14px。圆形用于任务完成、关闭等独立动作，方形用于批量选择；标签保持小圆角，日程点为圆形。形状表达操作与容器角色，不给每一任务行单独增加外框。

图标采用当前应用的 Tabler 线性 SVG：标准图标 18px，圆端、圆连接、2px 描边；紧凑工具按实际尺寸缩至 14px。图标跟随文字色，纯图标按钮必须保留可访问名称。

## Components

### Buttons and navigation

主按钮使用主色与 on-primary，基础最小高度 40px；次按钮使用次表面，图标按钮使用透明底。悬停改变表面或颜色，不平移。禁用态降低不透明度至 0.56 并保留真实 disabled。侧栏导航最小高度 42px，当前范围以 active 底色、主色文字和选中语义共同表达。

顶栏保留统一添加、可用时显示的撤销与设置入口，侧栏也提供设置入口。语言、浅色／深色／跟随系统及四种强调色控件只在“外观与语言”；界面文字、可访问名称、日期格式和单复数跟随语言，用户内容保持原文。系统模式响应系统变化与其他窗口偏好，显式选择保持不变；偏好切换只应用样式，不重建当前表单。

四视图是原生导航按钮，当前任务视图以可见选中样式及 `aria-current="page"` 共同表达；任务内容使用有名称的region。进入设置时不保留一个指向隐藏任务内容的选中tab。设置不占用四视图的持久化字段，不改变保存视图格式。

### Fields and form

普通字段使用 42px 最小高度、control 圆角和明确边框。搜索框使用次表面与低对比边界。标签、提示和错误各有真实文字，日期与时间各自具有可访问名称。编辑器分组使用轻微色差；桌面可成对排列，窄屏按 Layout 的规则折叠。无日期、重复、提醒与子任务继续使用实际控件，不以展示用标签替代。

装饰图标与输入文字分别留出空间：快速添加与命令搜索左侧内边距为 40px，最小高度分别为 40px、44px。任务搜索桌面使用 13px 字号、40px 最小高度与 86px 右内边距；779px 及以下使用 12px 字号、36px 最小高度与 40px 右内边距，清除按钮右距 10px，快捷键提示隐藏。快速添加窄屏字号为 12px。通用 input 规则不能覆盖这些字段的实际内边距、字号或高度。

### Task rows and chips

任务完成按钮的点击区域为桌面40px，内部20px圆形控件选中后绿底白勾；批量选择保持方形，子任务18px控件保留独立完成状态与可见勾号。任务标题、元信息、描述与子任务在中间列自然展开；日期保持文字形态，项目与重复用浅底标签，普通标签使用次表面。完成与归档行不通过整体透明度削弱文字。

任务更多菜单包含真实操作；首开先同步测量和定位，在视口边缘向上或向内调整。菜单明确使用 transition: none，不能给 top、left、max-height 或所有属性增加 transition，以免首次定位滑过画面或产生错误几何测量。方向键与 Home/End 移动项目，Escape 关闭并返回触发按钮。

### Calendar, dialogs and feedback

小日历与七天索引共用项目色：今日描边、选中日主色底、任务日期有点标记。小日历支持日期方向键；窄屏日程 dialog 关闭后还原日历位置并恢复焦点。主要任务编辑器、确认框和命令面板保持独立滚动与焦点管理。

反馈使用内容表面与对应语义图标，成功／信息为status，警告／错误为alert。弹窗内发生的反馈进入当前弹窗的流内区域，标题与关闭控件保持可见；打开新弹窗先结束旧反馈上下文。任务操作反馈可在应用反馈层提供短时撤销；常驻撤销仍由顶栏按可用状态显示。

动效服务于操作反馈：常用按钮颜色与表面变化使用180ms，按下时可轻移1px；任务行悬停保持原位，菜单定位不做几何动画。对话框使用短暂淡入与8px进入位移。prefers-reduced-motion下关闭按下位移并压低动画与transition时长，程序滚动使用auto。

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


## Whole-site usability direction — 4.11.0

- One global capture entry, available from a stable header. Content pages do not each repeat a permanent task-entry form. Quick capture and full editing share context without losing a draft.
- A page shows tools for its purpose. Statistics is for reading progress, calendar is for dates and an agenda, task lists are for execution. Page titles and selected navigation agree.
- Preferences have one home in Settings. Settings categories select panels rather than jumping down a long document; returning to tasks preserves context.
- Common task fields come first. Advanced fields and detailed clock guidance remain available through progressive disclosure, and existing nondefault values remain visible when editing.
- A mobile calendar presents a compact month and readable selected-day agenda; statistics prioritizes scanability instead of stacking desktop-sized cards.
- Empty states direct the next real action. Batch actions follow selection. Saved-view names outrank condition summaries. Feedback remains visible where the action happened.
- Evaluate by performing complete user tasks and inspecting actual renders. Protective regression tests follow the experience review; counts are not a proxy for usability.

## Functional completeness — 4.12.0

- 统计优先回答逾期、今天截止、无日期待办三个实际工作问题，零数量入口禁用；保留项目与搜索交集。下钻提供返回来源，用户改范围后清理旧返回上下文。七日回顾使用保留任务的真实完成时间，含已归档完成记录；当前任务详情按需展开。
- 批量先选择对象，再提供完成与有文字的更多操作。移到项目展示数量、允许已有或新项目并支持撤销；单条与批量归档规则一致。重复后继不继承上一期手动今日计划，稍后提醒持续呈现时间和通知状态。
- 相同条件的保存视图明确使用更新标题、已有名称与更新动作。导入方式、实际新增／跳过／替换／保留及结果数量随选择同步；替换前下载快照，恢复显示当前→目标对照。任务维护先展示整个工作区符合条件的数量，零数量禁用。
- 成功反馈不能代替持久状态，数字不能代替范围说明。危险操作具名，确认动作描述实际影响；普通成功、警告与错误使用各自图标和可访问语义。
