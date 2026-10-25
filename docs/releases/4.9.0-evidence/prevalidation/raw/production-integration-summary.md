# Task Tracer 4.9.0 界面集成工作记录

此记录由 index.html 集成负责人编写。当前应用位于 `/workspace/Task-Tracer-redesign`，父级正在执行正式截图与受影响验证；本记录不替代完整候选验收，也不声称用户已验收生产版本。

## 实现范围

仅由本负责人修改 index.html。版本为4.9.0、资源4.37，内置翻译与两份649键资源同步。SW、manifest、包版本、第三方声明、CSP、检查工具与发行文件由其他负责人管理。

- 将原居中的网格背景与独立任务卡片改为完整工作区：侧栏、顶部偏好入口、主任务表面、日期索引及辅助月历/即将到期区。沿用用户已正向确认的第二版可交互样板的层次与组件语言。
- 桌面未来7天索引、迷你月历、即将到期条目使用真实任务数据；日历日期沿用已有 civil date key 与保存时区辅助函数。日期点击走既有 calendar view/day 路由，没有新增持久化日期筛选字段。
- 窄屏侧栏采用 hidden/inert 与背景区域 inert、键盘焦点约束；展开时进入可见导航，Escape返回入口。侧栏同级项目导航在已有 action guard 成功后退出今日计划；原项目筛选控件仍可在今日计划内组合筛选。
- 小月历可在窄屏原生 dialog 中查看，关闭返回入口；空工作区或0匹配日期跳转有可见 calendar tab/新增入口回退。今天细环、选中实底、有任务事件点分别表达状态；今天与选中可共存。
- 任务完成操作移到行首。次要动作在任务节点内部的原位菜单中展示，继续使用原委托与动作路由；菜单可键盘操作。编辑/删除保存逻辑返回目标，非模态操作完成后在焦点丢失时恢复可见任务按钮，必要时选择相邻任务。
- 新语言与三态外观为原生 select，并排除旧 select enhancer。语言入口仍经过中央 guard；被拒绝或异步保存失败后与真实语言状态同步。用户任务、项目及标签内容不被语言切换改写。
- `theme` 旧 light/dark 值保持兼容，缺失/非法值按 system 处理；偏好与 resolved theme 分离。首屏bootstrap、matchMedia和真实 storage 事件同步仅更新呈现、chrome与选择值，不重建任务列表、表单或子任务输入。
- 缓存 Intl.PluralRules，为现有数量文案消费 One 别名；保留原占位符与实际计数含义，重复天数与提醒分钟等使用对应数值。
- 用稳定项目名称哈希提供侧栏、任务项目标记和周事件点的同一配色映射，不增加持久化偏好。
- 保留原数据模型、DB版本2、任务备份JSON2.4、视图1.1、旧1.0导入、事务/重复链/恢复历史/分页/批量/手动排序/IME与草稿流程。没有用研究样板的简化任务模型替换生产逻辑。

## CSS 与资产

按组件归拢被替换的旧基础 selector 与断点覆盖，保留安全、导入、表单及必要状态样式。首轮清理曾使旧单列 grid 和状态 pill 值重新覆盖，父级实拍发现后已修正显式三列与轻量 metadata；另删除旧 mobile project/filter/sort flex 规则以消除控件互盖。完成、归档行不再整体降低opacity；控件边界使用独立可测颜色。

使用研究样板中来源可追溯的 Tabler 原始SVG几何图标建立必要的新符号；未复制 AppFlowy 的图片、商标或专有图形。index metadata指向发行中的 THIRD_PARTY_NOTICES.md；runtime没有新增注释。

## 本负责人实际执行的调试检查

这些是集成过程中在本地 Chromium 上执行的有限调试，不是父级最终冻结候选的完整验收。

