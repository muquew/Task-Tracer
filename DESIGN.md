---
name: Task Tracer
description: 层次清晰、便于连续操作的个人任务工作区
colors:
  primary: "#5e527f"
  primary-hover: "#4c3f6a"
  on-primary: "#ffffff"
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
  page: "#dddce7"
  sidebar: "#312d48"
  header: "#d3d2e0"
  surface: "#eeeff5"
  surface-alt: "#e4e4ed"
  surface-raised: "#f9f8fc"
  hover: "#dfddeb"
  active: "#d9d2e7"
  overlay: "rgba(25,33,58,.32)"
  focus-ring: "rgba(94,82,127,.22)"
  text: "#312b43"
  text-secondary: "#55516b"
  text-tertiary: "#5a556f"
  border: "#867b98"
  border-light: "#c5c2d4"
  project-purple: "#6d58b3"
  project-ochre: "#805e2b"
  project-ochre-surface: "#faf1df"
  dark-primary: "#c2b0e2"
  dark-primary-hover: "#d3c3eb"
  dark-on-primary: "#271e35"
  dark-accent: "#97d4c2"
  dark-success: "#38a17b"
  dark-success-text: "#97d4c2"
  dark-warning: "#f0bd9a"
  dark-danger: "#f1a9b6"
  dark-danger-text: "#f1a9b6"
  dark-info-surface: "#3b3450"
  dark-success-surface: "#2a423e"
  dark-warning-surface: "#44372f"
  dark-danger-surface: "#48303b"
  dark-page: "#211e2e"
  dark-sidebar: "#191724"
  dark-header: "#292536"
  dark-surface: "#2d2a3b"
  dark-surface-alt: "#242132"
  dark-surface-raised: "#373246"
  dark-hover: "#403a51"
  dark-active: "#463957"
  dark-overlay: "rgba(4,9,19,.59)"
  dark-focus-ring: "rgba(194,176,226,.22)"
  dark-text: "#f1eef8"
  dark-text-secondary: "#beb7cd"
  dark-text-tertiary: "#b0a7c2"
  dark-border: "#8b809e"
  dark-border-light: "#514b64"
  dark-project-purple: "#c0b0ef"
  dark-project-ochre: "#e7ca95"
  dark-project-ochre-surface: "#443d30"
  nav-text: "#f0edf7"
  nav-secondary: "#d2c9df"
  nav-hover: "#433e5b"
  nav-selected: "#574e70"
  nav-selected-text: "#ffffff"
  nav-border: "#887d9d"
  nav-focus: "#d4c1f3"
  dark-nav-text: "#f0edf7"
  dark-nav-secondary: "#d2c9df"
  dark-nav-hover: "#332e43"
  dark-nav-selected: "#4b405f"
  dark-nav-selected-text: "#ffffff"
  dark-nav-border: "#887d9d"
  dark-nav-focus: "#d4c1f3"
typography:
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "27px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.55px"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  task-title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "14px"
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
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  input:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  navigation-active:
    backgroundColor: "{colors.nav-selected}"
    textColor: "{colors.nav-selected-text}"
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
    rounded: "14px"
  task-menu:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    padding: "7px"
---

# Design System: Task Tracer

**4.13.1实现规范。** 本文件依据当前应用源码 `428dd0489d3002883848bbaeb71d1c8dd86bcc88993bf9c81e26a8bafeb176a9` 维护完整主题、空间和组件角色。工程验证与发布状态由本版记录单独说明；本文件不代表Impeccable引擎或detector已运行。

## Overview

**Creative North Star: "有层次的任务工作区"**

界面以持续处理真实任务为中心：深色导航确定工作范围，主题底面组织上下文页头、任务工作页与日程tray。四套工作区主题各自提供画布、页头、内容、内嵌区、浮层、文字与控件颜色；内容层保持稳定可读，任务行与元信息以紧凑节奏建立关联。

亮暗主题共享布局、控件和语义。中英文共享视觉系统，文字按真实长度换行；任务正文、项目名与标签不作为装饰性文案改写。丰富而克制的层次与完整组件细节支持连续操作。

**Key Characteristics:**