- 四项合成任务实际新增、子任务展开/完成、1440px与390px截图；未出现pageerror，已检查无横向溢出。
- 菜单编辑后Escape返回逻辑更多按钮、非模态加入今日计划后回到可见更多按钮、今日计划到侧栏项目退出计划，均在实际页面操作中检查。
- 移动日程dialog居中、Escape返回入口；移动侧栏展开与Escape焦点；空工作区从移动日程点击日期后回到可见calendar tab，已操作通过。
- 英文单复数与用户内容保持原文已经实现；本负责人第三轮调试在导航断言处中断，其后安排的英文计数步骤未执行，不能记作通过，交由父级正式检查。
- 最后一次静态验证与git diff --check通过。
- 真实computed浅色完成框边界为rgb(122,134,157)对白色，对比3.668:1；暗色为rgb(160,173,198)对rgb(37,43,61)，6.227:1。对应任务文字为13.156:1与12.375:1。暗色采样等待body实际变为rgb(24,28,41)，不是首帧过渡颜色。

## 已发现并保留的调试失败

中间版本的移动侧栏曾两次未将焦点移至可见导航按钮：visibility/transform过渡首帧使即时与单次rAF聚焦失败。最终改成明确hidden/inert与显示状态后，两个必要移动焦点检查重新通过。中间版调试截图分别位于 `/tmp/task-tracer-integration-first`、`-second`、`-third`；它们不能当作最终版本截图。

第一次暗色颜色采样发生在样式切换首帧，仍取得浅色值，不能作为暗色通过证据；随后等待真实body颜色后重新取得上述暗色computed值。父级另执行的初步appearance结果及Firefox重载超时由父级原报告单列，不改写为本负责人修复或最终通过。

## 第四轮定点修复与调试

父级正式实拍及 affected 检查发现：桌面 grid 隐式列、窄屏工具栏过高、短列表 dropdown 被 quick-add 遮挡、七日按钮可见名称不在 aria-label、toast 不提供即时 Undo。按父级确定范围修复，并保留完整日期/余时文本可选择复制；工具栏改为窄屏 tabs/search/save 一行与 filters 一行，collapse/pin 保持直接可点。永久 Undo 只有顶栏入口，短时通知恢复原上下文 Undo 条件。footer明确全工作区（不含归档），不改变原统计集合。

第四轮真实 Chromium 调试中：40px/730px/40px 桌面列宽正确，390px无横溢；首任务 title bounding box 从约465px前移到330.5px；collapse/expand、无截止日期筛选与项目列表末项均以普通 pointer 通过。复用了原 notification pointer 专项，在1280px/900px实际点主菜单再点toast Undo，检查任务记录被撤销，均通过。调试无pageerror。该轮截图在 `/tmp/task-tracer-integration-fourth`，早于本批最后纵向留白/footer文案收紧，不能充作最终候选截图。

原失败保留：首次本地server在sandbox不能bind socket，自动审查批准外部执行后改用本地localhost；默认Playwright浏览器未安装，改用既有 `/usr/bin/chromium`。第一次项目指针点击被旧media specificity导致的filter按钮挡住，删除对应旧规则后相同路径重跑通过。调试使用普通本地static server，不替代父级带正式CSP的候选检查。

## 最后小批修复与复核

父级另明确四项实证收尾：存储故障与草稿恢复说明浅色对比4.48不足、Linux英文标点fallback不合适、窄屏项目菜单左侧越界、末行任务菜单距底80px时向下溢出54px。对应只改关键说明为正文色、在Segoe与CJK字体之间加入Arial、项目菜单start-align并限定宽度、任务菜单按触发器实矩形选择上下位置与夹紧，空间不足内部滚动。菜单保留任务节点内DOM与原委托/键盘/返回焦点，不portal、不改任务数据。OG截图元数据同时按父级要求更新为1440×1024。

首轮新定位代码出现断言瞬间旧BCR、稍后位置正确的失败；没有删断言或延时通过。动态诊断记录了HTTP响应与磁盘SHA一致、新helper实际执行、scrollY始终1653，而menu.getAnimations()出现top44px→-134px的CSSTransition。原因是全局reduced-motion universal给无自定义transition的菜单设置了极短duration，默认transition-property:all使几何进入首帧过渡。菜单明确transition:none后，保留同步定位再首次聚焦，未添加等待。