- 侧栏、任务表面与日程参照各有明确位置。
- 任务采用可扫描的行结构，标题、日期、项目、标签和子任务保持关联。
- 主色用于主要操作与选中状态，功能色帮助理解期限、完成与项目。
- 浮层有明确层级，键盘焦点与窄屏操作属于同一套组件行为。

布局与任务能力延续既有工作区，4.13.0重做整套主题、空间关系与组件材质。frontmatter记录默认雾紫／Iris的完整基础角色，dark-表示暗色覆盖；侧栏使用独立nav角色，不能套用内容区文字。四套主题的明确数值见下表，运行时以源码CSS为准。[本轮任务书](THEME_BRIEF.md)与[4.13.0记录](docs/releases/4.13.0.md)单独跟踪实现、审读与发布状态。4.12.0及更早版本的证据保留原版本身份。

## Colors

工作区主题为雾紫／Iris、海湾／Ocean、松林／Pine、莓暮／Berry。每套均为完整浅色与深色配色，覆盖导航、画布、页头、内容、内嵌区、浮层、文字、分隔和控件。工作区主题独立于浅色／深色／跟随系统外观；功能状态保留各自语义。frontmatter中的 `accent` 是既有绿色功能角色，兼容偏好key `accent` 及枚举 `iris/ocean/pine/berry` 现在选择完整主题。

- **Primary：** primary、primary-hover与on-primary用于主要操作及内容区选中状态；深导航使用自己的nav-selected、nav-selected-text与nav-focus。
- **Secondary：** accent、success 与 success-text 支持完成、重复任务等状态；warning 与 danger 系列区分临近期限、逾期和危险操作。状态同时具有文字或图标表达。
- **项目色：** 紫、绿、赭三组颜色同时用于侧栏点、项目标签和日期事件点；它们标识项目，不表示任务紧急程度。
- **Surface：** page组织工作区，sidebar承载深导航，theme-header形成上下文页头；surface承载任务或回顾，surface-alt组织工具、字段与日程tray，surface-raised区分菜单和弹窗。正文、辅助文字、控件边界与分隔使用本主题对应角色。
- **勾选与完成：** 普通选择／安全确认复选框使用primary底与本主题on-primary勾号（`--checkbox-check`）；子任务使用success底与固定白色勾号（`--success-check`），父任务完成也使用success与白色图标。success在浅色为`#287D64`、深色为`#38A17B`，不随工作区主题改变。

**The Semantic Color Rule.** 保留颜色与既有含义的对应关系；日期、状态和项目仍要能通过文字或图标辨认。

| 主题／外观 | page | sidebar | header | content | inset | raised |
| --- | --- | --- | --- | --- | --- | --- |
| 雾紫／浅色 | `#DDDCE7` | `#312D48` | `#D3D2E0` | `#EEEFF5` | `#E4E4ED` | `#F9F8FC` |
| 雾紫／深色 | `#211E2E` | `#191724` | `#292536` | `#2D2A3B` | `#242132` | `#373246` |
| 海湾／浅色 | `#D8E4E9` | `#213B48` | `#CBDDE4` | `#EBF2F5` | `#DDE9EF` | `#F6FAFC` |
| 海湾／深色 | `#182C37` | `#12232C` | `#1D3542` | `#233E4C` | `#1B3240` | `#2E4B59` |
| 松林／浅色 | `#DCE6DF` | `#243C36` | `#CDDDD2` | `#EDF3ED` | `#DFEADF` | `#F7FBF6` |
| 松林／深色 | `#1C3027` | `#14261F` | `#233D30` | `#294437` | `#20382D` | `#335040` |
| 莓暮／浅色 | `#E9DEE3` | `#4C303E` | `#DFC9D3` | `#F5EDF0` | `#ECDFE6` | `#FCF6F8` |
| 莓暮／深色 | `#382631` | `#2E1C27` | `#402B39` | `#47333F` | `#3E2936` | `#543F4C` |