最终本地定点复核：复用既有18任务真实UI回归，1280×720与390×844菜单整体在viewport、Delete中心实际mouse命中、确认Cancel后18条任务记录完全不变，均通过。另长字面项目名及status/sort在390×844、320×568六个展开菜单框全部在viewport；project左右边界分别为28/348、28/292。说明文字computed前景为rgb(38,48,71)，无pageerror。HTTP与磁盘最终SHA均为011d741e27bfe0134b8c065decd4ff5999e275b27d980a7728478347bc875bd4。普通本地static server复核不替代正式CSP。

JS语法与diff检查通过；静态检查唯一失败是父级已授权的新OG尺寸与validator旧1365×1227常量不一致，已交工具负责人更新准确1440×1024契约。内嵌649键与资源/版本仍匹配。应用源码随即暂停，父级负责CSP及最终受影响检查、截图与发行闭合。

## 保存视图按钮的最后局部修正

父级smoke抓到旧`.controls-bar .saved-view-save-btn`42px规则权重高于新移动32px规则，导致窄屏grid末列向外伸出10px。只删除这两条旧高权重重复（尺寸与span），将桌面42px完整值合入唯一base class；移动32×36不再被覆盖。

本地700/420/390/320四宽实际button都是32×36、右边界与toolbar row一致、scrollWidth等于viewport、中心hit为自身或其子节点。每宽普通pointer打开保存视图对话框并Cancel通过，0pageerror；HTTP响应与磁盘SHA一致。静态、649内嵌翻译、diff检查均通过。新稳定index SHA为50f6fffedafb60a1e15f547e7154e97e570b881dc799fea86304131fc881c0c2，交根刷新CSP后执行smoke/a11y与最终八图；未重跑无关全套。

## 三个装饰输入框的最小收尾

父级最终截图发现quick-add的plus压住placeholder。只读probe进一步确认quick/search/command三输入被通用input规则覆盖，实际统一padding9/12、font14、minheight42：quick/command文字侵入前置图标，search可延入clear和shortcut区。父级正式CSP旧源probe在 `/tmp/task-tracer-input-geometry/7cfc7978-0efe-44e9-bf40-976d55daee1e/report.json`，保留旧失败。

窗口结束后只在三个原组件声明块并列稳定ID，提高真实装饰input的base与media specificity，同时保留class对既有表单select的贡献；通用input规则不动。≤779px把search右安全区设40、clear右10、隐藏只读shortcut提示，键盘快捷键不变。桌面search保留右86，quick/command保留左40。

本地1440/779/390/320四宽实际长文字、普通pointer清空搜索、CtrlP打开命令面板并输入task/Escape、quick-add草稿原文保留均通过，无pageerror。quick/command文字起点在前置图标右侧约11px；desktop search安全右端949小于clear左958；mobile间隙5px。mobile search的font12/minheight36、quick height40与command minheight44按组件意图生效。普通本地static point check不替代正式CSP；父级更新CSP后重跑受影响范围与八图。最后静态、649内嵌翻译与diff检查通过，HTTP=磁盘，index SHA为c74e68e59b7705e8c22877e6a0170d5d6d6803405a49ff418549fd2a96ab3af7，已暂停写入。

## 交接与待验范围

index在第四轮修复后再次暂停写入；父级将刷新CSP并启动新稳定窗口。此前07:53:08 UTC窗口的appearance三引擎24/24通过属于其旧输入，其余失败如实保留并促成本轮修复。最终桌面/窄屏、明暗、中英文、完整功能、数据故障、三引擎、发行升级/回退、离线、生产域名及真实设备范围均以父级实际报告为准；本记录不预填这些结果。发现新问题须由父级协调同批修复与重验。