| 主题／外观 | text | secondary | tertiary | controlBorder | separator | hover | selected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 雾紫／浅色 | `#312B43` | `#55516B` | `#5A556F` | `#867B98` | `#C5C2D4` | `#DFDDEB` | `#D9D2E7` |
| 雾紫／深色 | `#F1EEF8` | `#BEB7CD` | `#B0A7C2` | `#8B809E` | `#514B64` | `#403A51` | `#463957` |
| 海湾／浅色 | `#243C49` | `#455D6B` | `#49616F` | `#698696` | `#BFCDD5` | `#D3E3EB` | `#C3DDE9` |
| 海湾／深色 | `#E8F4F9` | `#BDD5E1` | `#B5CDDA` | `#789AAA` | `#456372` | `#355969` | `#2D5367` |
| 松林／浅色 | `#243C31` | `#466252` | `#4C6455` | `#6C8877` | `#C1D1C5` | `#D9E6DB` | `#D0E4D7` |
| 松林／深色 | `#EFF7EE` | `#C5DBCA` | `#BBD3BE` | `#7DA58A` | `#476750` | `#3D5E49` | `#35583F` |
| 莓暮／浅色 | `#492C39` | `#684A59` | `#6D505E` | `#977383` | `#D5BDC8` | `#E8D5DF` | `#EAD0DB` |
| 莓暮／深色 | `#F9EDF3` | `#D7BCCB` | `#DAC0CE` | `#B18B9F` | `#77576A` | `#614657` | `#6A4358` |

| 主题／外观 | primary | primaryHover | onPrimary | navText | navSecondary | navHover | navSelected | navSelectedText | navBorder | navFocus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 雾紫／浅色 | `#5E527F` | `#4C3F6A` | `#FFFFFF` | `#F0EDF7` | `#D2C9DF` | `#433E5B` | `#574E70` | `#FFFFFF` | `#887D9D` | `#D4C1F3` |
| 雾紫／深色 | `#C2B0E2` | `#D3C3EB` | `#271E35` | `#F0EDF7` | `#D2C9DF` | `#332E43` | `#4B405F` | `#FFFFFF` | `#887D9D` | `#D4C1F3` |
| 海湾／浅色 | `#235F7D` | `#1C4D65` | `#FFFFFF` | `#EAF4F8` | `#CBDDE5` | `#2B4B5B` | `#365F70` | `#FFFFFF` | `#648798` | `#B8E3F7` |
| 海湾／深色 | `#A7D5ED` | `#C7E5F4` | `#173344` | `#EAF4F8` | `#CBDDE5` | `#25414E` | `#305466` | `#FFFFFF` | `#648798` | `#B8E3F7` |
| 松林／浅色 | `#2C6650` | `#22543F` | `#FFFFFF` | `#EFF6EF` | `#CFDED0` | `#304F43` | `#3D604D` | `#FFFFFF` | `#6E917B` | `#BEE5C5` |
| 松林／深色 | `#B0DBB6` | `#CEE9D0` | `#203C2A` | `#EFF6EF` | `#CFDED0` | `#284535` | `#345841` | `#FFFFFF` | `#6E917B` | `#BEE5C5` |
| 莓暮／浅色 | `#87415B` | `#71354C` | `#FFFFFF` | `#F8EDF2` | `#E5D0DA` | `#603E4E` | `#775061` | `#FFFFFF` | `#AC8297` | `#F1C1D6` |
| 莓暮／深色 | `#E7B1CA` | `#F4D0E2` | `#452435` | `#F8EDF2` | `#E5D0DA` | `#4B3040` | `#644254` | `#FFFFFF` | `#AC8297` | `#F1C1D6` |

nav-text、nav-secondary、nav-hover、nav-selected、nav-selected-text、nav-border与nav-focus只服务深导航；内容区与手机底栏使用各自表面和文字角色。主题切换保留任务、输入、草稿和批量选择；原有偏好枚举及跨窗口同步方式保持，DB2／任务JSON2.4／视图1.1和1.0导入兼容不变。

## Typography

全界面使用 frontmatter 的平台无衬线字体栈。Arial 是拉丁字体回退之一，其后是中文系统字体与 Noto CJK 回退；应用不依赖在线字体下载。快捷键示例使用系统 monospace。

- **Headline：** 桌面工作区标题27px、700，字距-0.55px；窄屏为24px。
- **Task title / Body：** 任务名14px、600，窄屏行高1.6；完成任务以文字划线表达，任务行本身保持完整不透明度。
- **Label / Metadata：** 表单与菜单以 13px 为主，标签与次要元信息以 12px 为主。窄屏紧凑工具允许 11px，不能据此缩小任务正文。
- **描述：** 桌面为 13px、行高 1.8、最大 70ch；窄屏为 12px。长标题、项目、标签与描述允许换行，不把任务主体挤入隐式列。
- **数字：** 日期、计数与日程日期使用等宽数字特性，便于纵向浏览。

## Layout

桌面应用壳由228px深导航与可收缩主工作区组成；顶栏最小高度62px，主内容最大宽度1480px，常规内边距20px／24px。桌面上下文页头使用主题header色面；任务工作页与278px日程tray成组，相隔20px。统计的三项工作入口横向成带，回顾与项目安排在至少1180px时并列。

工作区标题旁的未来七天索引是日期入口；1000px及以下改用日期摘要条和日程入口。1179px及以下主内容回到单列。779px及以下侧栏改为抽屉，主内容左右内边距14px，顶栏高60px；手机页头去掉独占色块与最小高度。抽屉打开时背景主区inert，关闭后回到触发按钮；日程使用原生dialog。

顶部统一“添加任务”直接打开完整表单，旁边箭头提供快速记录，“完整表单”接续草稿；内容页保留工具栏与任务行。任务行将完成、正文与更多操作分列，批量模式切换为选择对象的列结构。在至少1180px的列表中，截止日期与状态对齐右侧，描述与子任务仍可跨正文区域完整展开。

列表、日历、时间线、统计从可折叠工具栏提升为一级导航：桌面位于侧栏，779px及以下位于常驻底栏，图标与文字同时保留。主导航不随搜索／筛选工具折叠，也不在进入设置后失去返回任务的能力。移动内容、回到顶部与更新提示为底栏和安全区留出空间；底栏处于导航抽屉和模态遮罩之下。

窄屏任务工具栏保留可收缩搜索框与保存视图入口，项目、状态、排序、批量与工具栏操作保持紧凑排列，长筛选文字可省略，但选项内容仍完整。600px及以下表单字段、日期时间、统计及导入对比改为单列，批量操作保持两列按钮。640px的局部规则调整清除按钮和筛选菜单对齐；旧快速添加区间规则不构成新的页面布局断点。

“设置与数据”是与任务区并列的独立工作区，使用已有表面、文字、边界和功能色。外观与语言、备份与迁移、提醒与安装、任务维护、帮助与关于五个分类选择实际面板，本页内保留当前分类；手机分类导航为可横向滚动的单行。备份、恢复优先，CSV、视图迁移与数据安全归入其他数据工具。返回任务保留原任务区DOM及草稿、搜索、筛选和选择状态。

间距 tokens 记录源码反复使用的实际值，不要求每个组件机械套入等比尺度。

## Elevation & Depth

深度以完整主题的色面、分组和一次清晰的层叠建立。顶栏与手机底栏使用实色主题表面，任务与表单保持可读内容底；菜单与弹窗使用raised表面和对应阴影。单个任务行保持平面，不用透明效果、装饰纹理或空容器代替结构。

- **任务表面：** 工具区与组标题使用inset，任务区使用content，日程tray统一成组；任务行hover轻微改变表面，内容不整体抬升。
- **菜单：** 任务操作、下拉、自定义选择与命令面板使用 surface-raised，与母表面形成明确层次；亮色菜单阴影为 0 12px 32px 加较轻的第二层，暗色使用独立阴影。全局设置使用独立工作区。
- **对话框：** raised页头与操作栏包围content工作面，普通字段使用inset、聚焦字段使用raised。模态、抽屉与日程共用5px模糊scrim，日程dialog不叠第二层页面遮罩；降低透明度或不支持模糊时使用实色回退。弹窗阴影为0 24px 70px，单个表面只浮起一次。
- **焦点：** 内容字段与常用操作使用主色2px轮廓、偏移2px；深导航改用nav-focus，主题预览卡片偏移3px。快速记录只在输入包裹层显示焦点，内部input不重复描边。字段与任务复选框不叠加强调色阴影，菜单定位不因焦点改变而移动。

实际阴影、遮罩、焦点与动效规则记录在应用内联CSS；frontmatter列出默认雾紫主题和常用组件角色，正文表格保留四主题亮暗覆盖。表面颜色、交互状态和布局共同组成视觉系统。

## Shapes

控件以control圆角为基础；桌面任务表面14px、窄屏12px，对话框桌面16px、窄屏14px，任务菜单12px。圆形用于父任务完成、关闭等独立动作，方形用于批量选择；子任务保留18px完成控件。标签小圆角、日程点圆形，不给每一任务行增加独立外框。

图标采用当前应用的 Tabler 线性 SVG：标准图标 18px，圆端、圆连接、2px 描边；紧凑工具按实际尺寸缩至 14px。图标跟随文字色，纯图标按钮必须保留可访问名称。

## Components

### Buttons and navigation

主按钮使用primary与on-primary，基础最小高度40px；默认双层轻阴影形成raised，hover切primary-hover并上移1px，pressed下移1px并缩短阴影。次按钮使用raised底、轻边界与低阴影，hover切hover底并取消阴影。文字／图标按钮保持轻表面，危险操作沿用危险语义。disabled使用真实禁用状态与0.56不透明度。侧栏当前范围使用nav-selected与nav-selected-text，焦点使用nav-focus；今日计划与保存视图的图标继承所在导航状态的颜色。

顶栏保留统一添加、可用时显示的撤销与设置入口，侧栏也提供设置入口。外观页用具名fieldset和四个真实native radio呈现整套工作区预览，文字为雾紫／海湾／松林／莓暮；预览跟随当前亮暗模式。浅色／深色／跟随系统及语言仍为native select；旧accentSelect隐藏，仅兼容原有状态，不形成第二个可见或Tab入口。主题切换不重建任务列表或编辑表单。

四视图是原生导航按钮，当前任务视图以可见选中样式及 `aria-current="page"` 共同表达；任务内容使用有名称的region。进入设置时不保留一个指向隐藏任务内容的选中tab。设置不占用四视图的持久化字段，不改变保存视图格式。

### Fields and form

普通字段最小高度42px、8px圆角，使用inset底与controlBorder；聚焦切raised表面并保留一圈可辨焦点。任务搜索在inset工具区内使用content底。编辑器页头与操作栏为raised，正文工作面为content，日期、子任务与高级字段按用途分组；标题、描述与子任务等常用字段优先，非默认高级值保持可见。

编辑器的页头不收缩，表单为可滚动的flex子区域（min-height:0），操作栏在表单内sticky。展开更多设置后仍能滚到标签、提醒与重复末端；窄屏保留内容与操作栏之间的余量。日期与时区说明按需展开，取消、草稿及保存保护继续使用原有流程。

装饰图标与输入文字分别留出空间：快速添加与命令搜索左侧内边距为 40px，最小高度分别为 40px、44px。任务搜索桌面使用 13px 字号、40px 最小高度与 86px 右内边距；779px 及以下使用 12px 字号、36px 最小高度与 40px 右内边距，清除按钮右距 10px，快捷键提示隐藏。快速添加窄屏字号为 12px。通用 input 规则不能覆盖这些字段的实际内边距、字号或高度。

### Task rows and chips

父任务完成按钮保留至少40×44px操作区域，内部20px圆形控件完成后success底、白色图标；批量选择保持方形并使用primary／on-primary。子任务18px控件保持success底与独立白勾。任务主体保持文字、项目、标签、日期、描述与子任务关联，完成与归档行不降低整体不透明度。项目chip保留功能色并加重名称，普通标签使用透明底与辅助文字。

截止日期继续按界面语言和任务保存时区格式化，再通过Intl.DateTimeFormat的formatToParts将小时、分钟、秒与dayPeriod及其中间分隔文字放入同一`.task-clock`，使用nowrap。日期部分可自然换行，时间与AM/PM保持同组；这只改变呈现，不改期限值、时区或原始格式化文字。

任务更多菜单包含真实操作；首开先同步测量和定位，在视口边缘向上或向内调整。菜单明确使用 transition: none，不能给 top、left、max-height 或所有属性增加 transition，以免首次定位滑过画面或产生错误几何测量。方向键与 Home/End 移动项目，Escape 关闭并返回触发按钮。

### Calendar, dialogs and feedback

小日历与七天索引保留项目提示。完整日历的today日期使用active底、primary文字与边界；selected日期使用primary底与on-primary文字，同时给日期格轻选中底，选中当天由selected规则表达当前选择。事件chip使用轻项目／状态色底和实色点，任务名称可换行；当日日程在inset面中承载content任务行。窄屏保留紧凑月份与可读日程，原生日程dialog关闭后恢复位置和焦点。

反馈使用内容表面与对应语义图标，成功／信息为status，警告／错误为alert。弹窗内发生的反馈进入当前弹窗的流内区域，标题与关闭控件保持可见；打开新弹窗先结束旧反馈上下文。任务操作反馈可在应用反馈层提供短时撤销；常驻撤销仍由顶栏按可用状态显示。

动效服务于操作反馈：常用按钮颜色与表面变化使用180ms，主按钮hover轻移-1px、pressed轻移1px；任务行悬停保持原位，菜单定位不做几何动画。对话框使用短暂淡入与8px进入位移。prefers-reduced-motion下关闭主按钮位移、压低动画与transition时长，程序滚动使用auto。

## Do's and Don'ts

### Do:

- **Do** 使用现有语义颜色及对应暗色值，让主区、侧栏与浮层保持可辨层次。
- **Do** 保持任务中间列可收缩、长文本可换行，并在批量模式切换真实列结构。
- **Do** 在中英文、亮暗主题和窄屏中保留焦点、控件名称与相同功能。
- **Do** 尊重 reduced-motion，并在浮层关闭后把焦点返回有效触发元素。

### Don't:

- **Don't** 把逐项任务改成悬浮卡片、给任务行附加位移，或用装饰盖过状态信息。
- **Don't** 将任务菜单的首次测量和定位加入 transition。
- **Don't** 混用普通选择的on-primary勾号与子任务的固定白色成功勾号，或靠降低整行透明度表达完成。
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

## Workspace themes and component materials — 4.13.0

- **主／次操作：** 主题primary承载raised主按钮，hover与pressed有各自高度和阴影；次按钮、文字操作与危险操作按用途区分，不把所有按钮画成同一种色块。
- **字段与编辑器：** 搜索、普通字段、日期、标签与子任务分层，编辑器页头／工作面／字段／页脚使用不同表面；聚焦轮廓与选择状态分别可辨。
- **菜单：** raised菜单与母表面分离，hover／focus稳定，删除拥有危险分组与独立语义色，关闭恢复有效焦点。
- **日历与日程：** today、selected、事件chip与当日日程分别表达日期身份、当前选择与任务内容，长名称自然换行。
- **统计：** 三入口共享inset操作带，以分隔线区分；七日回顾使用content、项目安排使用inset，在桌面并列、窄屏顺序显示。项目待办条为4px高、不透明primary，宽度按本范围待办占比生成；项目面板按实际内容自然收高，任务详情独立展开。
- **密度与响应：** 上下文页头、成组任务页、日程tray与紧凑元信息共同组织空间，保留任务内容、功能与命中区域。手机标题不独占大色块，时间与AM/PM以同组呈现。
- **选择与偏好：** 原生radio保留checked、组名和键盘语义，预览随亮暗模式切换。完整workspace主题替换原先仅主色覆盖的配色方式；沿用accent的四枚举，不改任务、草稿、选择或DB／备份协议。

## 直接操作与状态 — 4.13.1

- 主添加与快捷记录共处一个稳定顶栏，不在四个视图重复铺表单。项目/无项目上下文与今日计划贯穿新建与草稿恢复；明确输入的项目优先。
- 今日计划的无匹配状态与真正空计划分开，清搜索/筛选后保留计划；最窄撤销使用可访问名称完整的图标。
- 帮助与关于提供主动检查更新、明确状态与就绪后的刷新；检查和刷新不吞掉草稿、恢复内容或进行中的保存。
- 任务菜单z-index为1000，高于工具栏及快速记录，低于导航遮罩与模态；向上展开仍可实际点击。
